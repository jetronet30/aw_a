from django.shortcuts import render
from cam.models import CamSettings


def index(request):

    cameras = CamSettings.objects.all()

    return render(request, "main.html", {
        "cameras": cameras
    })
