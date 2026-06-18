import time
import json
import random
import requests
import paho.mqtt.publish as publish
from bs4 import BeautifulSoup

MQTT_HOST = "core-mosquitto"
OPTIONS_FILE = "/data/options.json"
SEEN_IDS_FILE = "/data/seen_ids.json"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
        publish.single(topic, json.dumps(payload), hostname=MQTT_HOST)
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
        "Referer": "https://www.idealista.com/",
        "DNT": "1",
    }

    session = requests.Session()
    # First hit the homepage to get cookies (helps avoid blocks)
    try:
        session.get("https://www.idealista.com/", headers=headers, timeout=15)
        time.sleep(random.uniform(2, 5))
    except Exception:
        pass

    response = session.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article", class_="item")

    listings = []
    for article in articles:
        try:
            link_tag = article.find("a", class_="item-link")
            title = link_tag.get("title", "").strip() if link_tag else ""
            href = link_tag.get("href", "") if link_tag else ""
            full_url = f"https://www.idealista.com{href}" if href else ""

            price_tag = article.find("span", class_="item-price")
            price = price_tag.text.strip() if price_tag else "N/A"

            detail_tags = article.find_all("span", class_="item-detail")
            details = [d.text.strip() for d in detail_tags]

            desc_tag = article.find("div", class_="item-description")
            description = desc_tag.text.strip() if desc_tag else ""

            # Use the URL path as a stable ID
            listing_id = href.strip("/").split("/")[-1] if href else title

            listings.append({
                "id": listing_id,
                "title": title,
                "price": price,
                "details": details,
                "description": description[:200],
                "url": full_url,
            })
        except Exception as e:
            print(f"Error parsing listing: {e}")
            continue

    return listings

def main():
    options = load_options()
    city = options.get("city", "valencia-valencia")
    max_price = options.get("max_price", 1500)
    pets = options.get("pets", False)
    interval = options.get("interval_minutes", 30) * 60

    seen_ids = load_seen_ids()
    url = build_url(city, max_price, pets)

    print(f"Starting Idealista Bot — city: {city}, max_price: {max_price}, pets: {pets}")
    print(f"Search URL: {url}")

    while True:
        try:
            listings = scrape_listings(url)
            new_listings = [l for l in listings if l["id"] not in seen_ids]

            for listing in new_listings:
                print(f"New listing: {listing['title']} — {listing['price']}")
                mqtt_publish("idealista_bot/listing", listing)
                seen_ids.add(listing["id"])

            save_seen_ids(seen_ids)

            mqtt_publish("idealista_bot/status", {
                "status": "ok",
                "city": city,
                "total_found": len(listings),
                "new_listings": len(new_listings),
                "url": url,
            })

        except requests.HTTPError as e:
            print(f"HTTP error (possibly blocked): {e}")
            mqtt_publish("idealista_bot/status", {"status": "blocked", "error": str(e)})
        except Exception as e:
            print(f"Unexpected error: {e}")
            mqtt_publish("idealista_bot/status", {"status": "error", "error": str(e)})

        # Random sleep to appear more human
        jitter = random.randint(-60, 60)
        time.sleep(interval + jitter)

if __name__ == "__main__":
    main()
