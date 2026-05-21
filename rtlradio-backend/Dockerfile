ARG BUILD_FROM
FROM $BUILD_FROM

# Install rtl-sdr, ffmpeg, curl
RUN apk add --no-cache rtl-sdr ffmpeg curl kmod || \
    (apt-get update && apt-get install -y --no-install-recommends \
        rtl-sdr ffmpeg curl kmod && rm -rf /var/lib/apt/lists/*)

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY rtlradio_backend/ ./rtlradio_backend/
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8080
CMD ["/run.sh"]
