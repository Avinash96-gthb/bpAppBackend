from pathlib import Path
import shutil
import tempfile
import logging
import math
import time

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from bp_model import predict_bp_from_frames

app = FastAPI(title="BP Predictor API", version="1.0.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bp-backend")


@app.get("/")
def root():
    return {"status": "ok", "service": "bp-backend"}


def _read_frames(video_path: Path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Could not open uploaded video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 1:
        fps = 30

    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)

    cap.release()

    if len(frames) < 30:
        raise ValueError("Video too short. Provide at least ~1 second with clear face/palm.")

    return frames, int(round(fps))


def _default_rois(frame):
    h, w = frame.shape[:2]

    cheek_w = max(40, int(w * 0.22))
    cheek_h = max(40, int(h * 0.22))
    cheek_x = max(0, int(w * 0.39) - cheek_w // 2)
    cheek_y = max(0, int(h * 0.32) - cheek_h // 2)

    palm_w = max(50, int(w * 0.28))
    palm_h = max(50, int(h * 0.28))
    palm_x = max(0, int(w * 0.50) - palm_w // 2)
    palm_y = max(0, int(h * 0.72) - palm_h // 2)

    cheek_roi = (cheek_x, cheek_y, cheek_w, cheek_h)
    palm_roi = (palm_x, palm_y, palm_w, palm_h)
    return cheek_roi, palm_roi


def _downsample_frames(frames, fps, max_frames=360):
    original_count = len(frames)
    if original_count <= max_frames:
        return frames, fps, original_count

    step = max(1, int(math.ceil(original_count / max_frames)))
    reduced = frames[::step]
    adjusted_fps = max(1, int(round(fps / step)))
    return reduced, adjusted_fps, original_count


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/predict")
async def predict(
    video: UploadFile = File(...),
    cheek_x: int | None = Form(None),
    cheek_y: int | None = Form(None),
    cheek_w: int | None = Form(None),
    cheek_h: int | None = Form(None),
    palm_x: int | None = Form(None),
    palm_y: int | None = Form(None),
    palm_w: int | None = Form(None),
    palm_h: int | None = Form(None),
):
    suffix = Path(video.filename or "upload.mp4").suffix or ".mp4"
    start_time = time.time()
    logger.info("/predict request received: filename=%s content_type=%s", video.filename, video.content_type)

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = Path(tmp.name)
        shutil.copyfileobj(video.file, tmp)

    try:
        frames, fps = _read_frames(temp_path)
        frames, fps, original_frame_count = _downsample_frames(frames, fps)

        custom_roi_values = [cheek_x, cheek_y, cheek_w, cheek_h, palm_x, palm_y, palm_w, palm_h]
        if all(value is not None for value in custom_roi_values):
            cheek_roi = (int(cheek_x), int(cheek_y), int(cheek_w), int(cheek_h))
            palm_roi = (int(palm_x), int(palm_y), int(palm_w), int(palm_h))
        else:
            cheek_roi, palm_roi = _default_rois(frames[0])

        sys_bp, dia_bp, hr = predict_bp_from_frames(frames, fps, cheek_roi, palm_roi)
        elapsed = round(time.time() - start_time, 2)
        logger.info(
            "/predict success: elapsed=%ss original_frames=%s used_frames=%s fps=%s",
            elapsed,
            original_frame_count,
            len(frames),
            fps,
        )

        return {
            "heart_rate_bpm": hr,
            "systolic_mmhg": sys_bp,
            "diastolic_mmhg": dia_bp,
            "fps": fps,
            "frames": len(frames),
            "original_frames": original_frame_count,
            "processing_seconds": elapsed,
        }
    except Exception as exc:
        logger.exception("/predict failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
