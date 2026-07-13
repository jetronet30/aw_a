import fcntl
import logging
import queue
import threading
import time

import serial

from scale.models import ScaleSettings

from .tsr4000_parser import Tsr4000ParserDynamic

logger = logging.getLogger(__name__)

STX = 0x02           # პაკეტის სავალდებულო საწყისი ბაიტი
FRAME_END = b"\r\n"  # პაკეტის დამასრულებელი მიმდევრობა (0D 0A)

PERIODIC_COMMAND = "\u0005\r"   # პერიოდულად გასაგზავნი ბრძანება
PERIOD_MS = 2000                 # ინტერვალი მილიწამებში
RECONNECT_DELAY_S = 2            # პაუზა ხელახალ დაკავშირებამდე


class LatestValueBroadcaster:
    """უახლესი გაზომვის მნიშვნელობის thread-safe გავრცელება."""

    def __init__(self):
        self._value = None
        self._version = 0
        self._condition = threading.Condition()

    def publish(self, value):
        with self._condition:
            self._value = value
            self._version += 1
            self._condition.notify_all()

    def wait_for_update(self, last_seen_version, timeout=None):
        with self._condition:
            if self._version == last_seen_version:
                self._condition.wait(timeout=timeout)
            return self._value, self._version


latest_serial_value = LatestValueBroadcaster()
parser = Tsr4000ParserDynamic()


def _get_scale_settings():
    """
    ყოველ ჯერზე ბაზიდან ცოცხალი პარამეტრის წამოღება,
    ნაცვლად იმისა, რომ ერთხელ, იმპორტის დროს დაქეშდეს.
    """
    try:
        return ScaleSettings.objects.first()
    except Exception:
        logger.exception("ScaleSettings-ის წამოღება ვერ მოხერხდა")
        return None


