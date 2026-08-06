from django.urls import path
from . import views

urlpatterns = [
    path('whatsapp/contacts/', views.whatsapp_contacts, name='whatsapp_contacts'),
    path('whatsapp/contacts/add/', views.add_contact, name='whatsapp_add_contact'),
    path('whatsapp/contacts/upload/', views.upload_contacts_excel, name='whatsapp_upload_contacts'),
    path('whatsapp/contacts/<int:contact_id>/edit/', views.edit_contact, name='whatsapp_edit_contact'),
    path('whatsapp/contacts/<int:contact_id>/delete/', views.delete_contact, name='whatsapp_delete_contact'),
    path('whatsapp/send/', views.send_message, name='whatsapp_send'),
    path('whatsapp/message/<int:message_id>/status/', views.whatsapp_message_status, name='whatsapp_message_status'),
    path('whatsapp/history/delete/', views.delete_history, name='whatsapp_delete_history'),
    path('whatsapp/web-status/', views.whatsapp_web_status, name='whatsapp_web_status'),
]
