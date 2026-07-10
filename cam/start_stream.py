"""
გამოყენება:
    python manage.py start_streams

ბაზიდან იღებს ყველა enabled=True კამერას (CamSettings) და თითოეულისთვის
ცალკე პროცესში უშვებს YOLO11 დეტექცია + HLS სტრიმინგს.

HLS გამოვა: MEDIA_ROOT/hls/cam_<camera_no>/stream.m3u8
"""
import logging
import signal
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from cam.models import CamSettings
from cam.worker import start_worker_process

logger = logging.getLogger("cameras.command")

CHECK_INTERVAL_SEC = 10  # რამდენ წამში ერთხელ ვამოწმებთ crash-ებსა და ახალ კამერებს


class Command(BaseCommand):
    help = "იწყებს YOLO11 დეტექციასა და HLS სტრიმინგს ყველა აქტიური კამერისთვის, პარალელურად"

    def handle(self, *args, **options):
        workers: dict[int, dict] = {}  # camera_no -> {"proc", "stop_event", "params", "output_dir"}
        running = True

        def handle_shutdown(signum, frame):
            nonlocal running
            self.stdout.write(self.style.WARNING("\nვჩერდები... ყველა worker-ის გამორთვა"))
            running = False

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        self._sync_workers(workers)

        try:
            while running:
                time.sleep(CHECK_INTERVAL_SEC)
                if not running:
                    break
                self._sync_workers(workers)
                self._restart_dead(workers)
        finally:
            for camera_no, info in workers.items():
                info["stop_event"].set()
            for camera_no, info in workers.items():
                info["proc"].join(timeout=10)
            self.stdout.write(self.style.SUCCESS("ყველა stream გაჩერებულია."))

    def _camera_params(self, cam: CamSettings) -> dict:
        return {
            "camera_no": cam.camera_no,
            "cam_name": cam.cam_name,
            "rtsp_url": cam.rtsp_url,
            "min_confidence": cam.min_confidence,
            "min_width": cam.min_width,
            "min_height": cam.min_height,
        }

    def _output_dir(self, camera_no: int) -> str:
        return str(settings.MEDIA_ROOT / "hls" / f"cam_{camera_no}")

    def _sync_workers(self, workers: dict):
        """ბაზასთან სინქრონიზაცია: ახალი/disabled კამერების დამატება-მოცილება."""
        active_cams = {c.camera_no: c for c in CamSettings.objects.filter(enabled=True)}

        # გაითიშა კამერა -> გავაჩეროთ მისი worker
        for camera_no in list(workers.keys()):
            if camera_no not in active_cams:
                self.stdout.write(f"[cam {camera_no}] გამორთულია ბაზაში, ვაჩერებ worker-ს")
                workers[camera_no]["stop_event"].set()
                workers[camera_no]["proc"].join(timeout=10)
                del workers[camera_no]

        # ახალი აქტიური კამერა -> ავუშვათ worker
        for camera_no, cam in active_cams.items():
            if camera_no not in workers:
                params = self._camera_params(cam)
                output_dir = self._output_dir(camera_no)
                proc, stop_event = start_worker_process(params, output_dir)
                workers[camera_no] = {
                    "proc": proc,
                    "stop_event": stop_event,
                    "params": params,
                    "output_dir": output_dir,
                }
                self.stdout.write(self.style.SUCCESS(
                    f"[cam {camera_no}] '{cam.cam_name}' worker გაეშვა (PID={proc.pid})"
                ))

    def _restart_dead(self, workers: dict):
        """თუ პროცესი crash-ით დასრულდა, თავიდან ვუშვებთ."""
        for camera_no, info in list(workers.items()):
            if not info["proc"].is_alive():
                self.stdout.write(self.style.WARNING(
                    f"[cam {camera_no}] worker მოულოდნელად შეჩერდა, ვუშვებ თავიდან"
                ))
                proc, stop_event = start_worker_process(info["params"], info["output_dir"])
                workers[camera_no]["proc"] = proc
                workers[camera_no]["stop_event"] = stop_event
