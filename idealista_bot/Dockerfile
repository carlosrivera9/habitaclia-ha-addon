ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

RUN apk add --no-cache python3 py3-pip

RUN python3 -m venv /venv

COPY requirements.txt .

RUN /venv/bin/pip install --upgrade pip
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

RUN /venv/bin/playwright install chromium

COPY app.py .

ENV PATH="/venv/bin:$PATH"

CMD ["python", "app.py"]
