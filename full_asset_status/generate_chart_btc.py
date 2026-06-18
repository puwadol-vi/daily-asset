from PIL import Image, ImageDraw
from datetime import datetime, timezone

GRID_W, GRID_H = 200, 105
SCALE = 6  # → 1200 × 630

C_BG          = (13,  13,  13)
C_UP          = (247, 147, 26)   # bitcoin orange (all candles)
C_UP_WICK     = (184, 108, 16)   # darker orange (all wicks)
C_EMA200      = (99,  102, 241)  # indigo
C_EMA12       = (34,  197, 94)   # green
C_EMA26       = (239, 68,  68)   # red
C_ZONE_BULL   = (16,  39,  24)   # dark green fill
C_ZONE_BEAR   = (45,  21,  21)   # dark red fill
C_SPOT_UP     = (34,  197, 94)   # green dot above up candle
C_SPOT_DOWN   = (239, 68,  68)   # red dot below down candle
C_PRICE_LABEL = (74,  74,  90)
C_MONTH_LABEL = (58,  58,  74)
C_TICK        = (34,  34,  34)
C_MONTH_TICK  = (41,  41,  51)

MARGIN_TOP    = 8
MARGIN_LEFT   = 4
MARGIN_RIGHT  = 20   # room for price labels ("100K" = 15px + padding)
MARGIN_BOTTOM = 13   # room for month labels (tick + gap + 5px font)
N_CANDLES     = 58
BODY_W        = 2
SLOT_W        = 3    # 2px body + 1px gap
PRICE_STEP    = 4000

MONTH_NAMES = ['JAN','FEB','MAR','APR','MAY','JUN',
               'JUL','AUG','SEP','OCT','NOV','DEC']

# 3×5 bitmap font — bit 2=left col, bit 1=mid col, bit 0=right col
FONT_3X5 = {
    '0': [0b010, 0b101, 0b101, 0b101, 0b010],
    '1': [0b110, 0b010, 0b010, 0b010, 0b111],
    '2': [0b110, 0b001, 0b010, 0b100, 0b111],
    '3': [0b110, 0b001, 0b110, 0b001, 0b110],
    '4': [0b101, 0b101, 0b111, 0b001, 0b001],
    '5': [0b111, 0b100, 0b110, 0b001, 0b110],
    '6': [0b011, 0b100, 0b110, 0b101, 0b011],
    '7': [0b111, 0b001, 0b010, 0b010, 0b010],
    '8': [0b111, 0b101, 0b111, 0b101, 0b111],
    '9': [0b111, 0b101, 0b111, 0b001, 0b110],
    '@': [0b011, 0b101, 0b111, 0b100, 0b011],
    'A': [0b010, 0b101, 0b111, 0b101, 0b101],
    'B': [0b110, 0b101, 0b110, 0b101, 0b110],
    'C': [0b011, 0b100, 0b100, 0b100, 0b011],
    'D': [0b110, 0b101, 0b101, 0b101, 0b110],
    'E': [0b111, 0b100, 0b110, 0b100, 0b111],
    'F': [0b111, 0b100, 0b110, 0b100, 0b100],
    'G': [0b011, 0b100, 0b101, 0b101, 0b011],
    'J': [0b011, 0b001, 0b001, 0b101, 0b010],
    'K': [0b101, 0b101, 0b110, 0b101, 0b101],
    'L': [0b100, 0b100, 0b100, 0b100, 0b111],
    'M': [0b101, 0b111, 0b101, 0b101, 0b101],
    'N': [0b101, 0b111, 0b111, 0b101, 0b101],
    'O': [0b010, 0b101, 0b101, 0b101, 0b010],
    'P': [0b110, 0b101, 0b110, 0b100, 0b100],
    'R': [0b110, 0b101, 0b110, 0b101, 0b101],
    'S': [0b011, 0b100, 0b010, 0b001, 0b110],
    'T': [0b111, 0b010, 0b010, 0b010, 0b010],
    'U': [0b101, 0b101, 0b101, 0b101, 0b010],
    'V': [0b101, 0b101, 0b101, 0b010, 0b010],
    'Y': [0b101, 0b101, 0b010, 0b010, 0b010],
}


