from django.urls import path, include
from certificates import views

urlpatterns = [
    path('manage-certificates/', views.manage_certificates, name="manage_certificates"),
    path('report-certificates/', views.report_certificates, name="report_certificates"),
    path('add-certificate-manual/', views.add_certificate_manual, name='add_certificate_manual'),
    path('certificate/update/<uuid:uid>/', views.update_certificate, name='update_certificate'),
    path('pending_certificates/', views.pending_certificates, name="pending_certificates"),
    path('certificate/approve_reject/<uuid:uid>/', views.approve_reject_certificate, name='approve_reject_certificate'),
    path('export_certificate/<str:model_name>/<str:city>/', views.export_certificate_data_excel, name='export_certificate_and_city_excel'),
    path('certificate/<uuid:cert_uid>/pdf/', views.generate_certificate_pdf, name='generate_certificate_pdf'),
    path('unpaid-certificates/', views.unpaid_certificates, name="unpaid_certificates"),
    path('paid-certificates/', views.paid_certificates, name="paid_certificates"),
    path('report-paid-certificates/', views.report_paid_certificates, name="report_paid_certificates"),
    path('export/certificates/csv/', views.export_certificates_csv, name='export_certificates_csv'),
    path('certificate/update_unpaid/<uuid:uid>/', views.update_unpaid_certificate, name='update_unpaid_certificate'),
    path('cancelled-certificates/', views.cancelled_certificates, name="cancelled_certificates"),
    path('certificate/cancel/<uuid:uid>/', views.cancel_certificate, name='cancel_certificate'),
    path('certificate/activate/<uuid:uid>/', views.activate_certificate, name='activate_certificate'),
    path('holded-certificates/', views.holded_certificates, name="holded_certificates"),
    path('rejected-certificates/', views.rejected_certificates, name="rejected_certificates"),
    path('certificate/restore/<uuid:uid>/', views.restore_rejected_certificate, name="restore_rejected_certificate"),
    path('certificate/hold/<uuid:uid>/', views.hold_certificate, name='hold_certificate'),
    path('certificate/unhold/<uuid:uid>/', views.unhold_certificate, name='unhold_certificate'),

    path('certificate/update-field/<uuid:uid>/', views.update_certificate_field, name='update_certificate_field'),
]