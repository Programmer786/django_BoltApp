from django.urls import path
from ndt import views

urlpatterns = [
    path('manage-ndt/', views.manage_ndt, name="manage_ndt"),
    path('add-ndt-manual/', views.add_ndt_manual, name='add_ndt_manual'),
    path('ndt/update/<uuid:uid>/', views.update_ndt, name='update_ndt'),
    path('pending_ndt/', views.pending_ndt, name="pending_ndt"),
    path('rejected-ndt/', views.rejected_ndt, name="rejected_ndt"),
    path('ndt/restore/<uuid:uid>/', views.restore_rejected_ndt, name="restore_rejected_ndt"),
    path('ndt/approve_reject/<uuid:uid>/', views.approve_reject_ndt, name='approve_reject_ndt'),
    path('export_ndt/<str:model_name>/<str:city>/', views.export_ndt_data_excel, name='export_ndt_and_city_excel'),
    path('unpaid-ndt/', views.unpaid_ndt, name="unpaid_ndt"),
    path('paid-ndt/', views.paid_ndt, name="paid_ndt"),
    path('ndt/update_unpaid/<uuid:uid>/', views.update_unpaid_ndt, name='update_unpaid_ndt'),
    path('report-ndt/', views.report_ndt, name="report_ndt"),
    path('report-paid-ndt/', views.report_paid_ndt, name="report_paid_ndt"),
    path('ndt/update-field/<uuid:uid>/', views.update_ndt_field, name='update_ndt_field'),
]