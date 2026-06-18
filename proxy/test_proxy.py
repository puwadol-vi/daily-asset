import requests

WORKER_URL = 'https://fund-calendar.pdevspaceth.workers.dev'

url = f'{WORKER_URL}/fn3/api/fund/public/list'
print(f'Testing: {url}')

resp = requests.get(url, timeout=15)
print(f'Status: {resp.status_code}')

if resp.ok:
    data = resp.json()
    print(f'OK — got {len(data)} funds')
    sample = next((f for f in data if f.get('short_code') == 'SCBAXJ(E)'), None)
    if sample:
        print(f'SCBAXJ(E) found: id={sample["id"]}')
    else:
        print('SCBAXJ(E) not found in list')
else:
    print(f'FAILED: {resp.text[:300]}')
