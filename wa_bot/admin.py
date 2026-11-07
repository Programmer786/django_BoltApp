from django.contrib import admin

from .models import BotConversation, BotSettings, BotState


@admin.register(BotConversation)
class BotConversationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'phone', 'name', 'result', 'matched_type', 'matched_number', 'used_ai', 'response_ms')
    list_filter = ('result', 'used_ai')
    search_fields = ('phone', 'name', 'matched_number', 'message')


admin.site.register(BotSettings)
admin.site.register(BotState)
