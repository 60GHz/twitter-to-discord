import requests
import json
import os
from bs4 import BeautifulSoup

STATE_FILE = "state.json"

ACCOUNTS = {
    "Alina_AE": os.environ["WEBHOOK_AQW_NEWS"],
    "Datenshi6699": os.environ["WEBHOOK_NEW_ITEMS"]
}

NITTERS = [
    "https://nitter.net",
    "https://nitter.cz",
    "https://nitter.poast.org",
    "https://nitter.fdn.fr"
]

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
    for base in NITTERS:
        try:
            url = f"{base}/{username}"
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")
            tweet = soup.select_one("div.timeline-item")
            if not tweet:
                continue

            link = tweet.select_one("a.tweet-link")
            if not link:
                continue

            print(f"Found tweet for {username} via {base}")
            return "https://x.com" + link["href"]

        except Exception as e:
            print(f"{base} failed for {username}: {e}")

    return None

def post(webhook, content):
    r = requests.post(webhook, json={"content": content})
    print(f"Posted to Discord: {r.status_code}")

def main():
    state = load_state()
    updated = False

    for user, webhook in ACCOUNTS.items():
        latest = fetch_latest(user)
        if not latest:
            print(f"No tweet found for {user}")
            continue

        if state.get(user) != latest:
            post(webhook, latest)
            state[user] = latest
            updated = True
        else:
            print(f"No new tweet for {user}")

    if updated:
        save_state(state)

if __name__ == "__main__":
    main()
