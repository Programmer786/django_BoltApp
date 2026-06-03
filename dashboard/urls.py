from django.urls import path
from . import views  # or from dashboard import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload-all-data/', views.upload_all_data, name="upload_all_data"),
]