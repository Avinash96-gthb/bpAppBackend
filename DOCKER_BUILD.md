# Docker Build Instructions (macOS/Linux)

This project is configured to build APKs with Buildozer in Docker.

For Apple Silicon Macs, this setup pins the container to `linux/amd64` so Android SDK tools (like `aidl`) run correctly.

The Docker service uses a wrapper script to ensure Buildozer Python dependencies (for example `appdirs`) are installed before each run.

## 1) Prerequisites
- Docker Desktop installed and running
- Project folder opened in terminal

## 2) Build debug APK

```bash
docker compose run --rm buildozer android debug
```

First run downloads Android SDK/NDK and can take a long time.

## 3) Find APK output

APK files are created in:

```bash
bin/
```

## 4) Rebuild from clean state (optional)

```bash
docker compose run --rm buildozer android clean
docker compose run --rm buildozer android debug
```

After changing `buildozer.spec` requirements, always run a clean rebuild so the previous dist is discarded:

```bash
docker compose run --rm buildozer android clean
docker compose run --rm buildozer android debug
```

If you previously built outside Docker and get permission errors, reset local build artifacts once:

```bash
rm -rf .buildozer
docker compose down -v
docker compose run --rm buildozer android debug
```

If you changed architecture settings (for example adding `linux/amd64`), clear Docker volumes once so SDK/NDK is re-downloaded correctly:

```bash
docker compose down -v
docker compose pull
docker compose run --rm buildozer android debug
```

## 5) Deploy to connected Android device (optional)

```bash
docker compose run --rm buildozer android deploy run
```

(Enable USB debugging on your device.)

Note: if Buildozer prompts about running as root, type `y` to continue in this Docker workflow.
