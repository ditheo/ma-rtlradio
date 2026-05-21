#!/bin/bash

DEVICE_SERIAL="${DEVICE_SERIAL:-}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "[INFO] Starting RTL-SDR Radio Backend v0.1.0"
echo "[INFO] Device serial: ${DEVICE_SERIAL:-auto-detect}"

for mod in dvb_usb_rtl28xxu rtl2832 rtl2830; do
    modprobe -r "${mod}" 2>/dev/null || true
done

exec python3 -m uvicorn rtlradio_backend.app:app \
    --host 0.0.0.0 \
    --port 8080 \
    --log-level "${LOG_LEVEL}"
