import json
from datetime import datetime, timezone, timedelta

TZ_BKK = timezone(timedelta(hours=7))


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


def _zscore_emoji(v: float) -> str:
    if v < 0:  return '🔵'
    if v <= 4: return '🟢'
    if v <= 7: return '🟡'
    return '🔴'


def _fg_emoji(v: int) -> str:
    if v <= 24: return '🔴'
    if v <= 44: return '🟠'
    if v <= 55: return '🟡'
    if v <= 74: return '🟢'
    return '🟢'


def _fmt(price) -> str:
    return f'{price:,.2f}' if price is not None else 'N/A'


def _fv(data: dict, key: str, decimals: int = 2) -> str:
    v = data.get(key)
    return f'{v:.{decimals}f}' if v is not None else 'N/A'


def _chg_str(v: float, suffix: str = '') -> str:
    sign = '+' if v >= 0 else ''
    return f'{sign}{v:.2f}%{suffix}'


def build_daily(data: dict) -> str:
    d = data
    today        = datetime.now(TZ_BKK).strftime('%d %b %Y')
    signal       = '🟢 BTC' if d['above_ema200'] else '🔴 BTC'
    ema_check    = '🟢' if d['above_ema200'] else '🔴'
    az_emoji     = '🟢' if d['action_zone'] == 'bullish' else '🔴'
    rsi_emoji    = _rsi_emoji(d['rsi'])
    mvrv_emoji   = _mvrv_emoji(d['mvrv']) if d.get('mvrv') else '⚪'
    zscore_emoji = _zscore_emoji(d['mvrv_z_score']) if d.get('mvrv_z_score') is not None else '⚪'

    sth_rp = f"${_fmt(d.get('realized_price_sth'))}" if d.get('realized_price_sth') else 'N/A'
    lth_rp = f"${_fmt(d.get('realized_price_lth'))}" if d.get('realized_price_lth') else 'N/A'
    tmm    = f"${_fmt(d.get('true_market_mean'))}"   if d.get('true_market_mean')   else 'N/A'

    mvrv_str    = f"{d['mvrv']:.2f} {mvrv_emoji}" if d.get('mvrv') else 'N/A'
    zscore_str  = f"{d['mvrv_z_score']:.2f} {zscore_emoji}" if d.get('mvrv_z_score') is not None else 'N/A'

    return (
        f"📊 BTC Daily Status — @{today}\n"
        f"\n"
        f"{signal} · ${_fmt(d['price'])}  ({_chg_str(d['change_24h'])})\n"
        f"\n"
        f"📈 Technical\n"
        f"• EMA 200: {ema_check}  ·  RSI: {d['rsi']:.1f} {rsi_emoji}  ·  Action Zone: {az_emoji}\n"
        f"\n"
        f"⛓️ Onchain\n"
        f"Realized ${_fmt(d['realized_price'])}  ·  STH {sth_rp}  ·  LTH {lth_rp}  |  TMM {tmm}\n"
        f"MVRV {mvrv_str}  ·  STH {_fv(d, 'mvrv_sth')}  ·  LTH {_fv(d, 'mvrv_lth')}  |  Z-SCORE {zscore_str}\n"
        f"\n"
        f"🔗 Signal guide & emoji meanings link pinned in the comments below!"
    )


SYSTEM_PROMPT = """\
You are a crypto analyst. Write ONLY the AI Read section for a weekly BTC status post.
Return exactly 4 lines — no intro, no extra text, nothing else:

Read1: [1-line insight on Realized / TMM / NUPL / Supply Profit]
Read2: [1-line insight on MVRV / Z-SCORE / SOPR]
Wave: [your Elliott Wave call] · [1-line context]
Pattern: [chart pattern] · [brief note]

ELLIOTT WAVE (use ohlcv_last_120, 120 daily candles oldest→newest):
Count impulse (1→2→3→4→5) or corrective (A→B→C).
Rules:
• W2 retraces 50–61.8% of W1 (buy zone)
• W3 extends 1.618× W1 — strongest push
• W4 retraces ~38.2% of W3; W4 never enters W1 range
• W5 at 100–161.8% of W1 extension → watch for divergence
• A-B-C = corrective / counter-trend
Calls: "Wave 3 push ongoing" | "W4 pullback" | "W5 warn" | "A-B-C correction" | "Unclear"
Context (after ·): 1 key price observation

PATTERN (use ohlcv_last_120):
Types: bull flag · bear flag · ascending triangle · descending triangle · rising wedge · falling wedge · ascending channel · descending channel · "No clear pattern"
Add one brief note about where price sits in the pattern.
"""


