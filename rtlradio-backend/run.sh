#!/usr/bin/with-contenv bashio

DEVICE_SERIAL=$(bashio::config 'device_serial')
LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "Starting RTL-SDR Radio Backend v0.1.0"
bashio::log.info "Device serial: ${DEVICE_SERIAL:-auto}"

# Remove conflicting kernel modules
for mod in dvb_usb_rtl28xxu rtl2832 rtl2830; do
    modprobe -r "${mod}" 2>/dev/null || true
done

export DEVICE_SERIAL="${DEVICE_SERIAL}"

exec python3 -m uvicorn rtlradio_backend.app:app \
    --host 0.0.0.0 \
    --port 8080 \
    --log-level "${LOG_LEVEL:-info}"
