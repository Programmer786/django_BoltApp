from django.contrib import admin
from core.base_admin import LoggingAdminMixin
from .models import NonDestructiveTesting

@admin.register(NonDestructiveTesting)
class NonDestructiveTestingAdmin(LoggingAdminMixin, admin.ModelAdmin):
    list_display = (
        'report_no', 'company_name', 'material', 'inspection_type', 'inspection_date',
        'expiry_date', 'status', 'prepared_by', 'isApprove', 'isReject', 'view_activity_logs'
    )
    search_fields = (
        'report_no', 'lh_serial_no', 'material', 'structure_description',
        'company_name', 'invoice_no', 'client_rep_name', 'client_rep_number'
    )
    list_filter = ('inspection_type', 'status', 'company_name', 'inspection_date', 'expiry_date')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')  # if BaseModel includes these

    fieldsets = (
        ('General Information', {
            'fields': ('user', 'sr_no', 'lh_serial_no', 'report_no', 'material', 'structure_description', 'inspection_type')
        }),
        ('Activity Logs', {
            'classes': ('collapse', 'wide'),
            'fields': ('activity_logs',)
        }),
        ('Inspection Details', {
            'fields': ('inspection_date', 'expiry_date', 'remaining_months', 'joint_type', 'inspected_by', 'status', 'note')
        }),
        ('Approval and Preparation', {
            'fields': ('prepared_by', 'wasted_serial', 'approved_by')
        }),
        ('Financial Information', {
            'fields': ('invoice_no', 'amount', 'cash_bank')
        }),
        ('Client Contact Information', {
            'fields': ('client_rep_name', 'client_rep_number', 'email', 'remarks')
        }),
        ('Flags & Status', {
            'fields': ('isApprove', 'isReject', 'isActive', 'isCancel', 'isHold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
