from django.db import models


class CamSettings(models.Model):
    camera_no = models.PositiveSmallIntegerField(unique=True)

    enabled = models.BooleanField(default=True)

    cam_name = models.CharField(max_length=100)

    ip = models.GenericIPAddressField(default="192.168.1.100")

    rtsp_port = models.PositiveIntegerField(default=554)

    username = models.CharField(max_length=100, blank=True)

    password = models.CharField(max_length=100, blank=True)

    rtsp_path = models.CharField(
        max_length=255,
        default="/Streaming/Channels/101"
    )

    class Meta:
        ordering = ["camera_no"]

    def __str__(self):
        return self.cam_name

    @classmethod
    def create_defaults(cls):
        defaults = [
            {
                "camera_no": 1,
                "cam_name": "Camera 1",
                "enabled": True,
                "ip": "192.168.1.101",
            },
            {
                "camera_no": 2,
                "cam_name": "Camera 2",
                "enabled": True,
                "ip": "192.168.1.102",
            },
        ]

        for camera in defaults:
            cls.objects.get_or_create(
                camera_no=camera["camera_no"],
                defaults=camera
            )
