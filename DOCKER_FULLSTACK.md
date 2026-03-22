# Docker full setup (Backend + Flutter)

This lets you run backend and Flutter tooling without installing Python/Flutter on your host.

## 1) Start backend API

```bash
cd /Users/avinash/Downloads/BP_APP
docker compose up -d --build backend
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## 2) Prepare Flutter project in container

```bash
docker compose run --rm flutter "flutter create . && flutter pub get"
```

Run this only once to generate native project folders.

## 3) Build APK in container

```bash
docker compose run --rm flutter "flutter pub get && flutter build apk --release"
```

For Apple Silicon (M1/M2/M3), if you changed architecture settings or saw AAPT2/Rosetta errors, reset flutter containers/volumes once:

```bash
docker compose down -v
docker compose run --rm flutter "flutter pub get && flutter build apk --debug"
```

APK output on host:

```bash
frontend/build/app/outputs/flutter-apk/app-release.apk
```

## 4) Run app in Android Studio emulator

You have two options:
- Install APK manually to emulator:
  ```bash
  adb install -r frontend/build/app/outputs/flutter-apk/app-release.apk
  ```
- Or use Android Studio with Flutter plugin (requires local Flutter SDK in Android Studio setup).

## 5) Backend URL in Flutter app

In emulator, keep:

```text
http://10.0.2.2:8000
```

(If backend runs on another machine, use that machine's LAN IP.)

## 6) Deploy backend to Render

Use Docker deployment and point Render to:
- Dockerfile path: `backend/Dockerfile`
- Exposed port: `8000`
- Start command: leave default from Dockerfile

Monorepo is fine. You do not need separate repos; configure the Render service to use the same repo with root directory `backend/` (or Dockerfile path `backend/Dockerfile`).

Set your Flutter app backend URL to your Render URL, e.g.:

```text
https://your-service-name.onrender.com
```
