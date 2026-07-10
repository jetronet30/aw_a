from django.shortcuts import get_object_or_404, redirect, render

from .forms import CamSettingsForm
from .models import CamSettings


def camera_settings(request, camera_id):
    camera = get_object_or_404(CamSettings, id=camera_id)

    if request.method == "POST":
        form = CamSettingsForm(request.POST, instance=camera)

        print("POST:", request.POST)

        if form.is_valid():
            obj = form.save()
            print("SAVED:", obj.id, obj.cam_name, obj.ip)

            return redirect(
                "cam:camera_settings",
                camera_id=camera.pk
            )

        else:
            print("ERRORS:", form.errors)

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


def camera_stream(request, camera_id):
    camera = get_object_or_404(CamSettings, id=camera_id)

    return redirect(f"/media/hls/cam_{camera.camera_no}/stream.m3u8")
