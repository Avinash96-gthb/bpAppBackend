# Flutter + Python Backend (MVP)

This setup keeps your BP model logic in Python and uses Flutter as a simple mobile frontend.

## 1) Python backend

From project root:

```bash
cd /Users/avinash/Downloads/BP_APP
python3 -m venv .venv-backend
source .venv-backend/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## 2) Flutter frontend

Install Flutter first if missing.

Then from project root:

```bash
cd /Users/avinash/Downloads/BP_APP/frontend
flutter create .
flutter pub get
flutter run
```

### Backend URL to use in app
- Android emulator: `http://10.0.2.2:8000`
- Physical phone on same Wi‑Fi: `http://<YOUR_COMPUTER_LAN_IP>:8000`

## 3) Build APK from Flutter

From `frontend/`:

```bash
flutter build apk --release
```

APK output:

```bash
build/app/outputs/flutter-apk/app-release.apk
```

## Notes
- `training_data.xlsx` stays in project root and is used by backend model.
- ROI values are entered manually in the Flutter app for MVP speed.
- This is online inference (app sends video to backend). For offline on-device inference, keep Kivy/Buildozer or rewrite model natively.
