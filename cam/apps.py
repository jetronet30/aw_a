import os
import threading
import time

from django.apps import AppConfig


class CamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cam"
    verbose_name = "Camera Settings"

    def ready(self):

        if os.environ.get("RUN_MAIN") != "true":
            return

        def delayed_start():
            time.sleep(5)

            from .stream_manager import start_streams

            start_streams()

        threading.Thread(
            target=delayed_start,
            daemon=True
        ).start()
