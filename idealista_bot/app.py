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
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.google.es/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    session = requests.Session()
    session.headers.update(headers)
    try:
        session.get("https://www.idealista.com/", timeout=15)
        time.sleep(random.uniform(2, 5))
    except Exception:
        pass
    response = session.get(url, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article", class_="item")
    listings = []
    for article in articles:
        try:
            link_tag = article.find("a", class_="item-link")
            if not link_tag:
                continue
            href = link_tag.get("href", "")
            title = link_tag.get("title", "").strip()
            price_tag = article.find("span", class_="item-price")
            price = price_tag.text.strip() if price_tag else "N/A"
            details = [d.text.strip() for d in article.find_all("span", class_="item-detail")]
            full_url = f"https://www.idealista.com{href}" if href else ""
            listing_id = href.strip("/").split("/")[-1] if href else title
            listings.append({
                "id": listing_id,
                "title": title,
                "price": price,
                "details": details,
                "url": full_url,
            })
        except Exception as e:
            print(f"Error parsing listing: {e}")
    print(f"Listings found: {len(listings)}")
    return listings

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
