ARG BUILD_FROM
FROM $BUILD_FROM

# v1.1.13
WORKDIR /app

RUN apk add --no-cache python3 py3-pip

COPY app.py .

RUN pip3 install --break-system-packages paho-mqtt requests beautifulsoup4

CMD ["python3", "-u", "/app/app.py"]
