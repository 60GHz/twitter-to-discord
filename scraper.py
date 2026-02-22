# scraper.py
import feedparser
import requests
import json
import os
import time
import tempfile
from urllib.parse import urlparse

STATE_FILE = "state.json"

USERS = {
    "Alina_AE": os.environ.get("WEBHOOK_AQW_NEWS"),
    "Datenshi6699": os.environ.get("WEBHOOK_NEW_ITEMS"),
}

FEED_BASE = "https://nitter.net"  # keep nitter.net as canonical RSS provider

# TEST mode: if set (non-empty), the scraper will post but won't update state.json
TEST_MODE = os.environ.get("TEST_MODE", "").lower() in ("1", "true", "yes")
# Optionally set TEST_PREFIX to include in test posts (defaults to [TEST])
TEST_PREFIX = os.environ.get("TEST_PREFIX", "[TEST]")

HEADERS = {"User-Agent": "Mozilla/5.0"}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def atomic_write_state(state):
    # write atomically to avoid partial writes
    tfd, tmp = tempfile.mkstemp(dir=".", prefix="state.", text=True)
    with os.fdopen(tfd, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)

def canonicalize_link(url):
    """Turn nitter links into canonical x.com status links and strip fragments/queries."""
    if not url:
        return None
    # remove fragment and query
    p = urlparse(url)
    path = p.path.rstrip("/")
    # if nitter link like /User/status/123 or full nitter url:
    # extract username/status/... and return https://x.com/username/status/123
    # there are variations (nitter.net vs nitter.cz), handle generically
    if "nitter." in p.netloc or "nitter" in p.netloc:
        # path likely like '/User/status/123'
        return "https://x.com" + path
    # if it's already twitter/x
    if "twitter.com" in p.netloc or "x.com" in p.netloc:
        return p.scheme + "://" + p.netloc + path
    # fallback: return the given url without fragment/query
    return p.scheme + "://" + p.netloc + path

def fetch_feed_entries(username):
    rss_url = f"{FEED_BASE}/{username}/rss"
    feed = feedparser.parse(rss_url)
    if not feed or not getattr(feed, "entries", None):
        return []
    # feed.entries is newest-first; we want to handle them properly
    return feed.entries

def post_to_discord(webhook, link, is_test=False):
    if not webhook:
        print("[ERROR] missing webhook")
        return False
    post_link = link
    # convert nitter -> x link (redundant if we canonicalized, but safe)
    if post_link.startswith("https://nitter."):
        post_link = post_link.replace("https://nitter.net/", "https://x.com/").replace("https://nitter.cz/", "https://x.com/")
    content = f"{TEST_PREFIX} {post_link}" if is_test else post_link
    try:
        r = requests.post(webhook, json={"content": content}, timeout=15)
        print(f"[DISCORD] status {r.status_code}")
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[ERROR] posting to discord failed: {e}")
        return False

def process_user(username, webhook, state, posted_this_run):
    entries = fetch_feed_entries(username)
    if not entries:
        print(f"[INFO] no RSS entries for {username}")
        return False

    # compute canonical links list in newest->oldest order
    canonical_links = []
    for e in entries:
        link = e.get("link") or e.get("id") or ""
        c = canonicalize_link(link)
        if c:
            canonical_links.append(c)

    if not canonical_links:
        print(f"[INFO] no links found in RSS for {username}")
        return False

    last_seen = state.get(username)
    # If last_seen exists, find it in the list; else, we will only post the latest (avoid floods)
    if last_seen:
        # find index of last_seen in canonical_links
        try:
            idx = canonical_links.index(last_seen)
            # everything before idx (0..idx-1) are newer items (newest->older)
            new_links = canonical_links[:idx]
        except ValueError:
            # last_seen not found -> maybe state had old formatting; to be safe, post only the newest
            new_links = canonical_links[:1]
    else:
        # first-time run: post only the latest to avoid backfilling hundreds
        new_links = canonical_links[:1]

    if not new_links:
        print(f"[OK] no new post for {username}")
        return False

    # We have new links in newest->oldest order. Post oldest-first for correct timeline.
    new_links_to_post = list(reversed(new_links))

    any_posted = False
    for link in new_links_to_post:
        if link in posted_this_run:
            print(f"[SKIP] already posted this run: {link}")
            continue
        success = post_to_discord(webhook, link, is_test=TEST_MODE)
        if success:
            posted_this_run.add(link)
            any_posted = True
        else:
            print(f"[WARN] failed to post {link}; will not update state for it")
            # on failure we stop further posts to avoid partial state updates
            break

    # if we are not in test mode and we posted at least one, update state to newest posted link
    if any_posted and not TEST_MODE:
        newest_posted = new_links[0]  # new_links was newest->oldest, index 0 is newest
        state[username] = newest_posted
    elif not any_posted:
        # nothing posted
        pass

    return any_posted

def main():
    print("=== START SCRAPER ===")
    state = load_state()
    posted_this_run = set()
    updated = False

    for user, webhook in USERS.items():
        print(f"[CHECK] {user}")
        changed = process_user(user, webhook, state, posted_this_run)
        if changed:
            updated = True
        time.sleep(1)

    if updated and not TEST_MODE:
        # atomically write state and keep it for next runs
        atomic_write_state(state)
        print("[STATE] state.json updated")
    else:
        if TEST_MODE:
            print("[TEST] TEST_MODE active — state not changed")
        else:
            print("[STATE] no changes to state")

    print("=== FINISHED ===")

if __name__ == "__main__":
    main()
