import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import anthropic

# make sibling imports work whether run from repo root or this directory
sys.path.insert(0, str(Path(__file__).parent))

from fetch_btc import fetch_all
from prompt_btc import build_prompt, assemble
from generate_chart_btc import generate as generate_chart

# load .env from repo root (one level up from full_asset_status/)
load_dotenv(Path(__file__).parent.parent / '.env')


def main() -> None:
    cache_path = Path(__file__).parent / 'cache.json'
    if not cache_path.exists():
        cache_path.write_text(json.dumps({'btc': {}}, indent=2))

    # 1. fetch all data once — shared by image and text
    data = fetch_all()

    # 2. pixel art chart image (ohlcv_last_60, ema200/12/26_series)
    img_path = generate_chart(data, output_path='/tmp/btc_chart.png')

    # 3. build partial message (all labels pre-computed) + Claude prompt (ohlcv only)
    system_prompt, user_message, partial = build_prompt(data)

    # 4. Claude API → Wave + Pattern lines only
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    response = client.messages.create(
        model='claude-opus-4-7',
        max_tokens=256,
        system=system_prompt,
        messages=[{'role': 'user', 'content': user_message}],
    )
    discord_message = assemble(partial, response.content[0].text)

    # 5. post image + text to both Discord channels
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

    print(f"Posted: {data['date']}")


if __name__ == '__main__':
    main()
