ARG BUILD_FROM
FROM $BUILD_FROM
WORKDIR /app
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --break-system-packages paho-mqtt requests beautifulsoup4
COPY app.py .
CMD ["python3", "-u", "app.py"]
