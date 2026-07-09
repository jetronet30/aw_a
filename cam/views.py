from django.shortcuts import get_object_or_404, redirect, render

from .forms import CamSettingsForm
from .models import CamSettings


def camera_settings(request, camera_id):
    camera = get_object_or_404(CamSettings, id=camera_id)

    if request.method == "POST":
        form = CamSettingsForm(request.POST, instance=camera)

        if form.is_valid():
            form.save()
            return redirect("cam:camera_settings", camera_id=camera.pk)
    else:
        form = CamSettingsForm(instance=camera)

    return render(
        request,
        "cam/camera.html",
        {
            "form": form,
            "camera": camera,
        }
    )

