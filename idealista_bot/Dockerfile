ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache chromium chromium-chromedriver python3 py3-pip

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --break-system-packages -r requirements.txt

RUN playwright install chromium

COPY app.py .

CMD ["python3", "/app/app.py"]
