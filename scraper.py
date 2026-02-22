import requests
import json
import os
from bs4 import BeautifulSoup

STATE_FILE = "state.json"

ACCOUNTS = {
    "Alina_AE": os.environ["WEBHOOK_AQW_NEWS"],
    "Datenshi6699": os.environ["WEBHOOK_NEW_ITEMS"]
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fetch_latest(username):
    url = f"https://nitter.net/{username}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    tweet = soup.select_one("div.timeline-item")
    if not tweet:
        return None

    link = tweet.select_one("a.tweet-link")
    if not link:
        return None

    return "https://x.com" + link["href"]

def post(webhook, content):
    requests.post(webhook, json={"content": content})

def main():
    state = load_state()
    updated = False

    for user, webhook in ACCOUNTS.items():
        latest = fetch_latest(user)
        if not latest:
            continue

        if state.get(user) != latest:
            post(webhook, latest)  # link only = best Discord embed
            state[user] = latest
            updated = True

    if updated:
        save_state(state)

if __name__ == "__main__":
    main()
