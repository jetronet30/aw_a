from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render

from .serial_reader import latest_serial_value
from .serial_reader import send_start, send_abort

HEARTBEAT_INTERVAL = 15  # წმ — proxy/nginx timeout-ის თავიდან ასაცილებლად


def process(request):

    if request.method == "POST":

        action = request.POST.get("action")

        print("ACTION:", action)

        if action == "start":
            send_start()
            print("START")

        elif action == "abort":
            send_abort()
            print("ABORT")


        return JsonResponse({
            "status": "ok",
            "command": action
        })


    return render(request, "proc/process.html")




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
