from django.contrib import admin
from core.base_admin import LoggingAdminMixin
from .models import Card


@admin.register(Card)
class CardAdmin(LoggingAdminMixin, admin.ModelAdmin):
    list_display = (
        'card_no', 'iqama_no', 'operator_name', 'company_name',
        'issue_date', 'expiry_date', 'status', 'prepared_by', 'user', 'isApprove', 'isReject', 'view_activity_logs'
    )
    search_fields = ('card_no', 'iqama_no', 'operator_name', 'company_name', 'client_rep_name')
    list_filter = ('status', 'company_name', 'issue_date', 'expiry_date')
    readonly_fields = ('created_at', 'updated_at')  # Assuming BaseModel adds these fields
    ordering = ('-created_at',)

    # Optional: for better field grouping in detail view
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'sr_no', 'card_no', 'iqama_no', 'operator_name', 'company_name')
        }),
        ('Activity Logs', {
            'classes': ('collapse', 'wide'),
            'fields': ('activity_logs',)
        }),
        ('Validity & Status', {
            'fields': ('issue_date', 'expiry_date', 'remaining_months', 'status', 'note')
        }),
        ('Assessment & Approval', {
            'fields': ('trade', 'holo_gram_no', 'assessed_by', 'wasted_serial', 'requested_by', 'prepared_by')
        }),
        ('Financials & Client Info', {
            'fields': ('invoice_no', 'amount', 'cash_bank', 'client_rep_name', 'client_rep_number', 'email', 'remarks')
        }),
        ('Flags & Status', {
            'fields': ('isApprove', 'isReject', 'isActive', 'isCancel', 'isHold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
