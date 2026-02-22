# scraper.py
import requests
import feedparser
import json
import os
import time

STATE_FILE = "state.json"

USERS = {
    "Alina_AE": os.environ.get("WEBHOOK_AQW_NEWS"),
    "Datenshi6699": os.environ.get("WEBHOOK_NEW_ITEMS"),
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fetch_latest_from_rss(username):
    rss_url = f"https://nitter.cz/{username}/rss"
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"[ERROR] RSS fetch failed for {username}: {e}")
        return None

    if not feed.entries:
        print(f"[INFO] no RSS entries for {username}")
        return None

    entry = feed.entries[0]
    return entry.link

def post_to_discord(webhook, text):
    if not webhook:
        return
    r = requests.post(webhook, json={"content": text}, timeout=15)
    print(f"[DISCORD] status {r.status_code}")

def main():
    print("=== START SCRAPER ===")
    state = load_state()
    updated = False

    for user, webhook in USERS.items():
        print(f"[CHECK] {user}")
        latest = fetch_latest_from_rss(user)
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
