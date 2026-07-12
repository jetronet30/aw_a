from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path("serial-stream/", views.serial_stream, name="serial_stream"),
]