def build_weekly_partial(data: dict) -> tuple[str, str]:
    """Returns (user_message_for_claude, partial_message_with_placeholders)."""
    d = data

    now      = datetime.now(TZ_BKK)
    today    = now.date()
    last_sun = today - timedelta(days=1)
    last_mon = today - timedelta(days=7)

    signal       = '🟢 BTC' if d['above_ema200'] else '🔴 BTC'
    ema_check    = '🟢' if d['above_ema200'] else '🔴'
    adx_check    = '🟢' if d['adx_trending'] else '🔴'
    az_emoji     = '🟢' if d['action_zone'] == 'bullish' else '🔴'
    rsi_emoji    = _rsi_emoji(d['rsi'])
    nupl_emoji   = _nupl_emoji(d['nupl']) if d.get('nupl') is not None else '⚪'
    mvrv_emoji   = _mvrv_emoji(d['mvrv']) if d.get('mvrv') else '⚪'
    zscore_emoji = _zscore_emoji(d['mvrv_z_score']) if d.get('mvrv_z_score') is not None else '⚪'
    fg_emoji     = _fg_emoji(d['fg_value'])

    r_str = f"${_fmt(d['resistance'])}" if d['resistance'] else 'N/A'
    s_str = f"${_fmt(d['support'])}"    if d['support']    else 'N/A'

    sth_rp     = f"${_fmt(d.get('realized_price_sth'))}" if d.get('realized_price_sth') else 'N/A'
    lth_rp     = f"${_fmt(d.get('realized_price_lth'))}" if d.get('realized_price_lth') else 'N/A'
    tmm        = f"${_fmt(d.get('true_market_mean'))}"   if d.get('true_market_mean')   else 'N/A'
    profit_pct = f"{d['supply_in_profit_pct']:.1f}%"    if d.get('supply_in_profit_pct') else 'N/A'

    mvrv_str   = f"{d['mvrv']:.2f} {mvrv_emoji}" if d.get('mvrv') else 'N/A'
    zscore_str = f"{d['mvrv_z_score']:.2f} {zscore_emoji}" if d.get('mvrv_z_score') is not None else 'N/A'
    nupl_str   = f"{d['nupl']:.2f} {nupl_emoji}" if d.get('nupl') is not None else 'N/A'

    partial = (
        f"📊 BTC Weekly Status — @{today.strftime('%d %b %Y')}"
        f" ({last_mon.strftime('%d %b')} - {last_sun.strftime('%d %b')})\n"
        f"\n"
        f"{signal} · ${_fmt(d['price'])}  ({_chg_str(d['change_7d'], ' 7d')})\n"
        f"\n"
        f"📈 Technical\n"
        f"• EMA 200: {ema_check}  ·  ADX: {d['adx']:.1f} {adx_check}  ·  RSI: {d['rsi']:.1f} {rsi_emoji}\n"
        f"• Action Zone: {az_emoji} ${_fmt(d['action_cross_price'])} ({d['action_days']} days ago)\n"
        f"• Key Levels: R {r_str}  ·  S {s_str}\n"
        f"• BOS: {d['bos_status']}\n"
        f"\n"
        f"⛓️ Onchain\n"
        f"Realized ${_fmt(d['realized_price'])}  ·  STH {sth_rp}  ·  LTH {lth_rp}  |  TMM {tmm}\n"
        f"NUPL {nupl_str}  ·  Supply Profit {profit_pct}\n"
        f"✨ [READ1]\n"
        f"MVRV {mvrv_str}  ·  STH {_fv(d, 'mvrv_sth')}  ·  LTH {_fv(d, 'mvrv_lth')}  |  Z-SCORE {zscore_str}\n"
        f"SOPR  ·  STH {_fv(d, 'sopr_sth', 3)}  ·  LTH {_fv(d, 'sopr_lth', 3)}\n"
        f"✨ [READ2]\n"
        f"F&G: {d['fg_value']} {fg_emoji}  · Dom: {d['btc_dominance']:.1f}%\n"
        f"\n"
        f"🌊 Elliott Wave\n"
        f"✨ [WAVE]\n"
        f"〽️ Wave Patterns\n"
        f"✨ [PATTERN]\n"
        f"\n"
        f"🔗 Signal guide & emoji meanings link pinned in the comments below!\n"
        f"✨ = AI-generated insight"
    )

    ohlcv_json   = json.dumps(d['ohlcv_last_120'], separators=(',', ':'))
    user_message = (
        f"ohlcv_last_120 (120 daily candles, oldest→newest):\n{ohlcv_json}\n\n"
        f"resistance={d['resistance']}  support={d['support']}\n"
        f"NUPL={d.get('nupl')}  MVRV={d.get('mvrv')}  Z-SCORE={d.get('mvrv_z_score')}\n"
        f"SOPR_STH={d.get('sopr_sth')}  SOPR_LTH={d.get('sopr_lth')}\n"
        f"realized={d.get('realized_price')}  TMM={d.get('true_market_mean')}"
        f"  supply_profit={d.get('supply_in_profit_pct')}\n\n"
        f"Write the 4 AI Read lines."
    )

    return user_message, partial


def assemble(partial: str, ai_text: str) -> str:
    """Inserts Claude's 4 AI lines into the pre-built partial message."""
    lines   = [l.strip() for l in ai_text.strip().splitlines() if l.strip()]
    read1   = next((l[len('Read1:'):].strip()   for l in lines if l.startswith('Read1:')),   'N/A')
    read2   = next((l[len('Read2:'):].strip()   for l in lines if l.startswith('Read2:')),   'N/A')
    wave    = next((l[len('Wave:'):].strip()    for l in lines if l.startswith('Wave:')),    'Unclear')
    pattern = next((l[len('Pattern:'):].strip() for l in lines if l.startswith('Pattern:')), 'No clear pattern')
    return (
        partial
        .replace('[READ1]',   read1)
        .replace('[READ2]',   read2)
        .replace('[WAVE]',    wave)
        .replace('[PATTERN]', pattern)
    )
