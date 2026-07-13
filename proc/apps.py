from django.apps import AppConfig
import os


class ProcConfig(AppConfig):
    name = 'proc'

    def ready(self):
        # runserver-ის autoreload-ის დროს ready() ორჯერ სრულდება
        # (მთავარი + reloader პროცესი). RUN_MAIN='true' მხოლოდ
        # ნამდვილ worker პროცესშია დაყენებული.
        if os.environ.get("RUN_MAIN") != "true":
            return

        # მნიშვნელოვანია: SerialReader(...) პირდაპირ არ იქმნება აქ.
        # get_reader() არის ერთადერთი წყარო — თუ send_start()/send_abort()
        # მოგვიანებით ცალკე იქმნიდა თავის SerialReader-ს (რადგან ready()-ში
        # პირდაპირი SerialReader(...).start() გლობალურ singleton-ს არ ავსებდა),
        # პორტს ორი დამოუკიდებელი SerialReader ცდილობდა ერთდროულად გახსნას —
        # სწორედ ეს იწვევდა "multiple access on port" შეცდომას.
        from .serial_reader import get_reader
        get_reader(port="/dev/ttyS0", baudrate=9600)
