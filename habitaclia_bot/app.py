import time
import json
import random
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

def build_url(page=1):
    base = "https://www.enalquiler.com/alquilar/alquiler-pisos-mascota-valencia_2_50692_48.html"
    if page > 1:
        base = f"https://www.enalquiler.com/alquilar/alquiler-pisos-mascota-valencia_2_50692_48-{page}.html"
    return base

def scrape_listings(max_price):
    listings = []
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.enalquiler.com/",
    }

    for page in range(1, 6):
        url = build_url(page)
        print(f"Fetching: {url}", flush=True)

        try:
            time.sleep(random.uniform(2, 4))
            response = requests.get(url, headers=headers, timeout=20)
            response.encoding = 'latin-1'
            print(f"Status: {response.status_code}", flush=True)

            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select("li.ad-preview")

            if not items:
                print(f"No listings on page {page}, stopping", flush=True)
                break

            for item in items:
                try:
                    link_tag = item.select_one("a[href*='alquiler_piso']")
                    if not link_tag:
                        continue
                    href = link_tag["href"]
                    listing_id = href.split("_")[-1].replace(".html", "")
                    url_full = "https://www.enalquiler.com" + href if href.startswith("/") else href

                    title = link_tag.get_text(strip=True)

                    price_tag = item.select_one(".ad-price, .precio, [class*='price']")
                    price_text = price_tag.get_text(strip=True) if price_tag else "N/A"

                    price_num = int(''.join(filter(str.isdigit, price_text))) if price_text != "N/A" else 99999

                    if price_num > max_price:
                        continue

                    details = [d.get_text(strip=True) for d in item.select("li")]
                    details_str = " | ".join(details[:3]) if details else "N/A"

                    listings.append({
                        "id": listing_id,
                        "title": title,
                        "price": price_text,
                        "details": details_str,
                        "url": url_full,
                    })

                except Exception as e:
                    print(f"Error parsing item: {e}", flush=True)
                    continue

            print(f"Page {page}: found {len(items)} items", flush=True)

        except Exception as e:
            print(f"Request error on page {page}: {e}", flush=True)
            break

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
