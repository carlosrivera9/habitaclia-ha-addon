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
        "Cookie": "userUUID=5ffdf959-3086-413d-8b96-e608f12b68d1; SESSION=73609f225c1dae83~a7eb45c1-2eaa-40e1-8c78-54dcabe466fa; afUserId=1f041023-504f-4f83-8f16-c04fb1ca3f66-p; PARAGLIDE_LOCALE=es; utag_main__sn=1; utag_main_ses_id=1782419287894%3Bexp-session; vacationalEnabler="true:6.0"; _clck=1yg0fpz%5E2%5Eg77%5E1%5E2367; _tt_enable_cookie=1; _ttp=01KW07FW6AE1Z1EB138GKJ51NY_.tt.1; utag_main__ss=0%3Bexp-session; utag_main__prevTsUrl=https%3A%2F%2Fwww.idealista.com%2F%3Bexp-session; utag_main__prevTsReferrer=https://www.idealista.com/%3Bexp-session; utag_main__prevTsSource=Portal sites%3Bexp-session; utag_main__prevTsCampaign=organicTrafficByTm%3Bexp-session; utag_main__prevTsProvider=%3Bexp-session; utag_main__prevTsNotificationId=%3Bexp-session; utag_main__prevTsProviderClickId=%3Bexp-session; _fbp=fb.1.1782419288318.616316089258157730.Bg; _pcid=%7B%22browserId%22%3A%22mqtyf8xz8ay0ziu1%22%2C%22_t%22%3A%22n6idcqa1%7Cmqtyf8y1%22%7D; _pctx=%7Bu%7DN4IgrgzgpgThIC4B2YA2qA05owMoBcBDfSREQpAeyRCwgEt8oBJAE0RXSwH18ykAbPVYBjAI6EAjAB8AtmPwBPAGYAORZJABfIA; _gcl_au=1.1.1642975584.1782419288; _hjSessionUser_250321=eyJpZCI6ImJkNDU5MTA3LTBlYmUtNTViZS1iNzI3LTJiYjcxNzQ2Y2FiMiIsImNyZWF0ZWQiOjE3ODI0MTkyODg0NDUsImV4aXN0aW5nIjp0cnVlfQ==; _hjSession_250321=eyJpZCI6ImM1MDkwOGVhLWJjODktNDQwYS04NjJkLThjYzZmOWRkYzg0MyIsImMiOjE3ODI0MTkyODg0NDYsInMiOjEsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MH0=; _hjHasCachedUserAttributes=true; utag_main__prevEventLink=; ABTastySession=mrasn=&lp=https%253A%252F%252Fwww.idealista.com%252F; ABTasty=uid=bjptaxpq3rgzapgm&fst=1782419288145&pst=-1&cst=1782419288145&ns=1&pvt=5&pvis=5&th=; g_state={"i_l":0,"i_ll":1782419306131,"i_b":"urGFPyDflSTsz/vpTYMFan+wWFqGgFvx2VbPSbTtVcg","i_e":{"enable_itp_optimization":24},"i_et":1782419306131}; lang=es; contacta7eb45c1-2eaa-40e1-8c78-54dcabe466fa="{'maxNumberContactsAllow':10}"; cookieSearch-1=%2Falquiler-viviendas%2Fvalencia-valencia%2F%3A1782419560653; utag_main__pn=6%3Bexp-session; utag_main__se=13%3Bexp-session; utag_main__st=1782421362811%3Bexp-session; utag_main__prevEventView=005-idealista/portal > portal > adResults > resultList > viewResults%3Bexp-session; utag_main__prevLevel2=005-idealista/portal%3Bexp-session; _last_search=officialZone; __rtbh.uid=%7B%22eventType%22%3A%22uid%22%2C%22id%22%3A%22unknown%22%2C%22expiryDate%22%3A%222027-06-25T20%3A32%3A42.855Z%22%7D; __rtbh.lid=%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%22jnduKQIziAIp2njwEJwa%22%2C%22expiryDate%22%3A%222027-06-25T20%3A32%3A42.856Z%22%7D; _pprv=eyJjb25zZW50Ijp7IjAiOnsibW9kZSI6Im9wdC1pbiJ9LCI3Ijp7Im1vZGUiOiJvcHQtaW4ifX0sInB1cnBvc2VzIjpudWxsLCJfdCI6Im42aWRjcWEwfG1xdHlmOHkwIn0%3D; _clsk=1le2dsf%5E1782419562955%5E6%5E0%5El.clarity.ms%2Fcollect; _uetsid=9e8c8d706e4a11f1b8fd6f1d78c4de82; _uetvid=404c76d0d1c711f0996f7fa1fd9f5fd7; cto_bundle=zxy0WF9JeTIwc2FYR3B2NGdDdDgxRVE0WHRmZiUyRkE1a2xveXA1dG5FenpraU1Yc0xYYTlNbUtQZ2wzb1dDclRQV3pNRko3aVJ2UDZpcGxEdDB5aGpQRzliZkp0cWJ1Uml2RXNaT21iUEF6S3RyJTJCZzhtV1YwWDFIcnQxOGxPV0NtTyUyRk15WmpmdVJPRmRoc1JSTVBMVnZqSm5TakElM0QlM0Q; ttcsid=1782419302932::-it1WPt7MBDGXyDr_LRb.1.1782419572839.0::1.257033.259900::260907.2.1156.127::0.0.0; ttcsid_C5OI33SVNBDLN9M57490=1782419296121::cOM2xp1oTg8CulrbuqYx.1.1782419572840.1; datadome=~d7MhDmHcGKXBuDLntxaMIO38w87haT4ZxjEjeUldsNhsICcaDMqdpF4RM4cdnJAFfK30CDwjl1BgYh1s7l_TWOIsySMMMnxrnyV9OlHpzk5vM_uqFc8QJwwE~GwfVQA"
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
