#!/bin/sh

VENV_DIR=/opt/nvda_service/venv
SERVICE_DIR=/opt/nvda_service

if [ -f "$VENV_DIR/bin/python3" ]; then
  exec "$VENV_DIR/bin/python3" "$SERVICE_DIR/nvda_service.py"
else
  exec "usr/bin/python3" "$SERVICE_DIR/nvda_service.py"
fi
