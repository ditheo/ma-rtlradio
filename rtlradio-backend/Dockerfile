ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    rtl-sdr \
    ffmpeg \
    curl \
    kmod

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY rtlradio_backend/ ./rtlradio_backend/
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8080
CMD ["/run.sh"]
