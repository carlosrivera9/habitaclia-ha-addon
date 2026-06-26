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
            auth={"username": MQTT_USER, "password": MQTT_PASS}
        )
        print(f"MQTT published to {topic}")
    except Exception as e:
        print(f"MQTT error: {e}")

def build_url(city_slug, max_price, pets, page=1):
    base = f"https://www.habitaclia.com/alquiler-{city_slug}.htm"
    params = f"?precio_hasta={max_price}"
    if pets:
        params += "&animales=1"
    if page > 1:
        params += f"&pagina={page}"
    return base + params

def scrape_listings(city_slug, max_price, pets):
    listings = []
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.habitaclia.com/",
    }

    for page in range(1, 4):
        url = build_url(city_slug, max_price, pets, page)
        print(f"Fetching: {url}", flush=True)

        try:
            time.sleep(random.uniform(2, 5))
            response = requests.get(url, headers=headers, timeout=20)
            print(f"Status: {response.status_code}", flush=True)

            if response.status_code != 200:
                print(f"Non-200 response, stopping pagination", flush=True)
                break

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("article")

            if not articles:
                print(f"No articles found on page {page}, stopping", flush=True)
                break

            for article in articles:
                try:
                    listing_id = article.get("data-id") or article.get("id", "")
                    title_tag = article.find(["h2", "h3", "a"])
                    title = title_tag.get_text(strip=True) if title_tag else "N/A"
                    price_tag = article.find(class_=lambda c: c and "price" in c.lower())
                    price = price_tag.get_text(strip=True) if price_tag else "N/A"
                    link_tag = article.find("a", href=True)
                    link = "https://www.habitaclia.com" + link_tag["href"] if link_tag and link_tag["href"].startswith("/") else (link_tag["href"] if link_tag else "N/A")
                    location_tag = article.find(class_=lambda c: c and "location" in c.lower())
                    location = location_tag.get_text(strip=True) if location_tag else "N/A"
                    if listing_id:
                        listings.append({
                            "id": listing_id,
                            "title": title,
                            "price": price,
                            "location": location,
                            "url": link,
                        })
                except Exception as e:
                    print(f"Error parsing article: {e}", flush=True)
                    continue

            print(f"Page {page}: found {len(articles)} articles", flush=True)

        except Exception as e:
            print(f"Request error on page {page}: {e}", flush=True)
            break

    return listings

def main():
    global MQTT_USER, MQTT_PASS
    print("=== Habitaclia Bot Starting ===", flush=True)

    options = load_options()
    print(f"Options loaded: {options}", flush=True)

    MQTT_USER = options.get("mqtt_user", "idealista_bot")
    MQTT_PASS = options.get("mqtt_password", "idealista123")
    city_slug = options.get("city", "valencia-en-valencia")
    max_price = options.get("max_price", 1000)
    pets = options.get("pets", True)

    seen_ids = load_seen_ids()
    listings = scrape_listings(city_slug, max_price, pets)
    print(f"Total listings found: {len(listings)}", flush=True)

    new_listings = [l for l in listings if l["id"] not in seen_ids]
    print(f"New listings: {len(new_listings)}", flush=True)

    for listing in new_listings:
        mqtt_publish("habitaclia/listing", listing)
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
EOF
