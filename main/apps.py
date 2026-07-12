from django.apps import AppConfig
import os


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'


    def ready(self):
        # runserver-ის autoreload-ის დროს ready() ორჯერ სრულდება (მთავარი + reloader პროცესი).
        # RUN_MAIN='true' მხოლოდ ნამდვილ worker პროცესშია დაყენებული.
        if os.environ.get("RUN_MAIN") != "true":
            return

        from .serial_reader import SerialReader
        SerialReader(port="/dev/ttyS0", baudrate=9600).start()
