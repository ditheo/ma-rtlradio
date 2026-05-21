ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN cat >/etc/apk/repositories <<'EOF'
https://dl-cdn.alpinelinux.org/alpine/v3.21/main
https://dl-cdn.alpinelinux.org/alpine/v3.21/community
https://dl-cdn.alpinelinux.org/alpine/edge/main
https://dl-cdn.alpinelinux.org/alpine/edge/community
https://dl-cdn.alpinelinux.org/alpine/edge/testing
EOF

RUN apk add --no-cache \
    python3 \
    py3-pip \
    rtl-sdr \
    ffmpeg \
    curl \
    kmod \
    bash \
    welle-cli

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY rtlradio_backend/ ./rtlradio_backend/
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 7070
CMD ["/run.sh"]
