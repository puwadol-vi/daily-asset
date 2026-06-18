import json


def _rsi_emoji(v: float) -> str:
    if v < 30:   return '🔵'
    if v <= 70:  return '🟢'
    if v <= 80:  return '🟡'
    return '🔴'


def _mvrv_emoji(v: float) -> str:
    if v < 1.0:  return '🔵'
    if v <= 2.0: return '🟢'
    if v <= 3.5: return '🟡'
    return '🔴'


def _nupl_emoji(v: float) -> str:
    if v < 0:     return '🔵'
    if v <= 0.5:  return '🟢'
    if v <= 0.75: return '🟡'
    return '🔴'


def _fmt(price) -> str:
    return f'{price:,.2f}' if price is not None else 'N/A'


def _fmt_reserve(v: float) -> str:
    if v >= 1_000_000: return f'{v / 1_000_000:.2f}M'
    if v >= 1_000:     return f'{v / 1_000:.1f}K'
    return f'{v:.0f}'


def _fmt_flow(v: float) -> str:
    sign  = '+' if v >= 0 else '-'
    abs_v = abs(v)
    if abs_v >= 1_000_000: return f'{sign}{abs_v / 1_000_000:.2f}M'
    if abs_v >= 1_000:     return f'{sign}{abs_v / 1_000:.1f}K'
    return f'{sign}{abs_v:.0f}'


SYSTEM_PROMPT = """\
You are a crypto analyst. Write ONLY the "AI Read" section for a Discord BTC status post.
Return exactly 2 lines — no intro, no extra text, nothing else:

Wave: [your call] · [1-line context]
Pattern: [your call]

WAVE (Elliott Wave — use ohlcv_last_60, 60 daily candles oldest→newest):
Count impulse (1→2→3→4→5) or corrective (A→B→C).
Rules:
• W2 retraces 50–61.8% of W1 (buy zone)
• W3 extends 1.618× W1 — strongest push
• W4 retraces ~38.2% of W3 (add zone; W4 never enters W1 range)
• W5 at 100–161.8% of W1 extension → approach exit / watch for divergence
• A-B-C = corrective / counter-trend
Calls: "Wave 3 push ongoing" | "W4 pullback — watch for re-entry" | "W5 warn — approach exit" | "A-B-C correction" | "Unclear"
Context (after ·): 1 key observation e.g. "held $98,500 HL on Jun 12 · 6.5% to R $112,000"

PATTERN (use ohlcv_last_60):
Types: bull flag · bear flag · ascending triangle · descending triangle · rising wedge · falling wedge · ascending channel · "No clear pattern"
Add one brief note about where price sits relative to the pattern.
"""


def build_prompt(data: dict) -> tuple[str, str, str]:
    """Returns (system_prompt, user_message, partial_discord_message)."""
    d = data

    signal     = '🟢 BTC' if d['above_ema200'] and d['action_zone'] == 'bullish' else '🔴 BTC'
    ema_check  = '🟢' if d['above_ema200'] else '🔴'
    adx_check  = '🟢' if d['adx_trending'] else '🔴'
    rsi_emoji  = _rsi_emoji(d['rsi'])
    az_emoji   = '🟢' if d['action_zone'] == 'bullish' else '🔴'
    mvrv_emoji = _mvrv_emoji(d['mvrv']) if d['mvrv'] else '⚪'
    nupl_emoji = _nupl_emoji(d['nupl']) if d['nupl'] is not None else '⚪'
    chg        = f"+{d['change_24h']:.2f}" if d['change_24h'] >= 0 else f"{d['change_24h']:.2f}"
    r_str      = f"${_fmt(d['resistance'])}" if d['resistance'] else 'N/A'
    s_str      = f"${_fmt(d['support'])}"    if d['support']    else 'N/A'

    res_arrow  = '↑' if d['exchange_reserve_trend'] == 'rising' else '↓'
    res_val    = _fmt_reserve(d['exchange_reserve'])
    net_flow   = d['exchange_net_flow']
    flow_str   = _fmt_flow(net_flow)

    partial = (
        f"📊 BTC Daily Status — {d['date']}\n"
        f"\n"
        f"{signal} · ${_fmt(d['price'])}  ({chg}%)\n"
        f"\n"
        f"📈 Technical\n"
        f"• EMA 200: {ema_check}  |  ADX: {d['adx']:.1f} {adx_check}  |  RSI: {d['rsi']:.1f} {rsi_emoji}\n"
        f"• Action Zone: {az_emoji} ${_fmt(d['action_cross_price'])} ({d['action_days']} days ago)\n"
        f"• Key Levels: R {r_str}  |  S {s_str}\n"
        f"• BOS: {d['bos_status']}\n"
        f"\n"
        f"🤖 AI Read\n"
        f"• [WAVE]\n"
        f"• [PATTERN]\n"
        f"\n"
        f"🔗 Onchain\n"
        f"Realized Price ${_fmt(d['realized_price'])} · MVRV {d['mvrv']:.2f} {mvrv_emoji}\n"
        f"F&G: {d['fg_value']} {d['fg_label']}  · BTC Dom: {d['btc_dominance']:.1f}% {d['btc_dom_direction']}\n"
        f"Net Unrealized P/L {d['nupl']:.2f} {nupl_emoji} · Reserve {res_val}{res_arrow} {flow_str}"
    )

    ohlcv_json   = json.dumps(d['ohlcv_last_60'], separators=(',', ':'))
    user_message = (
        f"ohlcv_last_60 (60 daily candles, oldest→newest):\n{ohlcv_json}\n\n"
        f"resistance={d['resistance']}  support={d['support']}\n\n"
        "Write the 2 AI Read lines."
    )

    return SYSTEM_PROMPT, user_message, partial


def assemble(partial: str, ai_read: str) -> str:
    """Inserts Claude's Wave + Pattern lines into the pre-built message."""
    lines        = [l.strip() for l in ai_read.strip().splitlines() if l.strip()]
    wave_line    = next((l for l in lines if l.startswith('Wave:')),    'Wave: Unclear')
    pattern_line = next((l for l in lines if l.startswith('Pattern:')), 'Pattern: No clear pattern')
    return partial.replace('[WAVE]', wave_line).replace('[PATTERN]', pattern_line)
