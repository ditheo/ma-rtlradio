import subprocess, re

def discover_devices():
    """Return list of detected RTL-SDR devices via rtl_test."""
    try:
        result = subprocess.run(
            ["rtl_test", "-t"], capture_output=True, text=True, timeout=5
        )
        output = result.stderr + result.stdout
        devices = []
        for line in output.splitlines():
            m = re.search(r'(\d+):\s+(.+)', line)
            if m:
                devices.append({"index": int(m.group(1)), "name": m.group(2).strip()})
        return devices
    except Exception as e:
        return [{"error": str(e)}]
