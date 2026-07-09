from django.urls import path
from . import views

app_name = 'cam'

urlpatterns = [
    path('cam/<int:camera_id>', views.camera_settings, name="camera_settings"),
]
