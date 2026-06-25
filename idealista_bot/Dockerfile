ARG BUILD_FROM
FROM $BUILD_FROM
WORKDIR /app
RUN apk add --no-cache python3 py3-pip
COPY app.py .
COPY run /etc/services.d/idealista_searcher/run
RUN chmod +x /etc/services.d/idealista_searcher/run
RUN pip3 install --break-system-packages paho-mqtt requests beautifulsoup4
