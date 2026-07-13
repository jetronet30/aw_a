import os
import shutil
import subprocess


class HLSStreamer:
    def __init__(self, output_dir: str, width: int, height: int, fps: int = 15,
                 hls_time: int = 1, hls_list_size: int = 3):

        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "ffmpeg ვერ მოიძებნა სისტემაში. დააინსტალირეთ: apt install ffmpeg"
            )

        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.fps = fps
        self.hls_time = hls_time
        self.hls_list_size = hls_list_size
        self.process: subprocess.Popen | None = None

        self.clear_output_dir()

    def clear_output_dir(self)   :
        os.makedirs(self.output_dir, exist_ok=True)
        for item in os.listdir(self.output_dir):
            path = os.path.join(self.output_dir, item)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)

                elif os.path.isdir(path):
                    shutil.rmtree(path)

            except Exception as e:
                print(f"HLS cleanup error {path}: {e}")

    @property
    def playlist_path(self) -> str:
        return os.path.join(self.output_dir, "stream.m3u8")

    def start(self):
        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{self.width}x{self.height}",
            "-framerate", str(self.fps),
            "-i", "-",
            "-an",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-pix_fmt", "yuv420p",
            "-g", str(self.fps),
            "-f", "hls",
            "-hls_time", str(self.hls_time),
            "-hls_list_size", str(self.hls_list_size),
            "-hls_flags", "delete_segments+independent_segments",
            "-strftime", "1",
            "-hls_segment_filename",
            os.path.join(self.output_dir, "seg_%Y%m%d_%H%M%S.ts"),

            self.playlist_path,
        ]
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        return self.process

    def write_frame(self, frame_bytes: bytes):
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("Streamer არ არის გაშვებული — ჯერ start() გამოიძახეთ")
        try:
            self.process.stdin.write(frame_bytes)
        except BrokenPipeError:
            raise

    def stop(self):
        if self.process is not None:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
            except Exception:
                pass
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
