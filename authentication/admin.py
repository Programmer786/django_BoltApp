from django.contrib import admin
from .models import Profile
from .models import ActivityLog
from .models import Note

# Register Profile directly
admin.site.register(Profile)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'ip_address', 'browser_info')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'action', 'ip_address')


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('type', 'note', 'created_at', 'updated_at')
    list_filter = ('type',)
    search_fields = ('type', 'note')