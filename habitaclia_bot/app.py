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
        time.sleep(random.uniform(2, 4))
        response = requests.get(url, headers=headers, timeout=20)
        response.encoding = 'latin-1'
        print(f"Status: {response.status_code}", flush=True)

        if response.status_code != 200:
            print("Non-200 response", flush=True)
            return listings

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"alquiler_piso_valencia"))

        seen_hrefs = set()
        for link in links:
            href = link.get("href", "")
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            try:
                listing_id = href.split("_")[-1].replace(".html", "")
                url_full = "https://www.enalquiler.com" + href if href.startswith("/") else href
                title = link.get_text(strip=True)
                if not title:
                    continue

                parent = link.find_parent("li")
                price_text = "N/A"
                price_num = 99999
                if parent:
                    text = parent.get_text(" ", strip=True)
                    price_match = re.search(r'(\d[\d\.]*)\s*€', text)
                    if price_match:
                        price_num = int(price_match.group(1).replace(".", ""))
                        price_text = f"{price_num} €/mes"

                print(f"  Listing: {title[:50]} | {price_text}", flush=True)

                if price_num > max_price:
                    print(f"  Skipping (price {price_num} > {max_price})", flush=True)
                    continue

                listings.append({
                    "id": listing_id,
                    "title": title,
                    "price": price_text,
                    "url": url_full,
                })

            except Exception as e:
                print(f"Error parsing item: {e}", flush=True)
                continue

        print(f"Found {len(seen_hrefs)} total listings, {len(listings)} under {max_price}€", flush=True)

    except Exception as e:
        print(f"Request error: {e}", flush=True)

    return listings

def main():
    global MQTT_USER, MQTT_PASS
    print("=== Enalquiler Bot Starting ===", flush=True)

    options = load_options()
    print(f"Options loaded: {options}", flush=True)

    MQTT_USER = options.get("mqtt_user", "idealista_bot")
    MQTT_PASS = options.get("mqtt_password", "idealista123")
    max_price = options.get("max_price", 1000)

    seen_ids = load_seen_ids()
    listings = scrape_listings(max_price)
    print(f"Total listings found: {len(listings)}", flush=True)

    new_listings = [l for l in listings if l["id"] not in seen_ids]
    print(f"New listings: {len(new_listings)}", flush=True)

    for listing in new_listings:
        mqtt_publish("enalquiler/listing", listing)
        seen_ids.add(listing["id"])

    save_seen_ids(seen_ids)
    print("Done.", flush=True)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error: {e}", flush=True)
        time.sleep(1800)
