from django.urls import path
from . import views

urlpatterns = [
    path('whatsapp/contacts/', views.whatsapp_contacts, name='whatsapp_contacts'),
    path('whatsapp/contacts/add/', views.add_contact, name='whatsapp_add_contact'),
    path('whatsapp/contacts/upload/', views.upload_contacts_excel, name='whatsapp_upload_contacts'),
    path('whatsapp/contacts/<int:contact_id>/edit/', views.edit_contact, name='whatsapp_edit_contact'),
    path('whatsapp/contacts/<int:contact_id>/delete/', views.delete_contact, name='whatsapp_delete_contact'),
    path('whatsapp/contacts/bulk-delete/', views.bulk_delete_contacts, name='whatsapp_bulk_delete_contacts'),
    path('whatsapp/contacts/bulk-category/', views.bulk_assign_category, name='whatsapp_bulk_assign_category'),
    path('whatsapp/categories/add/', views.add_category, name='whatsapp_add_category'),
    path('whatsapp/categories/<int:category_id>/rename/', views.rename_category, name='whatsapp_rename_category'),
    path('whatsapp/categories/<int:category_id>/delete/', views.delete_category, name='whatsapp_delete_category'),
    path('whatsapp/categories/<int:category_id>/delete-contacts/', views.delete_category_contacts, name='whatsapp_delete_category_contacts'),
    path('whatsapp/send/', views.send_message, name='whatsapp_send'),
    path('whatsapp/message/<int:message_id>/status/', views.whatsapp_message_status, name='whatsapp_message_status'),
    path('whatsapp/message/<int:message_id>/retry/', views.retry_failed_message, name='whatsapp_retry_failed_message'),
    path('whatsapp/history/delete/', views.delete_history, name='whatsapp_delete_history'),
    path('whatsapp/web-status/', views.whatsapp_web_status, name='whatsapp_web_status'),
]
