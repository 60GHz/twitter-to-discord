# migrate_state.py
import json, re, os, sys

ID_RE = re.compile(r"/status/(\d+)")
state_file = "state.json"
if not os.path.exists(state_file):
    print("no state.json found")
    sys.exit(0)

with open(state_file, "r") as f:
    s = json.load(f)

new = {}
for k, v in s.items():
    if isinstance(v, str):
        m = ID_RE.search(v)
        if m:
            new[k] = m.group(1)
            continue
        # sometimes the value already is digits
        if re.fullmatch(r"\d+", v):
            new[k] = v
            continue
    # fallback: leave as-is (but warn)
    print(f"warning: could not find id for {k} value={v}; removing key to be safe")
    # do not include invalid entries (so first-run posts only latest)
print("migrated:", new)
with open(state_file, "w") as f:
    json.dump(new, f)
print("state.json migrated")
