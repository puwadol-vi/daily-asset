import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import anthropic

sys.path.insert(0, str(Path(__file__).parent))

from fetch_btc import fetch_all
from prompt_btc import build_prompt, assemble
from generate_chart_btc import generate as generate_chart

load_dotenv(Path(__file__).parent.parent / '.env')


def _post_facebook(img_path: str, caption: str) -> str:
    """Returns a status string to report back to Discord."""
    page_id = os.environ.get('FACEBOOK_PAGE_ID')
    token   = os.environ.get('FACEBOOK_PAGE_TOKEN')
    if not page_id or not token:
        return 'Facebook: skipped (no credentials)'

    try:
        # Step 1: upload image as unpublished → no premature feed story
        with open(img_path, 'rb') as f:
            r1 = requests.post(
                f'https://graph.facebook.com/v19.0/{page_id}/photos',
                data={'published': 'false', 'access_token': token},
                files={'source': f},
            )
        r1.raise_for_status()
        photo_id = r1.json()['id']

        # Step 2: create feed post with photo + caption (JSON body → UTF-8 → emojis work)
        r2 = requests.post(
            f'https://graph.facebook.com/v19.0/{page_id}/feed',
            json={
                'access_token':   token,
                'message':        caption,
                'attached_media': [{'media_fbid': photo_id}],
            },
        )
        r2.raise_for_status()
        post_id = r2.json().get('id', '')
        url = f'https://www.facebook.com/{post_id.replace("_", "/posts/")}'
        return f'Facebook: posted OK\n{url}'

    except requests.HTTPError as e:
        body = e.response.json() if e.response else {}
        err  = body.get('error', {})
        return f'Facebook: ERROR {err.get("code")} — {err.get("message", str(e))}'
    except Exception as e:
        return f'Facebook: ERROR — {e}'


def main() -> None:
    cache_path = Path(__file__).parent / 'cache.json'
    if not cache_path.exists():
        cache_path.write_text(json.dumps({'btc': {}}, indent=2))

    data = fetch_all()

    img_path = generate_chart(data, output_path='/tmp/btc_chart.png')

    system_prompt, user_message, partial = build_prompt(data)

    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    response = client.messages.create(
        model='claude-opus-4-7',
        max_tokens=256,
        system=system_prompt,
        messages=[{'role': 'user', 'content': user_message}],
    )
    discord_message = assemble(partial, response.content[0].text)

    webhooks = [
        os.environ['DISCORD_WEBHOOK_URL'],
        os.environ['FULL_ASSET_WEBHOOK_URL'],
    ]
    for url in webhooks:
        with open(img_path, 'rb') as img_file:
            resp = requests.post(
                url,
                files={'file': ('btc_chart.png', img_file, 'image/png')},
                data={'payload_json': json.dumps({'content': discord_message})},
            )
        resp.raise_for_status()

    fb_result = _post_facebook(img_path, discord_message)

    # Report Facebook result back to Discord
    for url in webhooks:
        requests.post(url, json={'content': fb_result})

    print(f"Posted: {data['date']}")


if __name__ == '__main__':
    main()
