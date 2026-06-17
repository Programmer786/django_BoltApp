from django.urls import path
from . import views

urlpatterns = [
    path('whatsapp/contacts/', views.whatsapp_contacts, name='whatsapp_contacts'),
    path('whatsapp/contacts/upload/', views.upload_contacts_excel, name='whatsapp_upload_contacts'),
    path('whatsapp/contacts/<int:contact_id>/delete/', views.delete_contact, name='whatsapp_delete_contact'),
    path('whatsapp/send/', views.send_message, name='whatsapp_send'),
]
