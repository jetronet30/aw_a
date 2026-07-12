import threading
import time
import logging
import serial

logger = logging.getLogger(__name__)

STX = 0x02           # პაკეტის სავალდებულო საწყისი ბაიტი
FRAME_END = b"\r\n"  # პაკეტის დამასრულებელი მიმდევრობა (0D 0A)


class LatestValueBroadcaster:
    """
    ინახავს მხოლოდ ბოლო მიღებულ მნიშვნელობას და აცნობებს ყველა
    დამოუკიდებელ SSE client-ს ვერსიის მექანიზმით — ასე გამორიცხულია
    Queue-ზე დამახასიათებელი პრობლემა, როცა ერთმანეთს "ართმევენ" data-ს.
    """
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


latest_serial_value = LatestValueBroadcaster()  # გლობალური, საერთო broadcaster


class SerialReader:
    def __init__(self, port="/dev/ttyS0", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.thread = None
        self.ser = None

    def start(self):
        if self.running:
            logger.warning("SerialReader უკვე გაშვებულია.")
            return
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _read_loop(self):
        buffer = bytearray()
        while self.running:
            try:
                if self.ser is None or not self.ser.is_open:
                    self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                    logger.info("დაკავშირებულია %s (%d baud)", self.port, self.baudrate)
                    buffer.clear()

                chunk = self.ser.read(max(1, self.ser.in_waiting))
                if not chunk:
                    continue
                buffer.extend(chunk)
                self._extract_frames(buffer)

            except (serial.SerialException, OSError) as e:
                logger.error("სერიალის შეცდომა: %s — ხელახლა დაკავშირება 2წმ-ში", e)
                if self.ser:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                self.ser = None
                time.sleep(2)
            except Exception:
                logger.exception("მოულოდნელი შეცდომა read loop-ში")
                time.sleep(1)

    def _extract_frames(self, buffer: bytearray):
        """მკაცრად ვალიდაცია: 02 ... 0D 0A. STX-ის გარეშე ფრეიმი უარყოფილია."""
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
            if data:
                logger.info("Serial Data: %s", data)
                latest_serial_value.publish(data)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("სერიალის პორტი დაიხურა.")
