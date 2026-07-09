
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('main.urls', namespace='main')),
    path('', include('cam.urls', namespace='cam')),
    path('admin/', admin.site.urls),
]
