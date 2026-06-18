ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY app.py .

CMD ["python3", "/app/app.py"]
