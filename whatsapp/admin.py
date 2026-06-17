from django.contrib import admin
from .models import WhatsAppContact, WhatsAppMessage, WhatsAppMessageLog


@admin.register(WhatsAppContact)
class WhatsAppContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'created_by', 'created_at')
    search_fields = ('name', 'phone')


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ('sent_by', 'message_type', 'mode', 'status', 'total_sent', 'total_failed', 'sent_at')
    list_filter = ('status', 'message_type', 'mode')


@admin.register(WhatsAppMessageLog)
class WhatsAppMessageLogAdmin(admin.ModelAdmin):
    list_display = ('phone', 'contact_name', 'status', 'sid')
    list_filter = ('status',)
