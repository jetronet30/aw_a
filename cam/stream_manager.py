import logging
import signal
import threading
import time

from django.conf import settings

from .models import CamSettings
from .worker import start_worker_process

logger = logging.getLogger("cameras.stream")
CHECK_INTERVAL_SEC = 10
def start_streams():
    workers: dict[int, dict] = {}
    stop_event = threading.Event()

    def handle_shutdown(signum, frame):
        logger.warning("ვჩერდები... ყველა worker-ის გამორთვა")
        stop_event.set()
    # signal მუშაობს მხოლოდ მთავარ thread-ში
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

    sync_workers(workers)

    try:
        while not stop_event.is_set():
            time.sleep(CHECK_INTERVAL_SEC)
            if stop_event.is_set():
                break
            sync_workers(workers)
            restart_dead(workers)

    finally:
        logger.warning("worker-ების გაჩერება...")
        for info in workers.values():
            info["stop_event"].set()

        for info in workers.values():
            info["proc"].join(timeout=10)
        logger.info("ყველა stream გაჩერებულია.")




def camera_params(cam: CamSettings) -> dict:

    return {
        "camera_no": cam.camera_no,
        "cam_name": cam.cam_name,
        "rtsp_url": cam.rtsp_url,
        "min_confidence": cam.min_confidence,
        "min_width": cam.min_width,
        "min_height": cam.min_height,
    }


def output_dir(camera_no: int) -> str:

    return str(
        settings.MEDIA_ROOT /
        "hls" /
        f"cam_{camera_no}"
    )


def sync_workers(workers: dict):

    active_cams = {
        c.camera_no: c
        for c in CamSettings.objects.filter(enabled=True)
    }


    # კამერა გაითიშა ბაზაში
    for camera_no in list(workers.keys()):
        if camera_no not in active_cams:
            logger.warning(
                f"Camera {camera_no} disabled, stopping worker"
            )
            workers[camera_no]["stop_event"].set()
            workers[camera_no]["proc"].join(timeout=10)
            del workers[camera_no]
    # ახალი კამერა
    for camera_no, cam in active_cams.items():

        if camera_no not in workers:
            params = camera_params(cam)
            out = output_dir(camera_no)
            proc, worker_stop_event = start_worker_process(
                params,
                out
            )
            workers[camera_no] = {
                "proc": proc,
                "stop_event": worker_stop_event,
                "params": params,
                "output_dir": out,
            }
            logger.info(
                f"Camera {camera_no} '{cam.cam_name}' started PID={proc.pid}"
            )




def restart_dead(workers: dict):
    for camera_no, info in list(workers.items()):
        if not info["proc"].is_alive():
            logger.warning(
                f"Camera {camera_no} worker crashed, restarting"
            )
            proc, worker_stop_event = start_worker_process(
                info["params"],
                info["output_dir"]
            )
            workers[camera_no]["proc"] = proc
            workers[camera_no]["stop_event"] = worker_stop_event
