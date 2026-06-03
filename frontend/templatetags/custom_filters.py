from django import template
from datetime import datetime
from django.conf import settings

register = template.Library()

@register.filter(name='custom_date')
def custom_date(value):
    if not value:
        return "—"
    try:
        if isinstance(value, str):
            date_obj = datetime.strptime(value, '%Y-%m-%d')
        else:
            date_obj = value
        return date_obj.strftime('%d-%m-%Y')
    except:
        return value

@register.filter(name='hide_sensitive_date')
def hide_sensitive_date(value):
    """
    Hides sensitive date information based on settings.HIDE_SENSITIVE_DATES
    Set HIDE_SENSITIVE_DATES = False in settings.py to always show dates
    Set HIDE_SENSITIVE_DATES = True to hide dates
    If not set, defaults to True (hide dates) in production
    """
    # Default to hiding dates in production if not explicitly set
    hide_dates = getattr(settings, 'HIDE_SENSITIVE_DATES', not settings.DEBUG)
    
    if hide_dates:
        return "—"
    return custom_date(value)
