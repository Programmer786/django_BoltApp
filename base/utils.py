import datetime
import json
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now

from authentication.models import ActivityLog
from certificates.models import Certificate

logger = logging.getLogger(__name__)

# this is used for pagination
items_per_page = 10
current_date = now().date().isoformat()  # Formatting the date as 'YYYY-MM-DD'


def get_manager_city(user):
    """
    Return the city a manager (is_staff, non-superuser) is restricted to.
    Returns None for superusers (no restriction) and regular employees.
    """
    if getattr(user, 'is_staff', False) and not user.is_superuser:
        profile = getattr(user, 'profile', None)
        return getattr(profile, 'city', None) if profile else None
    return None


def can_access_record(user, record):
    """
    True if `user` may view/edit `record` (a Card/Certificate/Training/NDT/
    Calibration instance, or anything exposing a `.city` property and a
    `.user_id`). Superusers: everything. Managers: only their own city.
    Everyone else (regular employees): only records they created.
    """
    if getattr(user, 'is_superuser', False):
        return True
    manager_city = get_manager_city(user)
    if manager_city:
        return getattr(record, 'city', None) == manager_city
    return getattr(record, 'user_id', None) == getattr(user, 'id', None)


def can_manage_record(user, record):
    """
    True if `user` may perform a privileged workflow action (approve,
    reject, cancel, hold, unhold, activate) on `record`. Superusers: yes.
    Managers: only for their own city. Regular employees: never, even for
    their own records — approval is a manager/admin action.
    """
    if getattr(user, 'is_superuser', False):
        return True
    manager_city = get_manager_city(user)
    return bool(manager_city) and getattr(record, 'city', None) == manager_city


def can_edit_amounts(user, record=None):
    """
    True if `user` may inline-edit the Total/Paid Amount cells.

    Superusers always may. A manager may only when a superuser has granted
    them the `can_edit_amounts` flag from Manage Accounts — and then only for
    records in their own city. Regular employees never may.

    Call with `record` on save (enforces the city check); call without it to
    decide whether to render the cells as editable at all.
    """
    if getattr(user, 'is_superuser', False):
        return True
    if not getattr(user, 'is_staff', False):
        return False
    profile = getattr(user, 'profile', None)
    if not (profile and profile.can_edit_amounts):
        return False
    return can_manage_record(user, record) if record is not None else True


def can_approve_reject(user, record=None):
    """
    True if `user` may approve or reject a pending record.

    Superusers always may. A manager may only when a superuser has granted
    them the `can_approve_reject` flag from Manage Accounts — and then only
    for records in their own city (same as can_manage_record). Regular
    employees never may.

    Call with `record` to enforce the city check on an actual approve/reject
    submission; call without it to decide whether to render the
    Approve/Reject controls at all.
    """
    if getattr(user, 'is_superuser', False):
        return True
    if not getattr(user, 'is_staff', False):
        return False
    profile = getattr(user, 'profile', None)
    if not (profile and profile.can_approve_reject):
        return False
    return can_manage_record(user, record) if record is not None else True


def redirect_back(request, fallback_view_name):
    """
    Redirect to the URL posted in a hidden `next` field — typically
    `{{ request.get_full_path }}`, the current filtered/paginated list page —
    when present and safe; otherwise fall back to the named view.

    Used by actions (approve/reject, hold/cancel, ...) triggered from a
    filtered list so the viewer's search/city/page selection survives the
    round trip instead of dumping them back to the unfiltered list.
    """
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect(fallback_view_name)


