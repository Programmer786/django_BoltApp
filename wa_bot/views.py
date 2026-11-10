import hmac
import json
import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings as django_settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from base.utils import log_activity
from whatsapp.views import superuser_required

from . import ai
from .engine import build_reply, handle_incoming
from .models import KEEP_CONVERSATIONS_DAYS, BotConversation, BotSettings, BotState

STALE_AFTER = timedelta(seconds=90)  # listener heartbeats every 30s


def _live_state(state):
    """Treat a listener that stopped reporting as offline."""
    if state.last_seen is None or timezone.now() - state.last_seen > STALE_AFTER:
        return 'offline'
    return state.state


def _sync_control_path():
    return os.getenv('SYNC_CONTROL_FILE', os.path.join(str(django_settings.MEDIA_ROOT), '.bolt_sync_control.json'))


def _read_sync_control():
    """The on/off button's saved state; no file means on."""
    try:
        with open(_sync_control_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'enabled': True}


def _live_sync_status():
    """Last result written by docker/sync_live.py (Docker copy only), or None."""
    path = os.getenv('SYNC_STATUS_FILE', os.path.join(str(django_settings.MEDIA_ROOT), '.bolt_sync.json'))
    try:
        with open(path) as f:
            data = json.load(f)
        data['at'] = datetime.fromisoformat(data['at'])
        data['interval_minutes'] = max(1, round(data.get('min_interval', 120) / 60))
        control = _read_sync_control()
        data['enabled'] = control.get('enabled', True)
        turned_on_at = control.get('turned_on_at')
        data['first_sync_pending'] = bool(
            data['enabled'] and turned_on_at and datetime.fromisoformat(turned_on_at) > data['at'])
        return data
    except (OSError, ValueError, KeyError):
        return None


# ---------------------------------------------------------------- admin pages

@superuser_required
def verification_page(request):
    BotConversation.delete_expired()  # the listener's heartbeat does this too, unless it is stopped
    settings = BotSettings.load()
    state = BotState.load()
    q = request.GET.get('q', '').strip()
    result = request.GET.get('result', '').strip()

    convs = BotConversation.objects.all()
    if q:
        convs = convs.filter(Q(phone__icontains=q) | Q(matched_number__icontains=q) |
                             Q(message__icontains=q) | Q(name__icontains=q))
    if result:
        convs = convs.filter(result=result)
    page = Paginator(convs, 25).get_page(request.GET.get('page'))

    today = timezone.localdate()
    by_result = dict(BotConversation.objects.filter(created_at__date=today)
                     .values_list('result').annotate(n=Count('id')))
    stats = {
        'today_total': sum(by_result.values()),
        'today_found': by_result.get('found', 0),
        'today_not_found': by_result.get('not_found', 0),
        'today_chat': by_result.get('chat', 0),
        'unique_people': BotConversation.objects.values('phone').distinct().count(),
    }
    return render(request, 'wa_bot/verification.html', {
        'live_sync': _live_sync_status(),
        'title': 'WhatsApp Verification',
        'sidebar_active': 'whatsapp_verification',
        'settings_obj': settings,
        'bot_state': state,
        'live_state': _live_state(state),
        'ai_available': ai.available(),
        'ai_model': ai.OLLAMA_MODEL,
        'conversations': page,
        'stats': stats,
        'keep_days': KEEP_CONVERSATIONS_DAYS,
        'q': q,
        'result_filter': result,
        'result_choices': BotConversation.RESULT_CHOICES,
    })


@superuser_required
def status_json(request):
    state = BotState.load()
    return JsonResponse({
        'state': _live_state(state),
        'qr': state.qr if _live_state(state) == 'qr' else '',
        'phone': state.phone,
        'last_seen': state.last_seen.isoformat() if state.last_seen else None,
        'pending_command': state.pending_command,
    })


