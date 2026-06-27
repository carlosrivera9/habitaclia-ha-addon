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

NO_PETS_KEYWORDS = [
    "no mascotas", "no se aceptan mascotas", "no animales",
    "no se admiten mascotas", "no se admite mascotas",
    "sin mascotas", "no pets", "no admite mascotas",
    "no aceptamos mascotas", "no se permite mascotas",
    "no se permiten mascotas", "no admitimos mascotas"
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

    url = f"https://www.enalquiler.com/search?provincia=48&poblacion=50692&precio_max={max_price}"
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
        cards = soup.find_all("li", class_="propertyCard")

        for card in cards:
            try:
                listing_id = card.get("list-item", "")
                if not listing_id:
                    continue

                link_tag = card.select_one("a.propertyCard__description--title")
                if not link_tag:
                    continue
                title = link_tag.get_text(strip=True)
                url_full = link_tag.get("href", "")

                price_tag = card.select_one("span.propertyCard__price--value")
                price_text = price_tag.get_text(strip=True) if price_tag else "N/A"
                price_num = int(re.sub(r'[^\d]', '', price_text)) if price_text != "N/A" else 99999

                location_tag = card.select_one("div.propertyCard__location p")
                location = location_tag.get_text(strip=True) if location_tag else "N/A"

                details = [li.get_text(strip=True) for li in card.select("ul.propertyCard__details li")]
                details_str = " | ".join(details) if details else "N/A"

                # Get description text for pets filtering
                desc_tag = card.select_one("p.propertyCard__description--txt")
                desc_text = desc_tag.get_text(strip=True).lower() if desc_tag else ""

                # Skip listings that explicitly say no pets
                if any(kw in desc_text for kw in NO_PETS_KEYWORDS):
                    print(f"  SKIP (no pets): {title[:50]}", flush=True)
                    continue

                print(f"  {title[:50]} | {price_num}€ | {location}", flush=True)

                listings.append({
                    "id": listing_id,
                    "title": title,
                    "price": f"{price_num} €/mes",
                    "details": details_str,
                    "location": location,
                    "url": url_full,
                })

            except Exception as e:
                print(f"Error parsing card: {e}", flush=True)
                continue

        print(f"Found {len(cards)} cards, {len(listings)} after filtering", flush=True)

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

    mqtt_publish("enalquiler/summary", {"listings": listings, "count": len(listings)})

    save_seen_ids(seen_ids)
    print("Done.", flush=True)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error: {e}", flush=True)
        time.sleep(1800)
