from django.urls import path

from . import views

urlpatterns = [
    path('whatsapp/verification/', views.verification_page, name='wa_bot_page'),
    path('whatsapp/verification/status/', views.status_json, name='wa_bot_status'),
    path('whatsapp/verification/settings/', views.save_settings, name='wa_bot_save_settings'),
    path('whatsapp/verification/test/', views.test_message, name='wa_bot_test'),
    path('whatsapp/verification/relink/', views.relink, name='wa_bot_relink'),
    # Called by the WhatsApp listener container (shared X-Bot-Key header).
    path('wa-bot/api/incoming/', views.api_incoming, name='wa_bot_api_incoming'),
    path('wa-bot/api/status/', views.api_status, name='wa_bot_api_status'),
]
