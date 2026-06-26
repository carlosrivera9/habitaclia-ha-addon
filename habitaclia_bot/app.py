import time
import json
import random
import re
import requests
from bs4 import BeautifulSoup
import paho.mqtt.publish as publish

MQTT_HOST = "core-mosquitto"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASS = None
OPTIONS_FILE = "/data/options.json"
SEEN_IDS_FILE = "/data/seen_ids.json"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

def load_options():
    with open(OPTIONS_FILE) as f:
        return json.load(f)

def load_seen_ids():
    try:
        with open(SEEN_IDS_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_seen_ids(seen_ids):
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump(list(seen_ids), f)

def mqtt_publish(topic, payload):
    try:
        publish.single(
            topic,
            json.dumps(payload),
            hostname=MQTT_HOST,
            port=MQTT_PORT,
            retain=True,
            auth={"username": MQTT_USER, "password": MQTT_PASS}
        )
        print(f"MQTT published to {topic}")
    except Exception as e:
        print(f"MQTT error: {e}")

def scrape_listings(max_price):
    listings = []
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.enalquiler.com/",
    }

    url = "https://www.enalquiler.com/alquilar/alquiler-pisos-mascota-valencia_2_50692_48.html"
    print(f"Fetching: {url}", flush=True)

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.encoding = 'latin-1'
        print(f"Status: {response.status_code}", flush=True)

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"alquiler_piso_valencia"))

        # Debug: print raw HTML of first listing's parent
        if links:
            first = links[0]
            parent = first.find_parent("li")
            if parent:
                print(f"DEBUG parent li HTML:\n{parent}", flush=True)
            else:
                print(f"DEBUG no parent li, printing grandparent:\n{first.parent}", flush=True)

    except Exception as e:
        print(f"Request error: {e}", flush=True)

    return listings

def main():
    global MQTT_USER, MQTT_PASS
    print("=== Enalquiler Bot Starting ===", flush=True)
    options = load_options()
    MQTT_USER = options.get("mqtt_user", "idealista_bot")
    MQTT_PASS = options.get("mqtt_password", "idealista123")
    max_price = options.get("max_price", 1000)
    scrape_listings(max_price)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error: {e}", flush=True)
        time.sleep(1800)