def handle_amount_field_update(request, model, uid):
    """
    Shared handler behind every module's inline Total/Paid Amount edit.

    One implementation for cards/certificates/training/ndt/calibration so the
    permission and validation rules can't drift apart between them.
    """
    obj = model.objects.filter(uid=uid).first()
    if obj is None:
        return JsonResponse({'status': 'error', 'message': 'Record not found.'}, status=404)

    if not can_edit_amounts(request.user, obj):
        return JsonResponse(
            {'status': 'error', 'message': 'You do not have permission to edit amounts.'},
            status=403,
        )

    try:
        data = json.loads(request.body or b'{}')
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Malformed request.'}, status=400)

    field = data.get('field')
    if field not in ('amount', 'total_amount'):
        return JsonResponse({'status': 'error', 'message': 'That field is not editable.'}, status=400)

    raw = str(data.get('value', '')).strip().replace(',', '')
    try:
        value = Decimal(raw or '0')
    except InvalidOperation:
        return JsonResponse({'status': 'error', 'message': 'Enter a valid number.'}, status=400)

    if value < 0:
        return JsonResponse({'status': 'error', 'message': 'Amount cannot be negative.'}, status=400)

    total = obj.total_amount or Decimal('0')
    paid = obj.amount or Decimal('0')
    if field == 'amount' and value > total:
        return JsonResponse(
            {'status': 'error', 'message': f'Paid amount cannot exceed the total ({total:.2f}).'},
            status=400,
        )
    if field == 'total_amount' and value < paid:
        return JsonResponse(
            {'status': 'error', 'message': f'Total cannot be less than the paid amount ({paid:.2f}).'},
            status=400,
        )

    setattr(obj, field, value)
    obj._request_user = request.user
    obj._request = request
    obj._activity_message = f"Updated {field.replace('_', ' ')} inline to {value:.2f}"
    obj.save()

    return JsonResponse({
        'status': 'success',
        'field': field,
        'value': f'{value:.2f}',
        'total_amount': f'{(obj.total_amount or Decimal("0")):.2f}',
        'amount': f'{(obj.amount or Decimal("0")):.2f}',
    })


def assert_city_allowed(user, city):
    """
    True if `user` may access data scoped to `city` (used for
    city-parameterized bulk endpoints such as Excel exports). Superusers
    may request any city; managers only their own; everyone else, none.
    """
    if getattr(user, 'is_superuser', False):
        return True
    manager_city = get_manager_city(user)
    return bool(manager_city) and manager_city.strip().lower() == (city or '').strip().lower()


def validate_image(image):
    """ Validates the image file type and size. """
    if not image.name.lower().endswith(('.jpg', '.jpeg', '.png')):
        raise ValidationError("Only JPG, JPEG, and PNG files are allowed.")
    if image.size > 5 * 1024 * 1024:  # 5MB limit
        raise ValidationError("File size must be less than 5MB.")


def format_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
    except (ValueError, TypeError):
        return date_str  # fallback if already formatted or invalid input


# def get_next_numeric_sr_no():
#     last = (
#         Certificate.objects
#         .exclude(sr_no__isnull=True)
#         .exclude(sr_no__exact='')
#         .filter(sr_no__regex=r'^\d+$')  # only pure numeric
#         .order_by('-sr_no')
#         .first()
#     )
#     if last:
#         return str(int(last.sr_no) + 1)
#     return "1"


from django.db.models.functions import Cast
from django.db.models import IntegerField

def get_next_numeric_sr_no():
    try:
        last = (
            Certificate.objects
            .exclude(sr_no__isnull=True)
            .exclude(sr_no__exact='')
            .filter(sr_no__regex=r'^\d+$')  # ensures only numeric sr_no
            .annotate(sr_no_int=Cast('sr_no', IntegerField()))
            .order_by('-sr_no_int')
            .first()
        )
        if last and last.sr_no_int is not None:
            return str(last.sr_no_int + 1)
    except Exception as e:
        logger.error(f"get_next_numeric_sr_no failed: {e}")

    return "1"


def log_activity(user, action, request=None, ip_address=None, browser_info=None):
    """
    `request` is the normal path (extracts IP/browser from it). Pass
    `ip_address`/`browser_info` directly when logging from a background
    thread that has no live request object (e.g. after a request handler
    has already returned).
    """
    ip = ip_address
    browser = browser_info

    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        browser = request.META.get('HTTP_USER_AGENT', '')

    ActivityLog.objects.create(
        user=user,
        action=action,
        ip_address=ip,
        browser_info=browser
    )


def format_decimal(value):
    return float(Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if value else 0.0


_FORMULA_LEAD_CHARS = ('=', '+', '-', '@', '\t', '\r')


def safe_cell(value):
    """
    Neutralize spreadsheet formula injection: if a value that's about to be
    written into an Excel/CSV cell starts with a character a spreadsheet
    app would interpret as a formula trigger, prefix it with a leading
    apostrophe so it's forced to render as plain text instead of executing.
    """
    if isinstance(value, str) and value.startswith(_FORMULA_LEAD_CHARS):
        return "'" + value
    return value
