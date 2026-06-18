ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

RUN apk add --no-cache python3 py3-pip

COPY app.py .

RUN echo "===== CHECKING APP.PY =====" && grep -n playwright /app/app.py || true

RUN pip3 install --break-system-packages paho-mqtt requests beautifulsoup4

CMD ["python3", "-u", "/app/app.py"]