@superuser_required
@require_POST
def save_settings(request):
    s = BotSettings.load()
    s.enabled = request.POST.get('enabled') == '1'
    s.use_ai = request.POST.get('use_ai') == '1'
    s.brand = (request.POST.get('brand') or s.brand).strip()[:120]
    s.office_contact = (request.POST.get('office_contact') or '').strip()[:200]
    for field in ('welcome_text', 'not_found_text', 'rate_limited_text'):
        value = (request.POST.get(field) or '').strip()
        if value:
            setattr(s, field, value)
    try:
        s.max_lookups_per_hour = max(1, min(200, int(request.POST.get('max_lookups_per_hour', s.max_lookups_per_hour))))
    except ValueError:
        pass
    s.save()
    log_activity(user=request.user, action='Updated WhatsApp verification bot settings', request=request)
    messages.success(request, 'Bot settings saved.')
    return redirect('wa_bot_page')


@superuser_required
@require_POST
def toggle_sync(request):
    """The live data sync's on/off button. docker/sync_live.py watches this file."""
    enabled = request.POST.get('enabled') == '1'
    control = _read_sync_control()
    if control.get('enabled', True) == enabled:  # stale page or double click
        return redirect('wa_bot_page')

    control['enabled'] = enabled
    if enabled:
        control['turned_on_at'] = datetime.now(dt_timezone.utc).isoformat()
    path = _sync_control_path()
    try:
        with open(path + '.tmp', 'w') as f:
            json.dump(control, f)
        os.replace(path + '.tmp', path)  # the sync program never sees a half-written file
    except OSError as e:
        messages.error(request, f'Could not change the live data sync: {e}')
        return redirect('wa_bot_page')

    log_activity(user=request.user, action=f'Turned live data sync {"ON" if enabled else "OFF"}', request=request)
    messages.success(request, 'Live data sync is ON. The first sync is starting now.' if enabled
                     else 'Live data sync is OFF. Nothing new will be copied until you turn it on.')
    return redirect('wa_bot_page')


@superuser_required
@require_POST
def test_message(request):
    """Preview the exact reply for a message, without sending or logging it."""
    text = request.POST.get('text', '')
    reply = build_reply(text, check_rate_limit=False)
    labels = dict(BotConversation.RESULT_CHOICES)
    return JsonResponse({'reply': reply.text, 'result': labels.get(reply.result, reply.result),
                         'used_ai': reply.used_ai})


@superuser_required
@require_POST
def relink(request):
    """Ask the listener to log out so a new QR code (new number) can be scanned."""
    state = BotState.load()
    state.pending_command = 'logout'
    state.save(update_fields=['pending_command'])
    log_activity(user=request.user, action='Requested WhatsApp bot re-link (logout)', request=request)
    messages.info(request, 'Logout requested. A new QR code will appear within about a minute.')
    return redirect('wa_bot_page')


# ------------------------------------------------- listener API (shared key)

def _authorized(request):
    key = os.getenv('WA_BOT_KEY', '')
    given = request.headers.get('X-Bot-Key', '')
    return bool(key) and hmac.compare_digest(key, given)


def _json_body(request):
    try:
        return json.loads(request.body or b'{}')
    except ValueError:
        return None


@csrf_exempt
@require_POST
def api_incoming(request):
    if not _authorized(request):
        return JsonResponse({'error': 'unauthorized'}, status=401)
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'bad json'}, status=400)
    phone = str(data.get('phone') or '').strip()
    if not phone:
        return JsonResponse({'error': 'phone required'}, status=400)
    reply = handle_incoming(phone, data.get('name', ''), str(data.get('text') or ''))
    return JsonResponse({'reply': reply.text, 'result': reply.result})


@csrf_exempt
@require_POST
def api_status(request):
    """Listener heartbeat / state change. Returns any pending command once."""
    if not _authorized(request):
        return JsonResponse({'error': 'unauthorized'}, status=401)
    data = _json_body(request) or {}
    state = BotState.load()
    new_state = data.get('state')
    if new_state in dict(BotState.STATE_CHOICES):
        state.state = new_state
    state.qr = str(data.get('qr') or '') if new_state == 'qr' else ''
    if 'phone' in data:
        state.phone = str(data.get('phone') or '')[:40]
    state.last_seen = timezone.now()
    command = state.pending_command
    state.pending_command = ''
    state.save()
    BotConversation.delete_expired()
    return JsonResponse({'command': command})
