from pathlib import Path
import shutil
import tempfile

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from bp_model import predict_bp_from_frames

app = FastAPI(title="BP Predictor API", version="1.0.0")


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


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/predict")
async def predict(
    video: UploadFile = File(...),
    cheek_x: int = Form(...),
    cheek_y: int = Form(...),
    cheek_w: int = Form(...),
    cheek_h: int = Form(...),
    palm_x: int = Form(...),
    palm_y: int = Form(...),
    palm_w: int = Form(...),
    palm_h: int = Form(...),
):
    suffix = Path(video.filename or "upload.mp4").suffix or ".mp4"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = Path(tmp.name)
        shutil.copyfileobj(video.file, tmp)

    try:
        frames, fps = _read_frames(temp_path)
        cheek_roi = (cheek_x, cheek_y, cheek_w, cheek_h)
        palm_roi = (palm_x, palm_y, palm_w, palm_h)

        sys_bp, dia_bp, hr = predict_bp_from_frames(frames, fps, cheek_roi, palm_roi)

        return {
            "heart_rate_bpm": hr,
            "systolic_mmhg": sys_bp,
            "diastolic_mmhg": dia_bp,
            "fps": fps,
            "frames": len(frames),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
