# scraper.py
import requests
import json
import os
import time
from bs4 import BeautifulSoup

STATE_FILE = "state.json"

USERS = {
    "Alina_AE": os.environ.get("WEBHOOK_AQW_NEWS"),
    "Datenshi6699": os.environ.get("WEBHOOK_NEW_ITEMS"),
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

def fetch_latest_from_worker(username):
    if not WORKER:
        print("[ERROR] WORKER_URL missing")
        return None

    url = f"{WORKER}/?user={username}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[ERROR] worker request failed for {username}: {e}")
        return None

    html = data.get("result", {}).get("body")
    if not html:
        print(f"[INFO] no HTML body for {username}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Most reliable: first tweet-link on the page
    link = soup.select_one("a.tweet-link")
    if not link or not link.get("href"):
        print(f"[INFO] no tweet-link found for {username}")
        return None

    href = link["href"].split("#")[0]
    if href.startswith("/"):
        return "https://x.com" + href

    return href

def post_to_discord(webhook, text):
    if not webhook:
        print("[ERROR] missing webhook")
        return
    r = requests.post(webhook, json={"content": text}, timeout=15)
    print(f"[DISCORD] status {r.status_code}")

def main():
    print("=== START SCRAPER ===")
    state = load_state()
    updated = False

    for user, webhook in USERS.items():
        print(f"[CHECK] {user}")
        latest = fetch_latest_from_worker(user)
        if not latest:
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
