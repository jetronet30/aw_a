from django.shortcuts import render
from .models import CamSettings

def camera_settings(request):

    CamSettings.create_defaults()

    cameras = CamSettings.objects.all()

    return render(request, "cam/camsettings.html", {
        "cameras": cameras
    })
