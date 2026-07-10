import logging
import os
import threading
import time
from multiprocessing import Event as _make_event, Process
from multiprocessing.synchronize import Event as EventType

import cv2

# PyTorch warning suppression
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"

logger = logging.getLogger("cameras.worker")

YOLO_MODEL_PATH = "yolo11n.pt"
TARGET_CLASSES: list[int] | None = None   # None = detect all classes
RECONNECT_DELAY_SEC = 5
STREAM_FPS = 15   # stable live FPS
DETECT_EVERY_N = 1
YOLO_IMGSZ = 320   # smaller = faster inference on CPU, adjust if needed


# -----------------------------
# Helpers
# -----------------------------
def _open_capture(rtsp_url: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # low latency
    return cap


class FrameGrabber:
    """Continuously reads frames from cap in a background thread and keeps
    only the most recently read one. This prevents processing (YOLO +
    encoding) that is slower than the camera's frame rate from causing
    frames to queue up and the stream to drift out of sync (growing lag).
    Older, unread frames are simply dropped instead of accumulating.
    """

    def __init__(self, cap: cv2.VideoCapture):
        self.cap = cap
        self._lock = threading.Lock()
        self._frame = None
        self._ok = False
        self._stopped = False
        self._got_first_frame = threading.Event()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        while not self._stopped:
            ok, frame = self.cap.read()
            if not ok:
                with self._lock:
                    self._ok = False
                break
            with self._lock:
                self._frame = frame
                self._ok = True
            self._got_first_frame.set()

    def wait_first_frame(self, timeout: float = 5.0) -> bool:
        """Block until the reader thread has produced its first frame (or
        failed / timed out). Call this once right after construction, before
        the main loop starts calling read() — otherwise read() can race the
        reader thread and report a false 'frame read failed' before the
        first frame has even arrived."""
        return self._got_first_frame.wait(timeout=timeout)

    def read(self) -> tuple[bool, "cv2.typing.MatLike | None"]:
        with self._lock:
            if self._frame is None:
                return False, None
            return self._ok, self._frame.copy()

    def stop(self):
        self._stopped = True
        self._thread.join(timeout=2)


# -----------------------------
# Worker
# -----------------------------
def camera_worker(cam_params: dict, output_dir: str, stop_event: EventType):
    from ultralytics import YOLO
    from cam.streamer import HLSStreamer

    camera_no = cam_params["camera_no"]
    cam_name = cam_params["cam_name"]
    rtsp_url = cam_params["rtsp_url"]
    min_confidence = cam_params["min_confidence"]
    min_width = cam_params["min_width"]
    min_height = cam_params["min_height"]

    logger.info("[cam %s] worker started (%s)", camera_no, cam_name)

    model = YOLO(YOLO_MODEL_PATH)

    while not stop_event.is_set():
        cap = _open_capture(rtsp_url)
        if not cap.isOpened():
            logger.warning("[cam %s] RTSP connection failed", camera_no)
            cap.release()
            time.sleep(RECONNECT_DELAY_SEC)
            continue

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        fps = STREAM_FPS  # ignore RTSP FPS

        streamer = HLSStreamer(output_dir=output_dir, width=width, height=height, fps=fps)
        streamer.start()

        grabber = FrameGrabber(cap)

        if not grabber.wait_first_frame(timeout=10):
            logger.warning("[cam %s] no frame received within timeout, reconnecting", camera_no)
            grabber.stop()
            cap.release()
            streamer.stop()
            time.sleep(RECONNECT_DELAY_SEC)
            continue

        logger.info("[cam %s] HLS started %sx%s @%s fps", camera_no, width, height, fps)

        frame_interval = 1 / fps
        frame_count = 0

        try:
            while not stop_event.is_set():
                loop_start = time.perf_counter()

                ok, frame = grabber.read()
                if not ok or frame is None:
                    logger.warning("[cam %s] frame read failed", camera_no)
                    break

                frame_count += 1
                if frame_count % DETECT_EVERY_N == 0:
                    results = model.predict(
                        frame,
                        conf=min_confidence,
                        classes=TARGET_CLASSES,
                        imgsz=YOLO_IMGSZ,
                        verbose=False,
                    )[0]

                    if results.boxes is not None:
                        for box in results.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            box_w, box_h = x2 - x1, y2 - y1

                            if box_w < min_width or box_h < min_height:
                                continue

                            conf = float(box.conf[0])
                            cls_id = int(box.cls[0])
                            label = f"{model.names[cls_id]} {conf:.2f}"

                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(
                                frame,
                                label,
                                (x1, max(20, y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 0),
                                1,
                            )

                try:
                    streamer.write_frame(frame.tobytes())
                except BrokenPipeError:
                    logger.error("[cam %s] FFmpeg pipe closed", camera_no)
                    break

                # FPS control
                elapsed = time.perf_counter() - loop_start
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)

        finally:
            grabber.stop()
            cap.release()
            streamer.stop()

        if not stop_event.is_set():
            time.sleep(RECONNECT_DELAY_SEC)

    logger.info("[cam %s] worker stopped", camera_no)


# -----------------------------
# Process starter
# -----------------------------
def start_worker_process(cam_params: dict, output_dir: str) -> tuple[Process, EventType]:
    stop_event = _make_event()
    proc = Process(
        target=camera_worker,
        args=(cam_params, output_dir, stop_event),
        name=f"cam-worker-{cam_params['camera_no']}",
        daemon=True,
    )
    proc.start()
    return proc, stop_event
