#!/usr/bin/env python3
"""
Exchange a short-lived Explorer token for a permanent Page token.

Usage:
  1. Go to https://developers.facebook.com/tools/explorer/
  2. Select your App → Generate Access Token (User token, NOT Page token)
  3. Make sure permissions include: pages_manage_posts, pages_read_engagement
  4. Run: python get_facebook_token.py
"""

import requests

APP_ID     = input("App ID     (from Meta App Settings): ").strip()
APP_SECRET = input("App Secret (from Meta App Settings): ").strip()
PAGE_ID    = input("Page ID    (your FACEBOOK_PAGE_ID) : ").strip()
USER_TOKEN = input("Short-lived User Token (from Explorer): ").strip()

print()

# Step 1: Exchange short-lived user token → long-lived user token (60 days)
r = requests.get(
    "https://graph.facebook.com/oauth/access_token",
    params={
        "grant_type":        "fb_exchange_token",
        "client_id":         APP_ID,
        "client_secret":     APP_SECRET,
        "fb_exchange_token": USER_TOKEN,
    },
    timeout=10,
)
r.raise_for_status()
ll_user_token = r.json().get("access_token")
if not ll_user_token:
    print("FAILED step 1:", r.json())
    exit(1)
print("Step 1 OK — got long-lived user token (60 days)")

# Step 2: Use long-lived user token → permanent Page token
r2 = requests.get(
    f"https://graph.facebook.com/v19.0/{PAGE_ID}",
    params={
        "fields":       "access_token,name",
        "access_token": ll_user_token,
    },
    timeout=10,
)
r2.raise_for_status()
page_data = r2.json()
page_token = page_data.get("access_token")
if not page_token:
    print("FAILED step 2:", page_data)
    exit(1)

print(f"Step 2 OK — Page: {page_data.get('name')}")
print()
print("=" * 60)
print("PERMANENT PAGE TOKEN (never expires):")
print(page_token)
print("=" * 60)
print()
print("Put this in your .env:")
print(f"FACEBOOK_PAGE_TOKEN={page_token}")
