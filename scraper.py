# scraper.py
import feedparser
import requests
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

def fetch_latest_tweet(username):
    rss_url = f"https://nitter.net/{username}/rss"
    feed = feedparser.parse(rss_url)

    if not feed.entries:
        print(f"[INFO] no RSS entries for {username}")
        return None

    return feed.entries[0].link

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
        latest = fetch_latest_tweet(user)
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
