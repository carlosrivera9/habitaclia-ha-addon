FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir paho-mqtt requests beautifulsoup4 playwright
RUN playwright install chromium
COPY app.py .
CMD ["python3", "-u", "app.py"]
