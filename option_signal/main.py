#!/usr/bin/env python3
"""
Sell-Option Signal (CSP / Covered Call) — run once per day via cron.
Cron: 5 8 * * * cd /path && venv/bin/python3 option_signal/main.py >> cron.log 2>&1
(08:05 UTC = 15:05 ICT, every day — 5 min after Binance's daily 08:00 UTC option rollover)

Binance BTC daily options list/expire at 08:00 UTC every day, so the
suggested contract is always simply "expires tomorrow" (1 DTE).

This is an advisory alert (checklist + suggested strike), not an execution bot.
See option_signal/Bitcoin_Options_Income_Strategy.md for the strategy spec.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd
import ta
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / '.env')

# ── config ───────────────────────────────────────────────────────────────────

CANDLE_LIMIT      = 500   # 4H candles fetched (~83 days)
VPVR_LOOKBACK     = 360   # trailing 4H candles used for the histogram (~60 days)
VPVR_BINS         = 50
HVN_PERCENTILE    = 70     # bins at/above this volume percentile are HVNs
EMA_WINDOW        = 200   # 4H EMA — second, independent trend confirmation

ADX_SIDEWAYS_MAX  = 25   # below this = no confirmed trend either way -> sell against structure
ADX_STRONG        = 40   # above this + right direction = confirmed trend -> sell near the money
STOCH_OVERSOLD    = 20
STOCH_OVERBOUGHT  = 80

# Strike buffers, scaled by ATR(14) rather than a fixed % — pushes strikes
# further out-of-the-money (safer, less premium) the more volatile BTC is.
NEAR_BUFFER_ATR_MULT   = 1.0   # near-the-money, trend-following entry
STRUCT_BUFFER_ATR_MULT = 2.0   # at-structure, sideways entry (wider, safer)

RV_LOOKBACK      = 42     # 4H bars (~7 days) for realized-vol comparison
FUNDING_EXTREME  = 0.0005 # 0.05%/8h (~55%/yr) — crowded-positioning threshold
IV_RV_LOW        = 0.8    # below this: premium too cheap for the realized risk
IV_RV_HIGH       = 2.0    # above this: vol spike / event risk

# All three overlays below only ever DEMOTE a 'near' (trend-confirmed) signal
# down to 'structure' (or None if no HVN level exists) — they never upgrade a
# signal, matching the "less risk" preference this module was built around.


# ── data ─────────────────────────────────────────────────────────────────────

def make_exchange():
    return ccxt.binance({'enableRateLimit': True})


def fetch_4h_candles(exchange) -> pd.DataFrame:
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '4h', limit=CANDLE_LIMIT)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df[:-1].reset_index(drop=True)  # exclude forming candle


def fetch_funding_rate(exchange):
    """Perp funding rate, per-8h. None on failure — this is a soft signal,
    a transient API hiccup shouldn't take down the whole alert."""
    try:
        fr = exchange.fetch_funding_rate('BTC/USDT:USDT')
        return float(fr['fundingRate'])
    except Exception:
        return None


def fetch_target_expiry_symbols(exchange, expiry_dt: datetime) -> list:
    """All BTC option contracts (both sides) for the Binance-listed expiry
    nearest to (at or after) our target date."""
    target_ts = int(expiry_dt.replace(hour=8, minute=0, second=0, microsecond=0).timestamp() * 1000)
    info = exchange.eapiPublicGetExchangeInfo()
    btc_opts = [o for o in info['optionSymbols']
                if o['symbol'].startswith('BTC-') and o['status'] == 'TRADING']
    if not btc_opts:
        return []
    expiries = sorted(set(int(o['expiryDate']) for o in btc_opts))
    chosen = next((e for e in expiries if e >= target_ts), expiries[-1])
    return [o for o in btc_opts if int(o['expiryDate']) == chosen]


def nearest_contract(symbols: list, target_price: float, side: str):
    candidates = [o for o in symbols if o['side'] == side]
    if not candidates:
        return None
    return min(candidates, key=lambda o: abs(float(o['strikePrice']) - target_price))


