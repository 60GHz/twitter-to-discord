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

    method = data.get("method")
    result = data.get("result", {})
    html = result.get("body", "")

    # --- Case 1: Nitter worked and gave timeline ---
    if method == "nitter":
        soup = BeautifulSoup(html, "html.parser")
        link = soup.select_one("a.tweet-link")
        if link and link.get("href"):
            href = link["href"].split("#")[0]
            return "https://x.com" + href if href.startswith("/") else href

        print(f"[INFO] Nitter returned non-timeline page for {username}")

    # --- Case 2: fallback to vxtwitter ---
    print(f"[FALLBACK] using vxtwitter for {username}")
    vx_url = f"https://vxtwitter.com/{username}"

    try:
        vx = requests.get(vx_url, headers=HEADERS, timeout=15, allow_redirects=True)
        # vxtwitter redirects to twitter.com/<user>
        if vx.url.startswith("https://twitter.com") or vx.url.startswith("https://x.com"):
            return vx.url
    except Exception as e:
        print(f"[ERROR] vxtwitter failed for {username}: {e}")

    return None

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
