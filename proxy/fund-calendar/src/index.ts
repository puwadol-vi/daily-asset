const FINNOMENA_BASE = 'https://www.finnomena.com';

const PROXY_HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
	'Accept': 'application/json, text/plain, */*',
	'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
	'Accept-Encoding': 'gzip, deflate, br',
	'Origin': 'https://www.finnomena.com',
	'Referer': 'https://www.finnomena.com/',
};

export default {
	async fetch(request: Request): Promise<Response> {
		const url = new URL(request.url);
		const target = FINNOMENA_BASE + url.pathname + url.search;

		const resp = await fetch(target, { headers: PROXY_HEADERS });

		return new Response(resp.body, {
			status: resp.status,
			headers: {
				'Content-Type': resp.headers.get('Content-Type') ?? 'application/json',
				'Access-Control-Allow-Origin': '*',
			},
		});
	},
} satisfies ExportedHandler;
