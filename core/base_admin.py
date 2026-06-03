from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class LoggingAdminMixin:
    """
    Mixin to add logging functionality to admin classes
    """
    def view_activity_logs(self, obj):
        content_type = ContentType.objects.get_for_model(obj).id
        return format_html(
            '<a class="button" href="{}?content_type__id__exact={}&object_id__exact={}">View Logs</a>',
            reverse('admin:admin_logentry_changelist'),
            content_type,
            str(obj.uid)
        )
    view_activity_logs.short_description = 'Activity Logs'
    view_activity_logs.allow_tags = True

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if 'activity_logs' not in readonly_fields:
            readonly_fields.append('activity_logs')
        return readonly_fields

    def activity_logs(self, obj):
        from django.contrib.admin.models import LogEntry
        content_type = ContentType.objects.get_for_model(obj)
        log_entries = LogEntry.objects.filter(
            content_type=content_type,
            object_id=str(obj.uid)
        ).order_by('-action_time')
        
        log_lines = []
        for entry in log_entries:
            action_flag = 'CHANGE'
            if entry.is_addition():
                action_flag = 'ADDITION'
            elif entry.is_deletion():
                action_flag = 'DELETION'
                
            log_lines.append(
                f'<div class="log-entry">'
                f'<div><strong>{entry.action_time}</strong> - <span class="log-user">{entry.user}</span></div>'
                f'<div class="log-action log-{action_flag.lower()}">{action_flag}</div>'
                f'<div class="log-message">{entry.change_message or "No details provided"}</div>'
                f'</div>'
            )
        
        return mark_safe('<div class="log-entries">' + '\n'.join(log_lines) + '</div>')
    activity_logs.short_description = 'Activity Logs'
    activity_logs.allow_tags = True

    class Media:
        css = {
            'all': ('admin/css/log_entries.css',)
        }
