import feedparser
import requests
import json
import os

STATE_FILE = "state.json"

ACCOUNTS = {
    "Alina_AE": {
        "feed": "https://rsshub.app/twitter/user/Alina_AE",
        "webhook": os.environ["WEBHOOK_AQW_NEWS"]
    },
    "Datenshi6699": {
        "feed": "https://rsshub.app/twitter/user/Datenshi6699",
        "webhook": os.environ["WEBHOOK_NEW_ITEMS"]
    }
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def post(webhook, content):
    r = requests.post(webhook, json={"content": content})
    print(f"Posted to Discord: {r.status_code}")

def main():
    state = load_state()
    updated = False

    for user, cfg in ACCOUNTS.items():
        feed = feedparser.parse(cfg["feed"])

        if not feed.entries:
            print(f"[INFO] No RSS entries for {user}")
            continue

        latest = feed.entries[0].link

        if state.get(user) != latest:
            post(cfg["webhook"], latest)
            state[user] = latest
            updated = True
        else:
            print(f"[INFO] No new post for {user}")

    if updated:
        save_state(state)

if __name__ == "__main__":
    main()
