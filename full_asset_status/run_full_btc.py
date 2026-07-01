import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
import anthropic

sys.path.insert(0, str(Path(__file__).parent))

from fetch_btc import fetch_all, cache_price_snapshot, load_price_history
from prompt_btc import build_daily, build_weekly_partial, assemble, SYSTEM_PROMPT
from generate_chart_btc import generate as generate_chart
from generate_onchain_chart_btc import generate as generate_onchain

load_dotenv(Path(__file__).parent.parent / '.env')

TZ_BKK = timezone(timedelta(hours=7))


def _is_weekly() -> bool:
    return datetime.now(TZ_BKK).weekday() == 0  # Monday


# ── Facebook helpers ──────────────────────────────────────────────────────────

def _fb_upload_photo(img_path: str, page_id: str, token: str) -> str:
    with open(img_path, 'rb') as f:
        r = requests.post(
            f'https://graph.facebook.com/v19.0/{page_id}/photos',
            data={'published': 'false', 'access_token': token},
            files={'source': f},
        )
    r.raise_for_status()
    return r.json()['id']


def _fb_post(caption: str, img_paths: list = None) -> str:
    """Post to Facebook page. Returns log status string."""
    page_id = os.environ.get('FACEBOOK_PAGE_ID')
    token   = os.environ.get('FACEBOOK_PAGE_TOKEN')
    if not page_id or not token:
        return 'Facebook: skipped (no credentials)'
    try:
        payload = {'access_token': token, 'message': caption}
        if img_paths:
            photo_ids = [_fb_upload_photo(p, page_id, token) for p in img_paths]
            payload['attached_media'] = [{'media_fbid': pid} for pid in photo_ids]
        r = requests.post(
            f'https://graph.facebook.com/v19.0/{page_id}/feed',
            json=payload,
        )
        r.raise_for_status()
        post_id = r.json().get('id', '')
        url = f'https://www.facebook.com/{post_id.replace("_", "/posts/")}'
        return f'Facebook: posted OK\n{url}'
    except requests.HTTPError as e:
        body = e.response.json() if e.response else {}
        err  = body.get('error', {})
        return f'Facebook: ERROR {err.get("code")} — {err.get("message", str(e))}'
    except Exception as e:
        return f'Facebook: ERROR — {e}'


# ── Discord helpers ───────────────────────────────────────────────────────────

def _discord_post(message: str, img_paths: list = None) -> None:
    url = os.environ['FULL_ASSET_WEBHOOK_URL']
    if not img_paths:
        requests.post(url, json={'content': message}).raise_for_status()
        return
    handles = [open(p, 'rb') for p in img_paths]
    try:
        files = [
            (f'files[{i}]', (Path(p).name, h, 'image/png'))
            for i, (p, h) in enumerate(zip(img_paths, handles))
        ]
        requests.post(
            url,
            files=files,
            data={'payload_json': json.dumps({'content': message})},
        ).raise_for_status()
    finally:
        for h in handles:
            h.close()


def _log(fb_result: str) -> None:
    log_url = os.environ.get('DISCORD_LOG_URL')
    if log_url:
        requests.post(log_url, json={'content': f'Full Asset Status\n{fb_result}'})


# ── modes ─────────────────────────────────────────────────────────────────────

def _run_daily(data: dict) -> None:
    message   = build_daily(data)
    _discord_post(message)
    fb_result = _fb_post(message)
    _log(fb_result)
    print(f"Daily posted: {data['date']}")


def _run_weekly(data: dict, history: list) -> None:
    user_message, partial = build_weekly_partial(data)

    client   = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    response = client.messages.create(
        model='claude-opus-4-7',
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_message}],
    )
    message = assemble(partial, response.content[0].text)

    img1 = generate_chart(history,  output_path='/tmp/btc_chart.png')
    img2 = generate_onchain(history, output_path='/tmp/btc_onchain.png')

    _discord_post(message, img_paths=[img1, img2])
    fb_result = _fb_post(message, img_paths=[img1, img2])
    _log(fb_result)
    print(f"Weekly posted: {data['date']}")


def main() -> None:
    data = fetch_all()
    cache_price_snapshot(data)
    history = load_price_history()   # read after update — includes today

    if _is_weekly():
        _run_weekly(data, history)
    else:
        _run_daily(data)


if __name__ == '__main__':
    main()
