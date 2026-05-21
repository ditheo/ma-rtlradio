# ma-rtlradio

FM and DAB+ radio for [Music Assistant](https://music-assistant.io) using any RTL2832U-based USB dongle (RTL-SDR).

## Components

| Component | Location | Description |
|---|---|---|
| HA Add-on | `rtlradio-backend/` | FastAPI backend that tunes the dongle and streams audio |
| MA Provider | `provider/rtlradio/` | Music Assistant provider that surfaces stations |

## Installation

### 1. Home Assistant Add-on

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add: `https://github.com/ditheo/ma-rtlradio`
3. Find **RTL-SDR Radio Backend** and click **Install**
4. Configure device_serial (leave empty for auto-detect)
5. Start the add-on

### 2. Music Assistant Provider

Copy `provider/rtlradio/` into your Music Assistant providers directory, then:
- **MA → Settings → Providers → Add → RTL-SDR Radio**
- Backend URL: `http://homeassistant.local:8080`

## USB Passthrough (Proxmox)

```bash
# Find your dongle
lsusb | grep -i realtek

# Passthrough to HAOS VM (replace 100 with your VM ID)
qm set 100 -usb0 host=0bda:2838
```

## Maintainer

[@ditheo](https://github.com/ditheo) — ditheo@gmail.com
