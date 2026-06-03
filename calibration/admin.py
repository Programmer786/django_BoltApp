from django.contrib import admin
from core.base_admin import LoggingAdminMixin
from .models import Calibration

@admin.register(Calibration)
class CalibrationAdmin(LoggingAdminMixin, admin.ModelAdmin):
    list_display = (
        'cert_no', 'equipment_name', 'company_name', 'date_of_calibration',
        'expiry_date', 'validity', 'status', 'prepared_by', 'isApprove', 'isReject', 'view_activity_logs'
    )
    search_fields = (
        'cert_no', 'lh_serial_no', 'equipment_name', 'company_name',
        'technician', 'invoice_no', 'client_rep_name', 'client_rep_number'
    )
    list_filter = ('status', 'company_name', 'date_of_calibration', 'expiry_date')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')  # if inherited from BaseModel

    fieldsets = (
        ('Identification Info', {
            'fields': ('user', 'sr_no', 'lh_serial_no', 'cert_no', 'sticker_no')
        }),
        ('Activity Logs', {
            'classes': ('collapse', 'wide'),
            'fields': ('activity_logs',)
        }),
        ('Calibration Details', {
            'fields': (
                'equipment_name', 'company_name', 'received_on', 'technician',
                'date_of_calibration', 'expiry_date', 'validity', 'status', 'note'
            )
        }),
        ('Prepared & Waste Info', {
            'fields': ('prepared_by', 'wasted_serial')
        }),
        ('Financial & Client Info', {
            'fields': (
                'invoice_no', 'amount', 'cash_bank',
                'client_rep_name', 'client_rep_number', 'email', 'remarks'
            )
        }),
        ('Flags & Status', {
            'fields': ('isApprove', 'isReject', 'isActive', 'isCancel', 'isHold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