def fetch_mark(exchange, symbol: str):
    try:
        r = exchange.eapiPublicGetMark({'symbol': symbol})
        d = r[0]
        return {'markIV': float(d['markIV']), 'delta': float(d['delta']), 'markPrice': float(d['markPrice'])}
    except Exception:
        return None


# ── indicators ───────────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> dict:
    df = df.copy()
    adx_ind = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)
    df['adx']    = adx_ind.adx()
    df['di_pos'] = adx_ind.adx_pos()   # +DI: strength of the up-move
    df['di_neg'] = adx_ind.adx_neg()   # -DI: strength of the down-move
    df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['ema_200'] = ta.trend.ema_indicator(df['close'], window=EMA_WINDOW)

    srsi = ta.momentum.StochRSIIndicator(df['close'], window=14, smooth1=3, smooth2=3)
    df['stochrsi_k'] = srsi.stochrsi_k() * 100
    df['stochrsi_d'] = srsi.stochrsi_d() * 100

    last = df.iloc[-1]
    return {
        'close':      float(last['close']),
        'atr_14':     float(last['atr_14']),
        'adx':        float(last['adx']),
        'di_pos':     float(last['di_pos']),
        'di_neg':     float(last['di_neg']),
        'ema_200':    float(last['ema_200']),
        'stochrsi_k': float(last['stochrsi_k']),
        'stochrsi_d': float(last['stochrsi_d']),
    }


def compute_realized_vol(df: pd.DataFrame, lookback: int = RV_LOOKBACK) -> float:
    """Annualized realized vol from trailing 4H log-returns (6 bars/day)."""
    closes = df['close'].tail(lookback + 1).reset_index(drop=True)
    log_ret = np.log(closes / closes.shift(1)).dropna()
    return float(log_ret.std() * np.sqrt(6 * 365))


def compute_vpvr(df: pd.DataFrame, price: float) -> dict:
    window = df.tail(VPVR_LOOKBACK).reset_index(drop=True)
    typical = (window['high'] + window['low'] + window['close']) / 3

    lo, hi = window['low'].min(), window['high'].max()
    edges  = np.linspace(lo, hi, VPVR_BINS + 1)
    centers = (edges[:-1] + edges[1:]) / 2

    bin_idx = np.clip(np.digitize(typical, edges) - 1, 0, VPVR_BINS - 1)
    vol_per_bin = np.zeros(VPVR_BINS)
    for idx, vol in zip(bin_idx, window['volume']):
        vol_per_bin[idx] += vol

    poc_idx = int(np.argmax(vol_per_bin))
    poc     = float(centers[poc_idx])

    threshold = np.percentile(vol_per_bin[vol_per_bin > 0], HVN_PERCENTILE)
    hvn_prices = sorted(float(c) for c, v in zip(centers, vol_per_bin) if v >= threshold and v > 0)

    below = [p for p in hvn_prices if p <= price]
    above = [p for p in hvn_prices if p > price]
    support    = max(below) if below else None
    resistance = min(above) if above else None

    return {'poc': poc, 'support': support, 'resistance': resistance}


# ── strategy logic ───────────────────────────────────────────────────────────

