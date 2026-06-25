import time
import json
import random
import requests
import paho.mqtt.publish as publish
from bs4 import BeautifulSoup

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
            auth={"username": MQTT_USER, "password": MQTT_PASS}
        )
        print(f"MQTT published to {topic}")
    except Exception as e:
        print(f"MQTT error: {e}")

def build_url(city_slug, max_price, pets):
    base = f"https://www.idealista.com/alquiler-viviendas/{city_slug}/"
    params = f"?precio-hasta={max_price}"
    if pets:
        params += "&mascota=1"
    return base + params

def scrape_listings(url):
    from playwright.sync_api import sync_playwright
    content = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)
            content = page.content()
            print(content[:2000], flush=True)
        except Exception as e:
            print(f"Browser error: {e}", flush=True)
        finally:
            browser.close()
    soup = BeautifulSoup(content, "html.parser")
    articles = soup.find_all("article", class_="item")

def main():
    global MQTT_USER, MQTT_PASS
    print("=== Idealista Bot Starting ===", flush=True)
    options = load_options()
    print(f"Options loaded: {options}", flush=True)
    MQTT_USER = options.get("mqtt_user", "idealista_bot")
    MQTT_PASS = options.get("mqtt_password", "idealista123")
    city = options.get("city", "valencia-valencia")
    max_price = options.get("max_price", 1000)
    pets = options.get("pets", True)

    seen_ids = load_seen_ids()
    url = build_url(city, max_price, pets)
    print(f"Scraping: {url}", flush=True)
    listings = scrape_listings(url)

    new_listings = [l for l in listings if l["id"] not in seen_ids]
    print(f"New listings: {len(new_listings)}", flush=True)

    for listing in new_listings:
        mqtt_publish("idealista/listing", listing)
        seen_ids.add(listing["id"])

    save_seen_ids(seen_ids)
    print("Done.", flush=True)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error: {e}", flush=True)
        time.sleep(1800)  # 30 minutes
