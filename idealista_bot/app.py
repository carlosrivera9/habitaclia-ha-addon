import time
import json
import random
import paho.mqtt.publish as publish
from bs4 import BeautifulSoup

MQTT_HOST = "core-mosquitto"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASS = None

OPTIONS_FILE = "/data/options.json"
SEEN_IDS_FILE = "/data/seen_ids.json"


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
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
            auth={
                "username": MQTT_USER,
                "password": MQTT_PASS
            }
        )
    except Exception as e:
        print(f"MQTT error: {e}")


def build_url(city_slug, max_price, pets):
    base = f"https://www.idealista.com/alquiler-viviendas/{city_slug}/"

    params = f"?precio-hasta={max_price}"

    if pets:
        params += "&mascota=1"

    return base + params


def scrape_listings(url):

    print("Downloading page...")

    import requests

    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    html = response.text


    soup = BeautifulSoup(html, "html.parser")


    articles = soup.find_all(
        "article",
        class_="item"
    )


    listings = []


    for article in articles:

        try:

            link_tag = article.find(
                "a",
                class_="item-link"
            )

            if not link_tag:
                continue


            href = link_tag.get("href", "")

            title = link_tag.get(
                "title",
                ""
            ).strip()


            price_tag = article.find(
                "span",
                class_="item-price"
            )

            price = (
                price_tag.text.strip()
                if price_tag
                else "N/A"
            )


            details = []

            for d in article.find_all(
                "span",
                class_="item-detail"
            ):
                details.append(
                    d.text.strip()
                )


            full_url = (
                "https://www.idealista.com" + href
                if href
                else ""
            )


            listing_id = (
                href.strip("/").split("/")[-1]
                if href
                else title
            )


            listings.append(
                {
                    "id": listing_id,
                    "title": title,
                    "price": price,
                    "details": details,
                    "url": full_url
                }
            )


        except Exception as e:

            print(
                f"Error parsing listing: {e}"
            )


    print(
        f"Listings found: {len(listings)}"
    )

    return listings



def main():

    global MQTT_USER, MQTT_PASS


    options = load_options()


    MQTT_USER = options.get(
        "mqtt_user",
        "idealista_bot"
    )

    MQTT_PASS = options.get(
        "mqtt_password",
        "idealista123"
    )


    city = options.get(
        "city",
        "valencia-valencia"
    )

    max_price = options.get(
        "max_price",
        1500
    )

    pets = options.get(
        "pets",
        False
    )


    interval = (
        options.get(
            "interval_minutes",
            30
        )
        * 60
    )


    seen_ids = load_seen_ids()


    url = build_url(
        city,
        max_price,
        pets
    )


    print(
        f"Starting Idealista Bot — city: {city}, max_price: {max_price}, pets: {pets}"
    )

    print(
        f"Search URL: {url}"
    )



    while True:


        try:

            listings = scrape_listings(url)


            new_listings = [
                l for l in listings
                if l["id"] not in seen_ids
            ]


            for listing in new_listings:

                print(
                    f"New listing: {listing['title']} — {listing['price']}"
                )

                mqtt_publish(
                    "idealista_bot/listing",
                    listing
                )


                seen_ids.add(
                    listing["id"]
                )



            save_seen_ids(
                seen_ids
            )



            mqtt_publish(
                "idealista_bot/status",
                {
                    "status": "ok",
                    "city": city,
                    "total_found": len(listings),
                    "new_listings": len(new_listings),
                    "url": url
                }
            )



        except Exception as e:


            print(
                f"Unexpected error: {e}"
            )


            mqtt_publish(
                "idealista_bot/status",
                {
                    "status": "error",
                    "error": str(e)
                }
            )



        jitter = random.randint(
            -60,
            60
        )


        time.sleep(
            interval + jitter
        )



if __name__ == "__main__":
    print("===== APP STARTED =====", flush=True)
    main()