def evaluate(ind: dict, vp: dict) -> dict:
    """
    Each side (put/call) independently gets one of three base states (before
    the funding/IV overlay is applied — see apply_overlay()):
      'skip'      — trend is confirmed AND pointed against this side
      'near'      — trend confirmed AND strongly favors this side AND price
                    is on the agreeing side of EMA200 (second confirmation)
      'structure' — ADX < 25, a genuinely confirmed sideways market — or a
                    'near' case whose EMA200 didn't agree, demoted here
    None covers the ambiguous ADX 25-40 band, or a demoted 'near' with no
    HVN level to fall back on.
    """
    adx = ind['adx']
    uptrend   = ind['di_pos'] > ind['di_neg']
    downtrend = ind['di_neg'] > ind['di_pos']
    trending  = adx >= ADX_SIDEWAYS_MAX
    strong    = adx > ADX_STRONG
    trend_label = ('uptrend' if uptrend else 'downtrend') if trending else 'sideways'
    price_above_ema = ind['close'] > ind['ema_200']

    k = ind['stochrsi_k']
    if k < STOCH_OVERSOLD:
        stoch_zone = 'oversold'
    elif k > STOCH_OVERBOUGHT:
        stoch_zone = 'overbought'
    else:
        stoch_zone = 'neutral'

    def _side_state(level, favorable: bool, opposing: bool, ema_agrees: bool):
        if trending and opposing:
            return 'skip'
        if strong and favorable:
            return 'near' if ema_agrees else ('structure' if level is not None else None)
        if not trending and level is not None:
            return 'structure'
        return None

    put_state  = _side_state(vp['support'],    favorable=uptrend,   opposing=downtrend, ema_agrees=price_above_ema)
    call_state = _side_state(vp['resistance'], favorable=downtrend, opposing=uptrend,   ema_agrees=not price_above_ema)

    return {
        'adx': adx, 'trending': trending, 'strong': strong,
        'uptrend': uptrend, 'downtrend': downtrend, 'trend_label': trend_label,
        'price_above_ema': price_above_ema,
        'stoch_zone': stoch_zone,
        'put_state': put_state, 'call_state': call_state,
    }


def fetch_atm_iv(exchange, symbols: list, price: float):
    """Live IV of the near-the-money contract for the target expiry — the
    general 'is premium rich or cheap right now' reference shown in the
    header, independent of whichever specific strike a side suggests."""
    if not symbols:
        return None
    contract = nearest_contract(symbols, price, 'CALL')
    mark = fetch_mark(exchange, contract['symbol']) if contract else None
    return mark['markIV'] if mark else None


def apply_overlay(exchange, is_put: bool, state, level, symbols: list,
                   funding_rate, rv: float, atr: float, price: float) -> dict:
    """Looks up the real listed contract nearest the ATR-computed strike for
    'near', 'structure', or the ⏸️ reference case (state is None but a level
    exists) — purely for display (real delta/premium/IV alongside the
    ATR-derived strike, which stays the actual selection method).

    Only 'near' can be demoted -> 'structure' (or None if there's no HVN to
    fall back on) when funding is crowded against this side, or live IV is
    too cheap or spiking relative to realized vol. Never upgrades a state."""
    result = {'state': state, 'contract': None, 'mark': None, 'iv_rv': None, 'reasons': []}
    if state not in ('near', 'structure') and not (state is None and level is not None):
        return result

    if state == 'near':
        target_strike = price - NEAR_BUFFER_ATR_MULT * atr if is_put else price + NEAR_BUFFER_ATR_MULT * atr
    else:
        target_strike = level - STRUCT_BUFFER_ATR_MULT * atr if is_put else level + STRUCT_BUFFER_ATR_MULT * atr

    option_side = 'PUT' if is_put else 'CALL'
    try:
        contract = nearest_contract(symbols, target_strike, option_side)
        mark = fetch_mark(exchange, contract['symbol']) if contract else None
    except Exception:
        contract, mark = None, None
    result['contract'], result['mark'] = contract, mark
    if mark and rv:
        result['iv_rv'] = mark['markIV'] / rv

    if state != 'near':
        return result

    demote = False
    if funding_rate is not None:
        if is_put and funding_rate > FUNDING_EXTREME:
            demote = True
            result['reasons'].append(f'crowded longs (funding {funding_rate*100:.3f}%/8h) — long-flush risk')
        if not is_put and funding_rate < -FUNDING_EXTREME:
            demote = True
            result['reasons'].append(f'crowded shorts (funding {funding_rate*100:.3f}%/8h) — short-squeeze risk')

    if result['iv_rv'] is not None:
        if result['iv_rv'] < IV_RV_LOW:
            demote = True
            result['reasons'].append(f'IV/RV {result["iv_rv"]:.2f} — premium too cheap for the realized risk')
        elif result['iv_rv'] > IV_RV_HIGH:
            demote = True
            result['reasons'].append(f'IV/RV {result["iv_rv"]:.2f} — vol spike, elevated event risk')

    if demote:
        result['state'] = 'structure' if level is not None else None
    return result


