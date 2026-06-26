FROM python:3.11-slim
WORKDIR /app
RUN pip3 install --no-cache-dir paho-mqtt requests beautifulsoup4
COPY app.py .
CMD ["python3", "-u", "app.py"]
