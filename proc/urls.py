from django.urls import path
from . import views

app_name = "proc"

urlpatterns = [
    path('porc/', views.process, name='process'),
]
