import time
import json
import paho.mqtt.publish as publish

MQTT_HOST = "core-mosquitto"

while True:

    data = {
        "location": "Moncada / Valencia",
        "status": "Bot running",
        "score": 0
    }

    publish.single(
        "idealista_bot/status",
        json.dumps(data),
        hostname=MQTT_HOST
    )

    time.sleep(300)
