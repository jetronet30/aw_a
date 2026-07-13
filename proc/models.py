from decimal import Decimal
from django.db import models


# ==========================================================
# ENUMS
# ==========================================================

class WeighingMethod(models.TextChoices):
    DYNAMIC = "DYNAMIC", "Dynamic"
    STATIC = "STATIC", "Static"


class WagonType(models.TextChoices):
    BASIC = "BASIC", "Basic"
    # დაამატე საჭირო ტიპები აქ


# ==========================================================
# TRAIN MODEL
# ==========================================================

class Train(models.Model):
    scale_id = models.BigIntegerField(null=True, blank=True)
    scale_process_id = models.CharField(max_length=255, null=True, blank=True)
    scale_name = models.CharField(max_length=255, null=True, blank=True)

    weighing_start_date = models.DateTimeField(auto_now_add=True)
    weighing_end_date = models.DateTimeField(null=True, blank=True)
    up_date_time = models.DateTimeField(null=True, blank=True)

    gross_weight = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    actual_tare = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    actual_neto = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    valid_tare = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    valid_neto = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)

    max_speed = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.0"))
    min_speed = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.0"))

    direction = models.CharField(max_length=10, default="OUT")
    layout = models.CharField(max_length=255, null=True, blank=True)

    weighing_method = models.CharField(
        max_length=30,
        choices=WeighingMethod.choices,
        default=WeighingMethod.DYNAMIC
    )

    # Flags
    done = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    actual_matched = models.BooleanField(default=False)
    valid_matched = models.BooleanField(default=False)
    numbered = models.BooleanField(default=False)
    over_load = models.BooleanField(default=False)
    over_speed = models.BooleanField(default=False)
    commercial = models.BooleanField(default=False)
    technical_safety = models.BooleanField(default=False)

    # Video paths
    video_path_1 = models.CharField(max_length=500, null=True, blank=True)
    video_path_2 = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        ordering = ["-weighing_start_date"]

    @property
    def wagon_count(self):
        return self.wagons.count()

    def __str__(self):
        return f"{self.scale_name} #{self.id}"


# ==========================================================
# WAGON MODEL
# ==========================================================

class Wagon(models.Model):
    scale_id = models.BigIntegerField(null=True, blank=True)
    scale_name = models.CharField(max_length=255, null=True, blank=True)

    wagon_type = models.CharField(
        max_length=30,
        choices=WagonType.choices,
        default=WagonType.BASIC
    )

    axle = models.IntegerField(default=4)
    wagon_number = models.CharField(max_length=20, null=True, blank=True)
    row_number = models.IntegerField(null=True, blank=True)
    wagon_description = models.CharField(max_length=500, null=True, blank=True)

    weighing_date = models.DateTimeField(auto_now_add=True)
    product_code = models.CharField(max_length=20, null=True, blank=True)

    gross_weight = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    valid_tare = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    actual_tare = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)

    speed = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.0"))

    # Flags
    valid = models.BooleanField(default=False)
    overload = models.BooleanField(default=False)
    over_speed = models.BooleanField(default=False)

    train = models.ForeignKey(
        Train,
        related_name="wagons",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["row_number"]
        constraints = [
            models.UniqueConstraint(fields=["train", "row_number"], name="unique_train_row"),
            models.UniqueConstraint(fields=["train", "wagon_number"], name="unique_train_wagon_number"),
        ]

    @property
    def actual_neto_calculated(self):
        if not self.gross_weight or not self.actual_tare or self.actual_tare == Decimal("0"):
            return Decimal("0")
        return self.gross_weight - self.actual_tare

    @property
    def valid_neto_calculated(self):
        if not self.gross_weight or not self.valid_tare or self.valid_tare == Decimal("0"):
            return Decimal("0")
        return self.gross_weight - self.valid_tare

    def __str__(self):
        return self.wagon_number or f"Wagon #{self.id}"
