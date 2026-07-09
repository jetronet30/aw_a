from cam.models import CamSettings


def cameras_menu(request):

    return {
        "cameras": CamSettings.objects.all()
    }
