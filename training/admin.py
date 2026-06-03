from django.contrib import admin
from core.base_admin import LoggingAdminMixin
from .models import Training

@admin.register(Training)
class TrainingAdmin(LoggingAdminMixin, admin.ModelAdmin):
    list_display = (
        'card_no', 'cert_no', 'name_of_trainee', 'company_name',
        'issue_date', 'expiry_date', 'status', 'prepared_by', 'isApprove', 'isReject', 'view_activity_logs'
    )
    search_fields = (
        'card_no', 'cert_no', 'name_of_trainee', 'company_name',
        'iqama_no', 'client_rep_name', 'client_rep_number', 'invoice_no'
    )
    list_filter = ('status', 'company_name', 'issue_date', 'expiry_date')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')  # From BaseModel if included

    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'sr_no', 'card_no', 'cert_no', 'name_of_trainee', 'company_name', 'iqama_no')
        }),
        ('Activity Logs', {
            'classes': ('collapse', 'wide'),
            'fields': ('activity_logs',)
        }),
        ('Dates & Status', {
            'fields': ('issue_date', 'expiry_date', 'remaining_months', 'status', 'note')
        }),
        ('Trade & Assessment', {
            'fields': ('trade', 'holo_gram_no', 'assessed_by_resource_person')
        }),
        ('Request & Preparation', {
            'fields': ('requested_by', 'prepared_by', 'wasted_serial')
        }),
        ('Financial Info', {
            'fields': ('invoice_no', 'amount', 'cash_bank')
        }),
        ('Client Contact Info', {
            'fields': ('client_rep_name', 'client_rep_number', 'email', 'remarks')
        }),
        ('Flags & Status', {
            'fields': ('isApprove', 'isReject', 'isActive', 'isCancel', 'isHold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
