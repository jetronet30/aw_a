from django.urls import path
from . import views

app_name = "proc"

urlpatterns = [
    path('porc/', views.process, name='process'),
    path("serial-stream/", views.serial_stream, name="serial_stream"),
]
