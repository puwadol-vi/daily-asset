#!/usr/bin/env python3
"""
Inspect any token from Graph API Explorer.
Tells you if it's correct for posting photos to a Facebook Page (run_full_btc.py).
"""

import requests
from datetime import datetime, timezone

TOKEN = input("Paste your token from Graph API Explorer: ").strip()
print()

r = requests.get(
    "https://graph.facebook.com/debug_token",
    params={"input_token": TOKEN, "access_token": TOKEN},
    timeout=10,
)
raw = r.json()
data = raw.get("data", {})

token_type = data.get("type", "unknown")   # USER or PAGE
is_valid   = data.get("is_valid", False)
expires    = data.get("expires_at", 0)
scopes     = data.get("scopes", [])
error      = data.get("error", {})

print(f"Token type : {token_type}")
print(f"Valid      : {is_valid}")
print(f"Scopes     : {', '.join(scopes) if scopes else 'none'}")

if error:
    print(f"Error      : {error.get('message')}")

# ── compute days remaining ──────────────────────────────────────────────────
now = datetime.now(tz=timezone.utc)
if expires:
    exp_dt = datetime.fromtimestamp(expires, tz=timezone.utc)
    days_left = (exp_dt - now).days
    print(f"Expires    : {exp_dt.strftime('%Y-%m-%d %H:%M UTC')}  ({days_left} days left)")
else:
    days_left = None
    print("Expires    : never")

print()

# ── verdict ─────────────────────────────────────────────────────────────────
if not is_valid:
    print("STATUS: WRONG TOKEN — token is invalid or already expired.")
    print("        Go to Graph API Explorer and generate a new token.")

elif token_type == "USER":
    print("STATUS: WRONG TOKEN — this is a USER token, not a Page token.")
    print("        run_full_btc.py needs a PAGE token to post photos (attached_media).")
    print("        Run get_facebook_token.py and paste this USER token when asked.")

elif token_type == "PAGE":
    # check required scope
    missing = [s for s in ["pages_manage_posts"] if s not in scopes]

    if missing:
        print(f"STATUS: WRONG TOKEN — Page token is missing scopes: {', '.join(missing)}")
        print("        Regenerate from Explorer with pages_manage_posts permission.")

    elif days_left is not None and days_left <= 7:
        print(f"STATUS: CORRECT TOKEN but expires in {days_left} days — renew soon.")
        print("        Run get_facebook_token.py to get a permanent one.")

    elif days_left is not None:
        print(f"STATUS: CORRECT TOKEN but SHORT-TERM — {days_left} days remaining.")
        print("        It will stop working after that. Run get_facebook_token.py")
        print("        to exchange it for a permanent (never-expiring) Page token.")

    else:
        # Get page info
        r2 = requests.get(
            "https://graph.facebook.com/v19.0/me",
            params={"fields": "id,name", "access_token": TOKEN},
            timeout=10,
        )
        page = r2.json()
        print(f"STATUS: CORRECT TOKEN — permanent (never expires)")
        print(f"        Page name : {page.get('name')}")
        print(f"        Page ID   : {page.get('id')}")
        print()
        print("        Put this in .env:")
        print(f"        FACEBOOK_PAGE_ID={page.get('id')}")
        print(f"        FACEBOOK_PAGE_TOKEN=<this token>")

else:
    print(f"STATUS: WRONG TOKEN — unknown token type: {token_type}")