def next_expiry(now: datetime) -> tuple:
    """Binance daily options expire 08:00 UTC — always tomorrow (1 DTE),
    the alert now runs every day including weekends."""
    return now + timedelta(days=1), 1


def entry_timing_note(now: datetime) -> str:
    rollover = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < rollover:
        rollover -= timedelta(days=1)
    minutes_since = (now - rollover).total_seconds() / 60
    if minutes_since <= 30:
        return f"🟢 opened {minutes_since:.0f}m after today's 08:00 UTC rollover — full premium window"
    hours = minutes_since / 60
    return f'🟡 opened {hours:.1f}h after rollover — reduced premium window, consider skipping today'


# ── message ──────────────────────────────────────────────────────────────────

def _plan_line(side: str, state, price: float, atr: float, level, adx: float,
               is_put: bool, dte: int, expiry_str: str, overlay: dict) -> list:
    if state == 'skip':
        against = 'downtrend' if is_put else 'uptrend'
        return [f'🚫 SELL {side} — skip: confirmed {against} (ADX {adx:.1f}) — any strike can break in a real trend']

    if state == 'near':
        buffer_ = NEAR_BUFFER_ATR_MULT * atr
        approx_strike = round(price - buffer_, -2) if is_put else round(price + buffer_, -2)
        mark, contract = overlay.get('mark'), overlay.get('contract')
        if mark and contract:
            strike = float(contract['strikePrice'])
            lines = [
                f'🎯 SELL {side} — strike ${strike:,.0f}  (Δ{mark["delta"]:.2f}, premium ${mark["markPrice"]:,.0f}, IV {mark["markIV"]*100:.0f}%) · {dte} DTE (expires {expiry_str})',
            ]
            if overlay.get('iv_rv') is not None:
                lines.append(f'   IV/RV {overlay["iv_rv"]:.2f} — healthy premium for the realized risk')
        else:
            lines = [
                f'🎯 SELL {side} — strike ~${approx_strike:,.0f}  (near spot, {NEAR_BUFFER_ATR_MULT:.1f}×ATR ${buffer_:,.0f} away, live option data unavailable) · {dte} DTE (expires {expiry_str})',
            ]
        return lines

    if state == 'structure':
        level_name = 'support' if is_put else 'resistance'
        buffer_ = STRUCT_BUFFER_ATR_MULT * atr
        approx_strike = round(level - buffer_, -2) if is_put else round(level + buffer_, -2)
        mark, contract = overlay.get('mark'), overlay.get('contract')
        if mark and contract:
            strike = float(contract['strikePrice'])
            lines = [
                f'🛡️ SELL {side} — strike ${strike:,.0f}  (Δ{mark["delta"]:.2f}, premium ${mark["markPrice"]:,.0f}, IV {mark["markIV"]*100:.0f}%, '
                f'beyond {level_name} ${level:,.0f}) · {dte} DTE (expires {expiry_str})',
            ]
        else:
            lines = [
                f'🛡️ SELL {side} — strike ~${approx_strike:,.0f}  (beyond {level_name} ${level:,.0f}, {STRUCT_BUFFER_ATR_MULT:.1f}×ATR ${buffer_:,.0f} further, live option data unavailable) · {dte} DTE (expires {expiry_str})',
            ]
        if overlay.get('reasons'):
            lines.append(f'   downgraded from near-spot: {"; ".join(overlay["reasons"])}')
        return lines

    # None: ambiguous ADX 25-40 band, a demoted 'near' with no HVN, or no HVN at all
    level_name = 'support' if is_put else 'resistance'
    if level is None:
        return [f'⏸️ SELL {side} — no {level_name} HVN found nearby to sell against']

    buffer_ = STRUCT_BUFFER_ATR_MULT * atr
    approx_strike = round(level - buffer_, -2) if is_put else round(level + buffer_, -2)
    mark, contract = overlay.get('mark'), overlay.get('contract')
    if mark and contract:
        strike = float(contract['strikePrice'])
        lines = [
            f'⏸️ SELL {side} — no confirmed signal (not recommended to sell), for reference: strike ${strike:,.0f}  '
            f'(Δ{mark["delta"]:.2f}, premium ${mark["markPrice"]:,.0f}, IV {mark["markIV"]*100:.0f}%, beyond {level_name} ${level:,.0f})',
        ]
    else:
        lines = [f'⏸️ SELL {side} — no confirmed signal (not recommended to sell), but nearest {level_name} is ${level:,.0f} ({STRUCT_BUFFER_ATR_MULT:.1f}×ATR ${buffer_:,.0f} away, live option data unavailable) → ~${approx_strike:,.0f}']
    if overlay.get('reasons'):
        lines.append(f'   also flagged: {"; ".join(overlay["reasons"])}')
    return lines


