from django.db import models


class ScaleStatus(models.TextChoices):
    READY = "READY", "Ready"
    RUNNING = "RUNNING", "Running"
    ERROR = "ERROR", "Error"


class ScaleSettings(models.Model):

    scale_name = models.CharField(
        max_length=255,
        default="Scale 1"
    )

    scale_status = models.CharField(
        max_length=30,
        choices=ScaleStatus.choices,
        default=ScaleStatus.READY
    )

    tare_update_enabled = models.BooleanField(
        default=True
    )

    op_weight = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True
    )


    def __str__(self):
        return self.scale_name


    @classmethod
    def create_defaults(cls):
        cls.objects.get_or_create(
            scale_name="Scale 1"
        )
        