def _px_text_width(text: str) -> int:
    # each char: 3px wide + 1px gap; last char has no trailing gap
    return max(0, len(text) * 4 - 1)


def _draw_px_text(draw: ImageDraw.Draw, x: int, y: int,
                  text: str, color: tuple, align: str = 'left') -> None:
    text = text.upper()
    w  = _px_text_width(text)
    cx = (x - w)          if align == 'right'  else \
         (x - w // 2)     if align == 'center' else x
    for ch in text:
        glyph = FONT_3X5.get(ch)
        if glyph is None:
            cx += 4
            continue
        for row, bits in enumerate(glyph):
            for col in range(3):
                if bits & (4 >> col):
                    draw.point((cx + col, y + row), fill=color)
        cx += 4


def generate(data: dict, output_path: str = '/tmp/btc_chart.png') -> str:
    ohlcv  = data['ohlcv_last_60']   # list of {open,high,low,close,ts}  ts = ms epoch
    ema200 = data['ema200_series']    # 60 floats
    ema12  = data['ema12_series']     # 60 floats
    ema26  = data['ema26_series']     # 60 floats

    img  = Image.new('RGB', (GRID_W, GRID_H), C_BG)
    draw = ImageDraw.Draw(img)

    # ── 0. asset + date label (top-left, inside top margin) ─────────────────
    last_ts  = ohlcv[-1].get('ts', 0)
    last_dt  = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
    lbl_text = 'BTC ' + last_dt.strftime('%d%b%Y').upper()
    _draw_px_text(draw, MARGIN_LEFT + 1, 1, lbl_text, C_PRICE_LABEL, align='left')

    cx = MARGIN_LEFT
    cy = MARGIN_TOP
    cw = GRID_W - MARGIN_LEFT - MARGIN_RIGHT   # 176
    ch = GRID_H - MARGIN_TOP  - MARGIN_BOTTOM  # 84

    # price scale — include all EMA series so chart never clips
    all_prices = (
        [c['high'] for c in ohlcv] +
        [c['low']  for c in ohlcv] +
        [v for v in ema200 + ema12 + ema26 if v is not None]
    )
    pmax = max(all_prices) * 1.006
    pmin = min(all_prices) * 0.994
    pr   = pmax - pmin

    def to_y(price: float) -> int:
        return int(cy + (pmax - price) / pr * ch)

    # candle block — 58 slots × 3px = 174px, centered in 176px chart width
    total_w = N_CANDLES * SLOT_W          # 174
    start_x = cx + (cw - total_w) // 2   # 5

    # ── 1. action zone fill (between EMA12 and EMA26) ──────────────────────
    for i, (v12, v26) in enumerate(zip(ema12[-N_CANDLES:], ema26[-N_CANDLES:])):
        if v12 is None or v26 is None:
            continue
        x     = start_x + i * SLOT_W
        y_top = min(to_y(v12), to_y(v26))
        y_bot = max(to_y(v12), to_y(v26))
        fill  = C_ZONE_BULL if v12 > v26 else C_ZONE_BEAR
        for y in range(y_top, y_bot + 1):
            draw.line([(x, y), (x + BODY_W - 1, y)], fill=fill)

    # ── 2. candles (all bitcoin orange) ─────────────────────────────────────
    for i, c in enumerate(ohlcv[-N_CANDLES:]):
        x     = start_x + i * SLOT_W
        is_up = c['close'] >= c['open']

        y_high = to_y(c['high'])
        y_low  = to_y(c['low'])
        y_top  = to_y(max(c['open'], c['close']))
        y_bot  = max(to_y(min(c['open'], c['close'])), y_top + 1)

        draw.line([(x, y_high), (x, y_low)], fill=C_UP_WICK)
        draw.rectangle([x, y_top, x + BODY_W - 1, y_bot], fill=C_UP)

    # ── 2.5. action zone cross marker — one 2×2 dot at the most recent cross ─
    disp_e12 = ema12[-N_CANDLES:]
    disp_e26 = ema26[-N_CANDLES:]
    cross_i  = None
    cross_bull = None
    for j in range(1, N_CANDLES):
        e12p, e26p = disp_e12[j - 1], disp_e26[j - 1]
        e12c, e26c = disp_e12[j],     disp_e26[j]
        if None in (e12p, e26p, e12c, e26c):
            continue
        if (e12c > e26c) != (e12p > e26p):
            cross_i    = j
            cross_bull = e12c > e26c

    if cross_i is not None:
        c_cross = ohlcv[-N_CANDLES:][cross_i]
        x_dot   = start_x + cross_i * SLOT_W
        if cross_bull:
            y_dot = to_y(c_cross['high']) - 3
            color = C_SPOT_UP
        else:
            y_dot = to_y(c_cross['low']) + 2
            color = C_SPOT_DOWN
        if cy <= y_dot <= cy + ch:
            draw.rectangle([x_dot, y_dot, x_dot + 1, y_dot + 1], fill=color)

    # ── 3. EMA 200 — indigo dot, every 2nd slot ─────────────────────────────
    for i, v in enumerate(ema200[-N_CANDLES:]):
        if v is None or i % 2 != 0:
            continue
        y = to_y(v)
        if cy <= y <= cy + ch:
            draw.point((start_x + i * SLOT_W + 1, y), fill=C_EMA200)

    # ── 4. EMA 12 — amber dot, col 0 of each slot ───────────────────────────
    for i, v in enumerate(ema12[-N_CANDLES:]):
        if v is None:
            continue
        y = to_y(v)
        if cy <= y <= cy + ch:
            draw.point((start_x + i * SLOT_W, y), fill=C_EMA12)

    # ── 5. EMA 26 — sky blue dot, col 1 of each slot ────────────────────────
    for i, v in enumerate(ema26[-N_CANDLES:]):
        if v is None:
            continue
        y = to_y(v)
        if cy <= y <= cy + ch:
            draw.point((start_x + i * SLOT_W + 1, y), fill=C_EMA26)

    # ── 6. price labels — right side, every 2000 USD ────────────────────────
    chart_right = cx + cw
    p_start     = int((pmin // PRICE_STEP + 1) * PRICE_STEP)
    last_label_y = -99

    for p in range(p_start, int(pmax) + 1, PRICE_STEP):
        y = to_y(p)
        if y < cy + 2 or y > cy + ch - 1:
            continue
        if abs(y - last_label_y) < 7:
            continue
        draw.line([(chart_right, y), (chart_right + 2, y)], fill=C_TICK)
        label = f'{round(p / 1000)}K'
        _draw_px_text(draw, GRID_W - 2, y - 2, label, C_PRICE_LABEL, align='right')
        last_label_y = y

    # ── 7. month labels — first candle of each month only ───────────────────
    edge_min = start_x + 8
    edge_max = start_x + total_w - 8

    for i, c in enumerate(ohlcv[-N_CANDLES:]):
        ts = c.get('ts')
        if ts is None:
            continue
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        if dt.day != 1:
            continue
        x = start_x + i * SLOT_W + 1
        if x < edge_min or x > edge_max:
            continue
        draw.line([(x, cy + ch + 1), (x, cy + ch + 3)], fill=C_MONTH_TICK)
        _draw_px_text(draw, x, cy + ch + 5,
                      MONTH_NAMES[dt.month - 1], C_MONTH_LABEL, align='center')

    out = img.resize((GRID_W * SCALE, GRID_H * SCALE), Image.NEAREST)
    out.save(output_path)
    return output_path