def build_message(ind: dict, vp: dict, verdict: dict, now: datetime,
                   funding_rate, atm_iv, rv: float, put_overlay: dict, call_overlay: dict) -> str:
    price, atr = ind['close'], ind['atr_14']
    date_str = now.strftime('%b %-d, %Y')
    expiry_dt, dte = next_expiry(now)
    expiry_str = expiry_dt.strftime('%b %-d, %Y 08:00 UTC')

    def _fmt_level(p):
        return f'${p:,.0f}' if p is not None else 'none nearby'

    def _signed_dist(p):
        return f' ({(p - price) / price * 100:+.2f}%)' if p is not None else ''

    # Trend
    strong_suffix = ' (strong)' if verdict['strong'] else ''
    if verdict['trend_label'] == 'sideways':
        trend_cond = f'ADX < {ADX_SIDEWAYS_MAX}'
    elif verdict['trend_label'] == 'uptrend':
        trend_cond = f'ADX >= {ADX_SIDEWAYS_MAX} & +DI>-DI'
    else:
        trend_cond = f'ADX >= {ADX_SIDEWAYS_MAX} & -DI>+DI'
    trend_line = (f"Trend     : {verdict['trend_label']}{strong_suffix} - {ind['adx']:.1f} ADX "
                  f"— (+DI {ind['di_pos']:.1f} / -DI {ind['di_neg']:.1f}) ({trend_cond})")

    # EMA — second, independent trend confirmation
    ema_label = 'uptrend' if verdict['price_above_ema'] else 'downtrend'
    ema_rel   = '>' if verdict['price_above_ema'] else '<'
    ema_line  = f"EMA       : {ema_label} - price ${price:,.0f} {ema_rel} EMA200 ${ind['ema_200']:,.0f} (price {ema_rel} EMA200)"

    # StochRSI (context only, does not gate any setup)
    k = ind['stochrsi_k']
    if verdict['stoch_zone'] == 'oversold':
        stoch_cond = f'%K < {STOCH_OVERSOLD}'
    elif verdict['stoch_zone'] == 'overbought':
        stoch_cond = f'%K > {STOCH_OVERBOUGHT}'
    else:
        stoch_cond = f'{STOCH_OVERSOLD} <= %K <= {STOCH_OVERBOUGHT}'
    stoch_line = f"StochRSI  : {verdict['stoch_zone']} - %K {k:.1f} / %D {ind['stochrsi_d']:.1f} ({stoch_cond})"

    # Funding
    if funding_rate is None:
        funding_line = 'Funding   : unavailable'
    else:
        annualized = funding_rate * 3 * 365 * 100
        thr = FUNDING_EXTREME * 100
        if funding_rate > FUNDING_EXTREME:
            f_label, f_cond = 'crowded long', f'funding > {thr:.2f}%/8h'
        elif funding_rate < -FUNDING_EXTREME:
            f_label, f_cond = 'crowded short', f'funding < -{thr:.2f}%/8h'
        else:
            f_label, f_cond = 'neutral', f'|funding| < {thr:.2f}%/8h'
        funding_line = (f'Funding   : {f_label} - {funding_rate*100:.4f}%/8h '
                        f'(~{annualized:.1f}%/yr) ({f_cond})')

    # Implied Vol (ATM reference) vs realized vol
    if atm_iv is not None and rv:
        iv_ratio = atm_iv / rv
        if iv_ratio < IV_RV_LOW:
            iv_label = 'cheap'
        elif iv_ratio > IV_RV_HIGH:
            iv_label = 'rich/event-risk'
        else:
            iv_label = 'healthy'
        iv_line = (f'Implied Vol: {iv_label} - IV {atm_iv*100:.0f}% vs RV {rv*100:.0f}% '
                   f'→ {iv_ratio:.2f}x ({IV_RV_LOW}-{IV_RV_HIGH} = healthy)')
    else:
        iv_line = 'Implied Vol: unavailable'

    lines = [
        f'📅 Sell Option Signal — {date_str}',
        f'💲 BTC/USDT — ${price:,.2f}',
        '',
        trend_line,
        ema_line,
        stoch_line,
        funding_line,
        iv_line,
        f"Support   : {_fmt_level(vp['support'])}{_signed_dist(vp['support'])}",
        f"Resistance: {_fmt_level(vp['resistance'])}{_signed_dist(vp['resistance'])}",
        '',
    ]

    put_state, call_state = put_overlay['state'], call_overlay['state']
    lines += _plan_line('PUT', put_state, price, atr, vp['support'], ind['adx'],
                        True, dte, expiry_str, put_overlay)
    lines.append('')
    lines += _plan_line('CALL', call_state, price, atr, vp['resistance'], ind['adx'],
                        False, dte, expiry_str, call_overlay)

    if put_state in ('near', 'structure') or call_state in ('near', 'structure'):
        lines += ['', f'   {entry_timing_note(now)}']

    return '\n'.join(lines)


