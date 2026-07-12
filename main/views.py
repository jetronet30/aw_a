from django.http import StreamingHttpResponse
from django.shortcuts import render
from cam.models import CamSettings
from .serial_reader import latest_serial_value

HEARTBEAT_INTERVAL = 15  # წმ — proxy/nginx timeout-ის თავიდან ასაცილებლად


def index(request):
    cameras = CamSettings.objects.all()
    return render(request, "main.html", {"cameras": cameras})


def serial_stream(request):
    def event_stream():
        # ბრაუზერების ადრეული ბუფერიზაციის თავიდან ასაცილებლად
        yield (":" + " " * 2048 + "\n\n").encode("utf-8")

        # პირველივე დაკავშირებაზე მაშინვე გავაგზავნოთ არსებული ბოლო მნიშვნელობა
        value, last_version = latest_serial_value.wait_for_update(-1, timeout=0.01)
        if value is not None:
            yield f"data: {value}\n\n".encode("utf-8")

        while True:
            value, version = latest_serial_value.wait_for_update(
                last_version, timeout=HEARTBEAT_INTERVAL
            )
            if version != last_version:
                last_version = version
                yield f"data: {value}\n\n".encode("utf-8")
            else:
                yield b": heartbeat\n\n"  # კავშირის შენარჩუნება

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
