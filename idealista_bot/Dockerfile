# Idealista bot test
ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-pip

COPY app.py /

RUN pip3 install paho-mqtt requests

CMD ["python3", "/app.py"]
