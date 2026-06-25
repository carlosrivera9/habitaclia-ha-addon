ARG BUILD_FROM
FROM $BUILD_FROM
WORKDIR /app
RUN pip3 install --no-cache-dir paho-mqtt requests beautifulsoup4
COPY app.py .
CMD ["python3", "-u", "app.py"]
