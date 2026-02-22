# scraper.py
import requests
import json
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

STATE_FILE = "state.json"

WEBHOOKS = {
    "Alina_AE": os.environ.get("WEBHOOK_AQW_NEWS"),
    "Datenshi6699": os.environ.get("WEBHOOK_NEW_ITEMS")
}

WORKER = os.environ.get("WORKER_URL", "").rstrip("/")

HEADERS = {"User-Agent": "Mozilla/5.0"}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fetch_via_worker(target_url):
    if not WORKER:
        print("[WARN] WORKER_URL not configured")
        return None
    fetch_url = f"{WORKER}/?url={quote_plus(target_url)}"
    try:
        r = requests.get(fetch_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[ERROR] worker fetch failed for {target_url}: {e}")
        return None

def parse_nitter(html):
    soup = BeautifulSoup(html, "html.parser")
    # common nitter timeline item selector
    item = soup.select_one("div.timeline-item")
    if not item:
        # fallback: some nitter instances use article.timeline-item or li
        item = soup.select_one("article.timeline-item, li.timeline-item")
    if not item:
        return None
    link = item.select_one("a.tweet-link")
    if not link or not link.get("href"):
        # fallback: some instances use data-link or relative anchors
        link = item.find("a", href=True)
    if not link or not link.get("href"):
        return None
    href = link.get("href")
    if href.startswith("/"):
        return "https://x.com" + href
    return href if href.startswith("http") else "https://x.com" + href

def post_to_discord(webhook, text):
    if not webhook:
        print("[ERROR] no webhook provided")
        return
    try:
        r = requests.post(webhook, json={"content": text}, timeout=15)
        print(f"[DISCORD] posted {r.status_code}")
    except Exception as e:
        print(f"[ERROR] posting to discord failed: {e}")

def main():
    print("=== START SCRAPER ===")
    state = load_state()
    updated = False

    for user, webhook in WEBHOOKS.items():
        print(f"[CHECK] {user}")
        nitter_url = f"https://nitter.cz/{user}"
        html = fetch_via_worker(nitter_url)
        if not html:
            print(f"[WARN] no HTML from worker for {user}")
            # try an alternate nitter instance if worker returned nothing
            alt = fetch_via_worker(f"https://nitter.net/{user}")
            if alt:
                html = alt
            else:
                continue

        latest = parse_nitter(html)
        if not latest:
            print(f"[INFO] no timeline item found for {user}")
            continue

        if state.get(user) != latest:
            print(f"[NEW] {user} -> {latest}")
            post_to_discord(webhook, latest)
            state[user] = latest
            updated = True
        else:
            print(f"[OK] no new post for {user}")

        time.sleep(1)

    if updated:
        save_state(state)
    print("=== FINISHED ===")

if __name__ == "__main__":
    main()
