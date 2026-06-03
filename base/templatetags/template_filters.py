from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """
    Replace or add a URL parameter while keeping existing parameters intact.
    Usage: {% url_replace request 'param_name' 'param_value' %}
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()

@register.filter
def default_empty(value, default=''):
    """
    Returns an empty string if the input is None or an empty string.
    Usage: {{ value|default_empty }}
    """
    if value is None or str(value).strip() == '':
        return default
    return value
