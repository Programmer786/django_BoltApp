from django.urls import path
from calibration import views

urlpatterns = [
    path('manage-calibration/', views.manage_calibration, name="manage_calibration"),
    path('add-calibration-manual/', views.add_calibration_manual, name='add_calibration_manual'),
    path('calibration/update/<uuid:uid>/', views.update_calibration, name='update_calibration'),
    path('pending_calibration/', views.pending_calibration, name="pending_calibration"),
    path('rejected-calibration/', views.rejected_calibration, name="rejected_calibration"),
    path('calibration/restore/<uuid:uid>/', views.restore_rejected_calibration, name="restore_rejected_calibration"),
    path('calibration/delete/<uuid:uid>/', views.delete_rejected_calibration, name="delete_rejected_calibration"),
    path('calibration/approve_reject/<uuid:uid>/', views.approve_reject_calibration, name='approve_reject_calibration'),
    path('export_calibration/<str:model_name>/<str:city>/', views.export_calibration_data_excel, name='export_calibration_and_city_excel'),
    path('unpaid-calibration/', views.unpaid_calibration, name="unpaid_calibration"),
    path('paid-calibration/', views.paid_calibration, name="paid_calibration"),
    path('calibration/update_unpaid/<uuid:uid>/', views.update_unpaid_calibration, name='update_unpaid_calibration'),
    path('report-calibration/', views.report_calibration, name="report_calibration"),
    path('report-paid-calibration/', views.report_paid_calibration, name="report_paid_calibration"),
    path('calibration/update-field/<uuid:uid>/', views.update_calibration_field, name='update_calibration_field'),
]