# ── main ─────────────────────────────────────────────────────────────────────

def run_once(exchange):
    now = datetime.now(timezone.utc)
    errors = 0
    err_msg = ''
    try:
        df = fetch_4h_candles(exchange)
        ind = compute_indicators(df)
        vp  = compute_vpvr(df, ind['close'])
        verdict = evaluate(ind, vp)

        rv = compute_realized_vol(df)
        funding_rate = fetch_funding_rate(exchange)
        expiry_dt, _ = next_expiry(now)
        try:
            symbols = fetch_target_expiry_symbols(exchange, expiry_dt)
        except Exception:
            symbols = []
        atm_iv = fetch_atm_iv(exchange, symbols, ind['close'])

        put_overlay  = apply_overlay(exchange, True,  verdict['put_state'],  vp['support'],    symbols,
                                      funding_rate, rv, ind['atr_14'], ind['close'])
        call_overlay = apply_overlay(exchange, False, verdict['call_state'], vp['resistance'], symbols,
                                      funding_rate, rv, ind['atr_14'], ind['close'])

        message = build_message(ind, vp, verdict, now, funding_rate, atm_iv, rv, put_overlay, call_overlay)

        url = os.getenv('SELL_OPTION_SIGNAL_WEBHOOK_URL')
        if url:
            r = requests.post(url, json={'content': message}, timeout=10)
            if r.status_code not in (200, 204):
                raise RuntimeError(f'Discord HTTP {r.status_code}: {r.text[:200]}')
        print(message)
    except Exception as e:
        errors = 1
        err_msg = str(e)
        print(f'[main] ERROR: {e}')
        raise
    finally:
        log_url = os.getenv('DISCORD_LOG_URL')
        if log_url:
            date_str = now.strftime('%b %-d, %Y')
            content = f'📅 Sell Option Signal — {date_str} — {errors} error(s)'
            if err_msg:
                content += f'\n{err_msg}'
            requests.post(log_url, json={'content': content}, timeout=10)


if __name__ == '__main__':
    exchange = make_exchange()
    run_once(exchange)
