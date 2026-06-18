ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

COPY requirements.txt /app/

RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN python3 -m playwright install chromium

COPY app.py /app/

CMD ["python3", "/app/app.py"]
