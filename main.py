import time
import threading

import cv2
import numpy as np
from bp_model import predict_bp_from_frames
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.graphics.texture import Texture
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.label import Label

VIDEO_TIME = 20
CAPTURE_HZ = 30


def bgr_to_texture(frame_bgr: np.ndarray) -> Texture:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    rgb = np.flipud(rgb)
    h, w = rgb.shape[:2]
    tex = Texture.create(size=(w, h), colorfmt="rgb")
    tex.blit_buffer(rgb.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
    return tex


class ROIImage(Image):
    def __init__(self, frame_bgr, on_roi_done, **kwargs):
        super().__init__(**kwargs)
        self.frame = frame_bgr
        self.on_roi_done = on_roi_done
        self.texture = bgr_to_texture(frame_bgr)
        self.allow_stretch = True
        self.keep_ratio = False
        self._start = None
        self._line = None

    def _to_frame_xy(self, x, y):
        xn = min(max((x - self.x) / max(self.width, 1), 0.0), 1.0)
        yn = min(max((y - self.y) / max(self.height, 1), 0.0), 1.0)
        h, w = self.frame.shape[:2]
        fx = int(xn * w)
        fy = int((1.0 - yn) * h)
        return fx, fy

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self._start = touch.pos
        with self.canvas.after:
            Color(0, 1, 0, 1)
            self._line = Line(rectangle=(touch.x, touch.y, 1, 1), width=2)
        return True

    def on_touch_move(self, touch):
        if self._start and self._line:
            x0, y0 = self._start
            x1, y1 = touch.pos
            self._line.rectangle = (min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if not self._start:
            return super().on_touch_up(touch)

        x0, y0 = self._start
        x1, y1 = touch.pos
        self._start = None

        fx0, fy0 = self._to_frame_xy(x0, y0)
        fx1, fy1 = self._to_frame_xy(x1, y1)

        x = min(fx0, fx1)
        y = min(fy0, fy1)
        w = abs(fx1 - fx0)
        h = abs(fy1 - fy0)

        if w < 10 or h < 10:
            return True

        self.on_roi_done((x, y, w, h))
        return True


class BPApp(App):
    def build(self):
        self.frames = []
        self.timestamps = []
        self.cheek_roi = None
        self.palm_roi = None
        self.record_event = None
        self.record_start = None

        root = BoxLayout(orientation="vertical", spacing=8, padding=8)
        self.status = Label(text="Align face + palm, then tap Start", size_hint=(1, 0.12))
        self.camera = Camera(play=True, resolution=(640, 480), size_hint=(1, 0.78))
        self.start_btn = Button(text=f"Start {VIDEO_TIME}s Recording", size_hint=(1, 0.10))
        self.start_btn.bind(on_press=self.start_recording)

        root.add_widget(self.status)
        root.add_widget(self.camera)
        root.add_widget(self.start_btn)
        return root

    def _read_camera_frame(self):
        tex = self.camera.texture
        if tex is None:
            return None

        w, h = tex.size
        buf = np.frombuffer(tex.pixels, dtype=np.uint8)
        if buf.size != w * h * 4:
            return None

        rgba = buf.reshape((h, w, 4))
        rgba = np.flipud(rgba)
        return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)

    def start_recording(self, *_):
        self.frames.clear()
        self.timestamps.clear()
        self.start_btn.disabled = True
        self.status.text = "Recording... keep still"
        self.record_start = time.time()
        self.record_event = Clock.schedule_interval(self._capture_tick, 1.0 / CAPTURE_HZ)

    def _capture_tick(self, dt):
        frame = self._read_camera_frame()
        if frame is not None:
            self.frames.append(frame)
            self.timestamps.append(time.time())

        elapsed = time.time() - self.record_start
        remaining = max(0, int(VIDEO_TIME - elapsed))
        self.status.text = f"Recording... {remaining}s left"

        if elapsed >= VIDEO_TIME:
            self.record_event.cancel()
            if len(self.frames) < 10:
                self.status.text = "Recording failed. Try again."
                self.start_btn.disabled = False
                return
            self.ask_cheek_roi()

    def ask_cheek_roi(self):
        self.status.text = "Draw CHEEK ROI (drag rectangle)"
        mid = len(self.frames) // 2
        frame = self.frames[mid].copy()

        self.root.remove_widget(self.camera)
        self.roi_view = ROIImage(frame, self._on_cheek_roi, size_hint=(1, 0.78))
        self.root.add_widget(self.roi_view, index=1)

    def _on_cheek_roi(self, roi):
        self.cheek_roi = roi
        self.status.text = "Draw PALM ROI (drag rectangle)"
        self.roi_view.on_roi_done = self._on_palm_roi

    def _on_palm_roi(self, roi):
        self.palm_roi = roi
        self.status.text = "Processing..."
        threading.Thread(target=self._run_model, daemon=True).start()

    def _run_model(self):
        if len(self.timestamps) > 1 and (self.timestamps[-1] - self.timestamps[0]) > 0:
            fps = max(1, int(round((len(self.timestamps) - 1) / (self.timestamps[-1] - self.timestamps[0]))))
        else:
            fps = CAPTURE_HZ

        try:
            sys_bp, dia_bp, hr = predict_bp_from_frames(
                self.frames,
                fps,
                self.cheek_roi,
                self.palm_roi,
            )
            result = (
                f"Heart Rate: {round(hr, 1)} bpm\n"
                f"Systolic: {round(sys_bp, 1)} mmHg\n"
                f"Diastolic: {round(dia_bp, 1)} mmHg"
            )
        except Exception as exc:
            result = f"Prediction error: {exc}"

        Clock.schedule_once(lambda *_: self._show_result(result), 0)

    def _show_result(self, result):
        self.status.text = result
        self.start_btn.disabled = False


if __name__ == "__main__":
    BPApp().run()