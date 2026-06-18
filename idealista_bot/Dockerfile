ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

COPY requirements.txt .

RUN ls -la /app
RUN cat requirements.txt

RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python3", "/app/app.py"]
