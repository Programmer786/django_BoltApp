from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe


@admin.register(LogEntry)
class CentralLogEntryAdmin(admin.ModelAdmin):
    """
    Centralized logging admin for all models.
    Accessible at /admin/admin/logentry/
    """
    list_display = ['__str__', 'action_time', 'user', 'content_type', 'object_link', 'change_message']
    list_filter = ['action_time', 'user', 'content_type']
    search_fields = ['object_repr', 'change_message', 'user__username']
    date_hierarchy = 'action_time'
    readonly_fields = ['action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def object_link(self, obj):
        if obj.is_deletion() or not obj.get_admin_url():
            return obj.object_repr
        try:
            model = obj.content_type.model_class()
            if model and hasattr(model, 'uid'):
                # For UUID-based models
                obj_id = str(obj.object_id).replace('-', '').lower()
                return format_html('<a href="{}">{}</a>', 
                                 f"{obj.get_admin_url()}?id={obj_id}",
                                 obj.object_repr)
            return format_html('<a href="{}">{}</a>', obj.get_admin_url(), obj.object_repr)
        except Exception:
            return obj.object_repr
    object_link.short_description = 'Object'
    object_link.admin_order_field = 'object_repr'
