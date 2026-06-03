from django.urls import path
from frontend import views


urlpatterns = [
    path('verification', views.verify_data, name='verify_data'),
]