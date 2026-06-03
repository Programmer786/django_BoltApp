from django.contrib import admin
from core.base_admin import LoggingAdminMixin
from .models import Certificate

@admin.register(Certificate)
class CertificateAdmin(LoggingAdminMixin, admin.ModelAdmin):
    list_display = (
        'cert_no', 'company_name', 'equipment_type', 'inspection_date',
        'expiry_date', 'status', 'prepared_by', 'user',
        'isApprove', 'isReject', 'isCancel', 'isActive', 'created_at', 'view_activity_logs'
    )
    search_fields = (
        'cert_no', 'company_name', 'eq_serial_no', 'plate_no',
        'invoice_no', 'client_rep_name', 'client_rep_number'
    )
    list_filter = (
        'status', 'equipment_type', 'inspection_date', 'expiry_date',
        'isApprove', 'isReject', 'isActive'
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def get_urls(self):
        from django.urls import path
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponseRedirect
        
        def certificate_detail_view(request, uid):
            cert = get_object_or_404(Certificate, uid=uid)
            return HttpResponseRedirect(
                reverse('admin:certificates_certificate_change', args=(cert.uid,))
            )
            
        urls = super().get_urls()
        custom_urls = [
            path(
                'certificate/<uuid:uid>/',
                self.admin_site.admin_view(certificate_detail_view),
                name='certificate-detail',
            ),
        ]
        return custom_urls + urls
        
    fieldsets = (
        ('Certificate Info', {
            'fields': (
                'user', 'sr_no', 'lh_serial_no', 'cert_no', 'sticker_no',
                'eq_serial_no', 'equipment_type', 'company_name'
            )
        }),
        ('Project & Location Details', {
            'fields': (
                'project_location', 'plate_no', 'manufacturer', 'inspected_by',
                'reference_standard', 'type_model_year', 'bucket_capacity',
            )
        }),
        ('Dates & Status', {
            'fields': (
                'inspection_date', 'date_of_report', 'date_of_last_inspection',
                'expiry_date', 'remaining_months', 'status', 'note'
            )
        }),
        ('Client & Financial Info', {
            'fields': (
                'invoice_no', 'amount', 'cash_bank',
                'client_rep_name', 'client_rep_number', 'email', 'remarks'
            )
        }),
        ('Summary & Remarks', {
            'fields': (
                'summary_description_1', 'summary_result_1', 'summary_comments_1',
                'summary_description_2', 'summary_result_2', 'summary_comments_2',
                'summary_description_3', 'summary_result_3', 'summary_comments_3',
            )
        }),
        ('Prepared & Waste Info', {
            'fields': ('prepared_by', 'wasted_serial')
        }),
        ('Flags & Status', {
            'fields': ('isApprove', 'isReject', 'isActive', 'isCancel', 'isHold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
        ('Activity Logs', {
            'classes': ('collapse', 'wide'),
            'fields': ('activity_logs',)
        }),
    )
