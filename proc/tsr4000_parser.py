from decimal import Decimal
import logging
from threading import Lock
from .process_service import ProcessService


from .models import Train, Wagon

logger = logging.getLogger(__name__)


class ParserState:

    def __init__(self):
        self.train_id = None
        self.sys_process_id = None
        self.wheel_weights = {}
        self.lock = Lock()



class Tsr4000ParserDynamic:

    def __init__(self):

        # scale_id -> ParserState
        self.states = {}


    def get_state(self, scale_id):
        if scale_id not in self.states:
            self.states[scale_id] = ParserState()
        return self.states[scale_id]


    def parse(self, scale, raw_data):

        raw_data = raw_data.strip()

        prefix = raw_data[:2]

        state = self.get_state(scale.id)


        try:
            # ===============================
            # CSTART
            # ===============================

            if "cstart" in raw_data.lower():

                with state.lock:

                    state.wheel_weights.clear()

                    train = ProcessService().create_train(
                        scale_id=scale.id,
                        scale_name=scale.scale_name,
                        direction="OUT"
                    )

                    state.train_id = train.id


                logger.info(
                    "START scale=%s train=%s",
                    scale.scale_name,
                    train.id
                )


                return self.format_response(prefix)



            # ===============================
            # W TYPE
            # ===============================

            elif len(raw_data) > 2 and raw_data[2] == "W":


                wheel_number = raw_data[11:13]

                raw_weight = raw_data[13:18]


                weight = (
                    Decimal(raw_weight)
                    .scaleb(-3)
                )
                row = self.get_row_num(
                    wheel_number
                )
                state.wheel_weights[row] = weight
                return self.format_response(prefix)

            # ===============================
            # V TYPE
            # ===============================

            elif len(raw_data) > 2 and raw_data[2] == "V":


                state.sys_process_id = raw_data[3:8]


                row_num = self.get_row_num(
                    raw_data[8:11]
                )


                weight = self.get_weight(
                    raw_data[11:17]
                )


                speed_axle = self.extract_speed_axle(
                    raw_data
                )


                speed = Decimal("0")


                if speed_axle:
                    speed = self.get_speed(
                        speed_axle[:6]
                    )


                Wagon.objects.create(
                    train_id=state.train_id,
                    row_number=row_num,
                    gross_weight=weight,
                    speed=speed
                )


                logger.info(
                    "WAGON row=%s weight=%s speed=%s",
                    row_num,
                    weight,
                    speed
                )
                state.wheel_weights.clear()
                return self.format_response(prefix)



            # ===============================
            # G TYPE
            # ===============================

            elif len(raw_data) > 2 and raw_data[2] == "G":


                state.sys_process_id = raw_data[3:8]


                full_weight = self.get_weight(
                    raw_data[8:16]
                )


                train = Train.objects.filter(
                    id=state.train_id
                ).first()


                if train:

                    train.done = True
                    train.closed = True
                    train.save()



                logger.info(
                    "TRAIN END weight=%s",
                    full_weight
                )

                return self.format_response(prefix)


            # ===============================
            # Direction
            # ===============================

            elif "TRN_DIR:" in raw_data.upper():

                direction = self.extract_direction(
                    raw_data.upper()
                )


                Train.objects.filter(
                    id=state.train_id
                ).update(
                    direction=direction
                )


                return self.format_response(prefix)



            # ===============================
            # Layout
            # ===============================

            elif "TX_VEH:" in raw_data.upper():

                layout = (
                    raw_data
                    .replace("TX_VEH:", "")
                    .strip()
                )


                Train.objects.filter(
                    id=state.train_id
                ).update(
                    layout=layout
                )


                return self.format_response(prefix)



            elif "RFINISH:" in raw_data.upper():

                scale.scale_status = "READY"
                scale.save()


            elif "CWSTATE=" in raw_data.upper():

                scale.connected = True
                scale.save()

                return self.format_response(prefix)



            else:

                logger.info(
                    "UNKNOWN: %s",
                    raw_data
                )


        except Exception:

            logger.exception(
                "Parser error scale=%s",
                scale.id
            )


        return None



    # ================= HELPERS =================


    def format_response(self, prefix):

        return (
            "\x06"
            + prefix
            + "\r"
            + "\x05"
            + "\r"
        )


    def get_weight(self, value):

        if not value:
            return Decimal("0")

        try:
            return Decimal(value).scaleb(-3)

        except:
            return Decimal("0")



    def get_speed(self, value):

        if not value:
            return Decimal("0")

        try:
            return Decimal(value).scaleb(-2)

        except:
            return Decimal("0")



    def get_row_num(self, value):

        if not value:
            return 0

        return int(value.lstrip("0") or 0)



    def extract_direction(self, text):

        if "TRN_DIR: OUT" in text:
            return "OUT"

        if "TRN_DIR: IN" in text:
            return "IN"

        return None



    def extract_speed_axle(self, text):

        parts = text.split()

        for part in parts:

            if len(part) == 16 and part.isdigit():
                return part

        return None
