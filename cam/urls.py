from django.urls import path
from . import views

app_name = "cam"

urlpatterns = [
    path("cam/<int:camera_id>", views.camera_settings, name="camera_settings"),
    path("cam/<int:camera_id>/stream.m3u8", views.camera_stream, name="camera_stream"),
]
