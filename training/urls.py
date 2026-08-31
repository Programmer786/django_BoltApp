from django.urls import path
from training import views

urlpatterns = [
    path('manage-training/', views.manage_training, name="manage_training"),
    path('report-training/', views.report_training, name="report_training"),
    path('export/training/csv/', views.export_training_csv, name='export_training_csv'),
    path('add-training-manual/', views.add_training_manual, name='add_training_manual'),
    path('training/update/<uuid:uid>/', views.update_training, name='update_training'),
    path('pending_training/', views.pending_training, name="pending_training"),
    path('training/approve_reject/<uuid:uid>/', views.approve_reject_training, name='approve_reject_training'),
    path('export_training/<str:model_name>/<str:city>/', views.export_training_data_excel, name='export_training_and_city_excel'),
    path('unpaid-training/', views.unpaid_training, name="unpaid_training"),
    path('paid-training/', views.paid_training, name="paid_training"),
    path('report-paid-training/', views.report_paid_training, name="report_paid_training"),
    path('training/update_unpaid/<uuid:uid>/', views.update_unpaid_training, name='update_unpaid_training'),
    path('cancelled-training/', views.cancelled_training, name="cancelled_training"),
    path('training/cancel/<uuid:uid>/', views.cancel_training, name='cancel_training'),
    path('training/activate/<uuid:uid>/', views.activate_training, name='activate_training'),
    path('holded-training/', views.holded_training, name="holded_training"),
    path('rejected-training/', views.rejected_training, name="rejected_training"),
    path('training/restore/<uuid:uid>/', views.restore_rejected_training, name="restore_rejected_training"),
    path('training/delete/<uuid:uid>/', views.delete_rejected_training, name="delete_rejected_training"),
    path('training/hold/<uuid:uid>/', views.hold_training, name='hold_training'),
    path('training/unhold/<uuid:uid>/', views.unhold_training, name='unhold_training'),
    path('training/update-field/<uuid:uid>/', views.update_training_field, name='update_training_field'),
]