class SerialReader:
    """
    ერთადერთი thread ეხება სერიალის პორტს (წაკითხვა, პერიოდული
    გაგზავნა, echo). გარედან (START/ABORT) მოსული ბრძანებები
    queue-ს გადაეცემა და მხოლოდ ამ thread-ის loop-ში სრულდება —
    ასე პორტთან ერთდროული წვდომა საერთოდ არ ხდება და
    "multiple access on port" ტიპის შეცდომები აღარ გვექნება.
    """

    READ_TICK_S = 0.1  # რამდენად ხშირად "იღვიძებს" loop-ი წასაკითხად/საგზავნად

    def __init__(self, port="/dev/ttyS0", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.thread = None
        self.ser = None
        self._out_queue = queue.Queue()
        self._last_periodic_ts = 0.0

    def start(self):
        if self.running:
            logger.warning("SerialReader უკვე გაშვებულია.")
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _ensure_connected(self):
        if self.ser is None or not self.ser.is_open:
            ser = serial.Serial(self.port, self.baudrate, timeout=self.READ_TICK_S)
            try:
                # exclusive lock პორტის file descriptor-ზე — თუ სხვა
                # პროცესს (მაგ. ხელით გაშვებული სკრიპტი, ან წინა
                # გაშვებიდან "ჩამოკიდებული" პროცესი) უკვე უჭირავს
                # პორტი, აქ ცხადად გავიგებთ ამის შესახებ.
                fcntl.flock(ser.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                ser.close()
                logger.error(
                    "%s უკვე დაკავებულია სხვა პროცესის მიერ "
                    "(შეამოწმე: lsof %s ან fuser %s)",
                    self.port, self.port, self.port,
                )
                raise
            self.ser = ser
            logger.info("დაკავშირებულია %s (%d baud)", self.port, self.baudrate)
            return True  # ახლად დაკავშირდა → ბუფერის გასუფთავება საჭიროა
        return False

    def _close_connection(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None

    def _loop(self):
        """
        ერთი ციკლი: (1) კავშირის შემოწმება, (2) რიგში მდგარი
        ბრძანებების გაგზავნა, (3) პერიოდული ბრძანების გაგზავნა
        საჭიროებისას, (4) რაც არსებობს — წაკითხვა და დამუშავება.
        ყველაფერი ერთსა და იმავე thread-ში, თანმიმდევრობით.
        """
        buffer = bytearray()
        while self.running:
            try:
                if self._ensure_connected():
                    buffer.clear()

                self._flush_out_queue()
                self._maybe_send_periodic()

                waiting = self.ser.in_waiting
                chunk = self.ser.read(max(1, waiting)) if waiting else self.ser.read(1)
                if chunk:
                    buffer.extend(chunk)
                    self._extract_frames(buffer)

            except (serial.SerialException, OSError) as e:
                logger.error(
                    "სერიალის შეცდომა: %s — ხელახლა დაკავშირება %dწმ-ში",
                    e, RECONNECT_DELAY_S,
                )
                self._close_connection()
                time.sleep(RECONNECT_DELAY_S)
            except Exception:
                logger.exception("მოულოდნელი შეცდომა loop-ში")
                time.sleep(1)

    def _flush_out_queue(self):
        """გარედან (სხვა thread-იდან) მოსული ბრძანებების გაგზავნა."""
        while True:
            try:
                payload, label = self._out_queue.get_nowait()
            except queue.Empty:
                break
            self._write_now(payload, label)

    def _maybe_send_periodic(self):
        now = time.monotonic()
        if now - self._last_periodic_ts >= PERIOD_MS / 1000.0:
            self._last_periodic_ts = now
            self._write_now(PERIODIC_COMMAND, "periodic")

    def _extract_frames(self, buffer: bytearray):
        while True:
            end_idx = buffer.find(FRAME_END)
            if end_idx == -1:
                if len(buffer) > 4096 and STX not in buffer:
                    logger.warning("Junk data ბუფერში, სუფთავდება")
                    buffer.clear()
                break

            frame = bytes(buffer[:end_idx])
            del buffer[:end_idx + len(FRAME_END)]

            stx_idx = frame.find(STX)
            if stx_idx == -1:
                logger.warning("არასწორი პაკეტი (STX არ მოიძებნა), იგნორირდება: %r", frame)
                continue

            data = frame[stx_idx + 1:].decode(errors="ignore").strip()
            if not data:
                continue

            logger.info("Serial Data: %s", data)
            scale = _get_scale_settings()
            if scale is None:
                logger.warning("ScaleSettings ვერ მოიძებნა, პაკეტი გამოტოვებულია")
                continue

            try:
                parsed = parser.parse(scale, data)
            except Exception:
                logger.exception("პარსინგის შეცდომა, პაკეტი: %r", data)
                continue

            # echo პირდაპირ იგზავნება (იმავე thread-შია, queue არ სჭირდება)
            self._write_now(self._send_formatter(parsed), "echo")
            latest_serial_value.publish(data)

    def _write_now(self, payload: str, label: str):
        """რეალურად წერს პორტში. მხოლოდ loop-ის thread-იდან უნდა გამოიძახებოდეს."""
        try:
            if not (self.ser and self.ser.is_open):
                logger.warning("პორტი არ არის გახსნილი, %s ვერ გაიგზავნა", label)
                return
            self.ser.write(payload.encode("utf-8"))
            logger.info("გაგზავნილია %s command: %r", label, payload)
        except Exception as e:
            logger.error("%s გაგზავნის შეცდომა: %s", label, e)

    def _enqueue(self, payload: str, label: str):
        """გარე thread-იდან გამოსაძახებელი — ბრძანებას რიგში დებს."""
        self._out_queue.put((payload, label))

    def send_echo(self, data):
        self._enqueue(self._send_formatter(data), "echo")

    def send_start(self):
        self._enqueue(self._send_formatter("49CSTART7C345F"), "START")

    def send_abort(self):
        self._enqueue(self._send_formatter("3DCABORT933C6A"), "ABORT")

    @staticmethod
    def _send_formatter(cmd: str) -> str:
        return f"{chr(STX)}{cmd}{chr(0x0D)}"

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self._close_connection()
        logger.info("სერიალის პორტი დაიხურა.")


# --- გლობალური ინსტანსი: singleton, უსაფრთხოდ იმართება lock-ით ---
_reader = None
_reader_lock = threading.Lock()


def get_reader(port="/dev/ttyS0", baudrate=9600) -> SerialReader:
    """
    Singleton წვდომა SerialReader-ზე. აღარ იხსნება იმპორტისთანავე
    (module-level side effect) — ეს იწვევდა პორტის ბლოკვას, თუ
    მოდული Django-ს autoreload-ის ან რამდენიმე worker-ის მიერ
    ერთზე მეტჯერ ჩაიტვირთებოდა.

    გამოძახება უნდა მოხდეს ერთხელ, აპლიკაციის დაწყებისას
    (მაგ. AppConfig.ready()-დან), ან პირველ საჭიროებაზე.
    """
    global _reader
    with _reader_lock:
        if _reader is None:
            _reader = SerialReader(port, baudrate)
            _reader.start()
        return _reader


def send_start():
    get_reader().send_start()


def send_abort():
    get_reader().send_abort()


def stop_reader():
    global _reader
    with _reader_lock:
        if _reader is not None:
            _reader.stop()
            _reader = None
