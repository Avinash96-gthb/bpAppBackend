#!/bin/sh
set -eu

/home/user/.venv/bin/python3 -m pip install -q \
  appdirs \
  colorama>=0.3.3 \
  jinja2 \
  "sh>=1.10,<2.0" \
  build \
  toml \
  packaging \
  setuptools

exec /home/user/.venv/bin/buildozer "$@"
