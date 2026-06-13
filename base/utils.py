import datetime
import logging
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
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


def log_activity(user, action, request=None):
    ip = None
    browser = None

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
