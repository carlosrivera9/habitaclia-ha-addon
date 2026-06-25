ARG BUILD_FROM
FROM $BUILD_FROM
WORKDIR /app
RUN pip3 install --break-system-packages paho-mqtt requests beautifulsoup4
COPY app.py .
COPY rootfs /
