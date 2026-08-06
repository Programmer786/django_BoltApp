import functools
import logging
import threading

import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import connection
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from base.utils import log_activity
from .models import WhatsAppContact, WhatsAppMessage, WhatsAppMessageLog

logger = logging.getLogger(__name__)


def superuser_required(view_func):
    @functools.wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Access denied. Admin only.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped


@superuser_required
def whatsapp_contacts(request):
    search = request.GET.get('search', '').strip()
    qs = WhatsAppContact.objects.all()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(phone__icontains=search))

    paginator = Paginator(qs, 25)
    page = request.GET.get('page', 1)
    try:
        contacts_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        contacts_page = paginator.page(1)

    return render(request, 'whatsapp/contacts.html', {
        'sidebar_active': 'whatsapp_contacts',
        'contacts': contacts_page,
        'total_contacts': WhatsAppContact.objects.count(),
        'search': search,
    })


@superuser_required
@require_POST
def upload_contacts_excel(request):
    excel_file = request.FILES.get('excel_file')
    if not excel_file:
        messages.error(request, 'Please select an Excel file.')
        return redirect('whatsapp_contacts')

    if not excel_file.name.lower().endswith(('.xlsx', '.xls')):
        messages.error(request, 'Only Excel files (.xlsx, .xls) are supported.')
        return redirect('whatsapp_contacts')

    try:
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb.active

        created = updated = skipped = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue

            name = str(row[0]).strip()
            phone_raw = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ''

            if not name or not phone_raw or phone_raw == 'None':
                skipped += 1
                continue

            # Normalize: remove spaces/dashes, ensure leading +
            phone = phone_raw.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not phone.startswith('+'):
                phone = '+' + phone

            _, was_created = WhatsAppContact.objects.update_or_create(
                phone=phone,
                defaults={'name': name, 'created_by': request.user},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        wb.close()
        log_activity(
            user=request.user,
            action=f"Uploaded WhatsApp contacts Excel: {created} created, {updated} updated, {skipped} skipped",
            request=request,
        )
        messages.success(request, f'Import complete — {created} added, {updated} updated, {skipped} skipped.')

    except Exception as e:
        logger.error(f"WhatsApp Excel upload failed: {e}")
        messages.error(request, f'Error reading Excel file: {e}')

    return redirect('whatsapp_contacts')


@superuser_required
@require_POST
def delete_contact(request, contact_id):
    contact = get_object_or_404(WhatsAppContact, id=contact_id)
    name = contact.name
    contact.delete()
    log_activity(user=request.user, action=f"Deleted WhatsApp contact: {name}", request=request)
    messages.success(request, f'Contact "{name}" deleted.')
    return redirect('whatsapp_contacts')


@superuser_required
@require_POST
def add_contact(request):
    name = request.POST.get('name', '').strip()
    phone_raw = request.POST.get('phone', '').strip()

    if not name or not phone_raw:
        messages.error(request, 'Name and phone number are required.')
        return redirect('whatsapp_contacts')

    phone = phone_raw.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    if WhatsAppContact.objects.filter(phone=phone).exists():
        messages.warning(request, f'A contact with phone {phone} already exists.')
        return redirect('whatsapp_contacts')

    WhatsAppContact.objects.create(name=name, phone=phone, created_by=request.user)
    log_activity(user=request.user, action=f"Added WhatsApp contact: {name} ({phone})", request=request)
    messages.success(request, f'Contact "{name}" added successfully.')
    return redirect('whatsapp_contacts')


@superuser_required
@require_POST
def edit_contact(request, contact_id):
    contact = get_object_or_404(WhatsAppContact, id=contact_id)
    name = request.POST.get('name', '').strip()
    phone_raw = request.POST.get('phone', '').strip()

    if not name or not phone_raw:
        messages.error(request, 'Name and phone number are required.')
        return redirect('whatsapp_contacts')

    phone = phone_raw.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    # Check duplicate phone — allow same contact to keep its own phone
    if WhatsAppContact.objects.filter(phone=phone).exclude(id=contact_id).exists():
        messages.warning(request, f'Another contact already uses {phone}.')
        return redirect('whatsapp_contacts')

    old_name = contact.name
    contact.name = name
    contact.phone = phone
    contact.save()
    log_activity(user=request.user, action=f"Edited WhatsApp contact: {old_name} → {name} ({phone})", request=request)
    messages.success(request, f'Contact updated successfully.')
    return redirect('whatsapp_contacts')


@superuser_required
def whatsapp_web_status(request):
    """AJAX — returns WhatsApp Web connection status + QR base64 if not logged in."""
    from .selenium_sender import get_status
    status = get_status()
    return JsonResponse(status)


@superuser_required
def send_message(request):
    contacts = WhatsAppContact.objects.all().order_by('name')
    history = WhatsAppMessage.objects.prefetch_related('logs').order_by('-sent_at')[:30]

    if request.method == 'POST':
        sender = request.POST.get('sender', 'twilio')     # twilio | selenium
        mode = request.POST.get('mode', 'text')           # text | template
        msg_type = request.POST.get('message_type', 'single')  # single | bulk
        body = request.POST.get('body', '').strip()
        content_sid = request.POST.get('content_sid', '').strip()
        content_variables = request.POST.get('content_variables', '').strip()
        template_lang = request.POST.get('template_lang', 'en_US').strip() or 'en_US'
        template_vars_raw = request.POST.get('template_vars', '').strip()  # e.g. "{name}, 12/01"

        # prebuilt mode is just custom text (editable template body)
        if mode == 'prebuilt':
            mode = 'text'

        # Validate
        if mode == 'text' and not body:
            messages.error(request, 'Message body is required.')
            return redirect('whatsapp_send')
        if mode == 'template' and not content_sid:
            messages.error(request, 'Template SID is required.')
            return redirect('whatsapp_send')

        # Handle image upload → save and build public URL
        image_url = None
        image_local_path = None  # absolute path on disk — used by Selenium sender
        image_https_warning = False
        uploaded_image = request.FILES.get('message_image')
        if uploaded_image:
            try:
                import os
                import uuid
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile

                ext = os.path.splitext(uploaded_image.name)[1].lower()
                filename = f"whatsapp_images/{uuid.uuid4().hex}{ext}"
                saved_name = default_storage.save(filename, ContentFile(uploaded_image.read()))
                image_local_path = default_storage.path(saved_name)  # absolute disk path

                # Use WHATSAPP_BASE_URL from env (must be HTTPS for Twilio media delivery)
                base_url = getattr(settings, 'WHATSAPP_BASE_URL', '').rstrip('/')
                if not base_url:
                    domain = getattr(settings, 'DOMAIN_NAME', '147.93.90.97')
                    base_url = f"http://{domain}"
                image_url = f"{base_url}/media/{filename}"

                # HTTPS only matters for Twilio — Selenium uploads the local file directly
                if sender == 'twilio' and not image_url.startswith('https://'):
                    image_https_warning = True
                    logger.warning(f"WhatsApp image URL is not HTTPS — image won't be sent via Twilio: {image_url}")

            except Exception as e:
                logger.error(f"WhatsApp image upload failed: {e}")

        # Resolve recipients
        if msg_type == 'single':
            contact_id = request.POST.get('contact_id', '').strip()
            if not contact_id:
                messages.error(request, 'Please select a contact.')
                return redirect('whatsapp_send')
            recipient_qs = WhatsAppContact.objects.filter(id=contact_id)
        else:
            selected_ids = request.POST.getlist('bulk_contacts')
            recipient_qs = WhatsAppContact.objects.filter(id__in=selected_ids) if selected_ids else WhatsAppContact.objects.all()

        recipient_ids = list(recipient_qs.values_list('id', flat=True))
        if not recipient_ids:
            messages.error(request, 'No contacts to send to.')
            return redirect('whatsapp_send')

        wa_message = WhatsAppMessage.objects.create(
            sent_by=request.user,
            message_type=msg_type,
            mode=mode,
            via=sender,
            body=body if mode == 'text' else None,
            image_url=image_url,
            content_sid=content_sid if mode == 'template' else None,
            content_variables=content_variables if mode == 'template' else None,
            status='queued',
            total_recipients=len(recipient_ids),
        )

        if image_https_warning and sender == 'twilio':
            messages.warning(
                request,
                'Image was saved but will NOT be sent — Twilio requires HTTPS for images. '
                'Set WHATSAPP_BASE_URL=https://... in your .env to enable image sending.'
            )

        # The actual sending happens in a background thread so this request
        # returns immediately instead of blocking the web worker for the
        # entire bulk send (WhatsApp Web sends run ~12-17s per contact).
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        browser_info = request.META.get('HTTP_USER_AGENT', '')

        thread = threading.Thread(
            target=_send_whatsapp_bulk,
            args=(
                wa_message.id, sender, mode, body, image_local_path, image_url,
                content_sid, content_variables, template_lang, template_vars_raw,
                recipient_ids, msg_type, request.user.id, ip_address, browser_info,
            ),
            daemon=True,
        )
        thread.start()

        messages.info(request, f'Sending to {len(recipient_ids)} contact(s) — track progress below.')
        return redirect(f"{reverse('whatsapp_send')}?tracking={wa_message.id}")

    return render(request, 'whatsapp/send_message.html', {
        'sidebar_active': 'whatsapp_send',
        'contacts': contacts,
        'history': history,
        'total_contacts': contacts.count(),
        'tracking_message_id': request.GET.get('tracking', ''),
    })


def _send_whatsapp_bulk(wa_message_id, sender, mode, body, image_local_path, image_url,
                         content_sid, content_variables, template_lang, template_vars_raw,
                         recipient_ids, msg_type, user_id, ip_address, browser_info):
    """
    Runs the actual per-contact sending off the request thread. Updates
    WhatsAppMessage.total_sent/total_failed after every contact so the
    frontend can poll real progress instead of a simulated timer.
    """
    try:
        wa_message = WhatsAppMessage.objects.get(id=wa_message_id)
        wa_message.status = 'sending'
        wa_message.save(update_fields=['status'])

        recipient_qs = WhatsAppContact.objects.filter(id__in=recipient_ids)
        total_sent = total_failed = 0

        def record(contact, success, error=None, sid=None):
            nonlocal total_sent, total_failed
            WhatsAppMessageLog.objects.create(
                message=wa_message,
                contact=contact,
                phone=contact.phone,
                contact_name=contact.name,
                sid=sid,
                status='sent' if success else 'failed',
                error=error,
            )
            if success:
                total_sent += 1
            else:
                total_failed += 1
            wa_message.total_sent = total_sent
            wa_message.total_failed = total_failed
            wa_message.save(update_fields=['total_sent', 'total_failed'])

        # ── WhatsApp Web (Selenium) ────────────────────────────────────────────
        if sender == 'selenium':
            from .selenium_sender import get_status, send_wa_message

            status = get_status()
            if not status['available']:
                logger.error(f"Selenium error: {status['error']}")
                wa_message.status = 'failed'
                wa_message.save(update_fields=['status'])
                return
            if not status['logged_in']:
                logger.error('WhatsApp Web is not connected — QR not scanned.')
                wa_message.status = 'failed'
                wa_message.save(update_fields=['status'])
                return

            for contact in recipient_qs:
                success, error = send_wa_message(contact.phone, body or '', image_path=image_local_path)
                record(contact, success, error=error)

        # ── Meta WhatsApp Business Cloud API ────────────────────────────────────
        elif sender == 'meta':
            from .meta_sender import send_meta_message, is_configured

            if not is_configured():
                logger.error('Meta Cloud API is not configured (META_WA_ACCESS_TOKEN/META_WA_PHONE_NUMBER_ID missing).')
                wa_message.status = 'failed'
                wa_message.save(update_fields=['status'])
                return

            for contact in recipient_qs:
                tpl_vars = None
                if mode == 'template' and template_vars_raw:
                    tpl_vars = [
                        v.strip().replace('{name}', contact.name)
                        for v in template_vars_raw.split(',')
                    ]
                success, error, msg_id = send_meta_message(
                    contact.phone,
                    body or '',
                    image_path=image_local_path,
                    mode=mode,
                    template_name=content_sid,  # reused field holds the template name for Meta
                    template_lang=template_lang,
                    template_vars=tpl_vars,
                )
                record(contact, success, error=error, sid=msg_id)

        # ── Twilio API ─────────────────────────────────────────────────────────
        else:
            try:
                from twilio.rest import Client
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            except Exception as e:
                logger.error(f"Twilio client init failed: {e}")
                wa_message.status = 'failed'
                wa_message.save(update_fields=['status'])
                return

            for contact in recipient_qs:
                try:
                    kwargs = {
                        'from_': settings.TWILIO_WHATSAPP_NUMBER,
                        'to': f'whatsapp:{contact.phone}',
                    }
                    if mode == 'template':
                        kwargs['content_sid'] = content_sid
                        if content_variables:
                            kwargs['content_variables'] = content_variables
                    else:
                        kwargs['body'] = body
                        if image_url and image_url.startswith('https://'):
                            kwargs['media_url'] = [image_url]

                    msg = client.messages.create(**kwargs)
                    record(contact, True, sid=msg.sid)

                except Exception as e:
                    logger.error(f"Twilio send to {contact.phone} failed: {e}")
                    record(contact, False, error=str(e))

        wa_message.status = 'sent' if total_failed == 0 else ('failed' if total_sent == 0 else 'partial')
        wa_message.save(update_fields=['status'])

        user = User.objects.filter(id=user_id).first()
        log_activity(
            user=user,
            action=f"WhatsApp [{sender}] sent — {total_sent} ok, {total_failed} failed ({msg_type})",
            ip_address=ip_address,
            browser_info=browser_info,
        )
    except Exception:
        logger.exception(f"WhatsApp background send failed for message {wa_message_id}")
        WhatsAppMessage.objects.filter(id=wa_message_id).update(status='failed')
    finally:
        connection.close()


@superuser_required
def whatsapp_message_status(request, message_id):
    """AJAX — polled by the send page to show real (not simulated) send progress."""
    msg = get_object_or_404(WhatsAppMessage, id=message_id)
    return JsonResponse({
        'status': msg.status,
        'total_sent': msg.total_sent,
        'total_failed': msg.total_failed,
        'total_recipients': msg.total_recipients,
    })


@superuser_required
@require_POST
def delete_history(request):
    """Delete all WhatsApp message history, including saved image files."""
    import os
    from django.core.files.storage import default_storage

    messages_qs = WhatsAppMessage.objects.all()
    total = messages_qs.count()

    # Remove uploaded image files from disk
    removed_files = 0
    for m in messages_qs.exclude(image_url__isnull=True).exclude(image_url=''):
        # image_url looks like http://host/media/whatsapp_images/<name>
        marker = '/media/'
        if marker in (m.image_url or ''):
            rel_path = m.image_url.split(marker, 1)[1]  # whatsapp_images/<name>
            try:
                if default_storage.exists(rel_path):
                    default_storage.delete(rel_path)
                    removed_files += 1
            except Exception as e:
                logger.warning(f"Could not delete image {rel_path}: {e}")

    # Logs are cascade-deleted with their parent message
    messages_qs.delete()

    log_activity(
        user=request.user,
        action=f"WhatsApp history cleared — {total} message(s), {removed_files} image(s) removed",
        request=request,
    )
    messages.success(request, f'History cleared — {total} message(s) and {removed_files} image(s) deleted.')
    return redirect('whatsapp_send')
