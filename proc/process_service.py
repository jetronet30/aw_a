from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Train, Wagon



class ProcessService:
    def create_train(self, scale_id=None,  scale_name=None, direction="OUT"):
        self._delete_all_not_closed_trains()
        return Train.objects.create(
            scale_id=scale_id,
            scale_name=scale_name,
            direction=direction
        )

    def close_train(self):
        train = self.get_last_not_closed_train()
        train.closed = True
        train.weighing_end_date = timezone.now()
        train.save()
        return train

    def set_direction(self, direction:str):
        train = self.get_last_not_closed_train()
        train.direction = direction
        train.save()
        return train

    def set_layout(self, layout:str):
        train = self.get_last_not_closed_train()
        train.layout = layout
        train.save()
        return train

    def add_wagon(self, row_number:int, gross_weight:Decimal):
        train = self.get_last_not_closed_train()
        return Wagon.objects.create(
            train=train,
            row_number=row_number,
            gross_weight=gross_weight,
            valid=True,
        )

    def get_last_not_closed_train(self):
        return Train.objects.filter(closed=False).order_by("-weighing_start_date").first()

    @transaction.atomic
    def _delete_all_not_closed_trains(self):
        trains = Train.objects.filter(closed=False)
        deleted_count, _ = trains.delete()
        return deleted_count
