from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Replace or add URL parameters while keeping existing parameters intact.
    Usage: {% load url_utils %}
           <a href="?{% url_replace request page=page_obj.next_page_number %}">Next</a>
    """
    query = context['request'].GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    return query.urlencode()
