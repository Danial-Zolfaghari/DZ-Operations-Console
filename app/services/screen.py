from __future__ import annotations

import time
import cv2
import mss
import numpy as np


class ScreenStreamer:
    def __init__(self, fps: int = 8, scale: float = 0.65) -> None:
        self.fps = fps
        self.scale = scale

    def frames(self):
        frame_delay = 1 / self.fps
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            while True:
                started = time.perf_counter()
                raw = np.asarray(sct.grab(monitor))
                frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
                if self.scale != 1:
                    frame = cv2.resize(frame, None, fx=self.scale, fy=self.scale, interpolation=cv2.INTER_AREA)
                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 76])
                if ok:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-store\r\n\r\n" + encoded.tobytes() + b"\r\n"
                elapsed = time.perf_counter() - started
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)
