from PIL import Image, ImageDraw
from datetime import datetime, timezone

GRID_W, GRID_H = 400, 200
SCALE = 3  # → 1200 × 600

C_BG          = (13,  13,  13)
C_UP          = (247, 147, 26)
C_UP_WICK     = (184, 108, 16)
C_EMA200      = (99,  102, 241)  # indigo/blue
C_EMA12       = (34,  197, 94)   # green
C_EMA26       = (239, 68,  68)   # red
C_ZONE_BULL   = (16,  39,  24)
C_ZONE_BEAR   = (45,  21,  21)
C_SPOT_UP     = (34,  197, 94)
C_SPOT_DOWN   = (239, 68,  68)
C_PRICE_LABEL = (74,  74,  90)
C_MONTH_LABEL = (58,  58,  74)
C_TICK        = (34,  34,  34)
C_MONTH_TICK  = (41,  41,  51)

MARGIN_TOP    = 16
MARGIN_LEFT   = 8
MARGIN_RIGHT  = 32   # "100K" = 30px + 2px padding
MARGIN_BOTTOM = 26   # tick(2) + gap(2) + font(10) + pad(12)
N_CANDLES     = 120
BODY_W        = 2
SLOT_W        = 3    # 2px body + 1px gap
PRICE_STEP    = 4000
S             = 2    # font scale: 3×5 → 6×10 per character

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
    'H': [0b101, 0b101, 0b111, 0b101, 0b101],
    'I': [0b111, 0b010, 0b010, 0b010, 0b111],
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
    # each char: 3S wide + S gap; last char has no trailing gap
    return max(0, len(text) * (3 * S + S) - S)


def _draw_px_text(draw: ImageDraw.Draw, x: int, y: int,
                  text: str, color: tuple, align: str = 'left') -> None:
    text = text.upper()
    w  = _px_text_width(text)
    cx = (x - w)          if align == 'right'  else \
         (x - w // 2)     if align == 'center' else x
    for ch in text:
        glyph = FONT_3X5.get(ch)
        if glyph is None:
            cx += (3 + 1) * S
            continue
        for row, bits in enumerate(glyph):
            for col in range(3):
                if bits & (4 >> col):
                    draw.rectangle(
                        [cx + col * S,       y + row * S,
                         cx + col * S + S-1, y + row * S + S-1],
                        fill=color,
                    )
        cx += (3 + 1) * S


def generate(history: list, output_path: str = '/tmp/btc_chart.png') -> str:
    ohlcv  = history
    ema200 = [e.get('ema200') for e in history]
    ema12  = [e.get('ema12')  for e in history]
    ema26  = [e.get('ema26')  for e in history]

    img  = Image.new('RGB', (GRID_W, GRID_H), C_BG)
    draw = ImageDraw.Draw(img)

    cx = MARGIN_LEFT
    cy = MARGIN_TOP
    cw = GRID_W - MARGIN_LEFT - MARGIN_RIGHT   # 360
    ch = GRID_H - MARGIN_TOP  - MARGIN_BOTTOM  # 158

    # ── 0. header: date label (left) + EMA200 indicator (right) ─────────────
    last_date = history[-1].get('date', '') if history else ''
    try:
        last_dt  = datetime.strptime(last_date, '%b %d, %Y') if ',' in last_date \
                   else datetime.strptime(last_date, '%Y-%m-%d')
        lbl_text = 'BTC ' + last_dt.strftime('%d%b%Y').upper()
    except Exception:
        lbl_text = 'BTC'
    _draw_px_text(draw, cx + 1, 2, lbl_text, C_PRICE_LABEL, align='left')
    _draw_px_text(draw, cx + cw - 1, 2, 'EMA 200', C_EMA200, align='right')

    # price scale — exclude EMA200 values that are >5% outside candle range
    candle_high   = max(c.get('high') or c.get('close') or 0 for c in ohlcv[-N_CANDLES:])
    candle_low    = min(c.get('low')  or c.get('close') or 0 for c in ohlcv[-N_CANDLES:])
    ema200_hi_cut = candle_high * 1.05
    ema200_lo_cut = candle_low  * 0.95

    all_prices = (
        [c.get('high') or c.get('close') for c in ohlcv if c.get('high') or c.get('close')] +
        [c.get('low')  or c.get('close') for c in ohlcv if c.get('low')  or c.get('close')] +
        [v for v in ema200[-N_CANDLES:] if v is not None and ema200_lo_cut <= v <= ema200_hi_cut] +
        [v for v in ema12 + ema26 if v is not None]
    )
    pmax = max(all_prices) * 1.006
    pmin = min(all_prices) * 0.994
    pr   = pmax - pmin

    def to_y(price: float) -> int:
        return int(cy + (pmax - price) / pr * ch)

    total_w = N_CANDLES * SLOT_W          # 360
    start_x = cx + (cw - total_w) // 2   # 8

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

    # ── 2. candles ───────────────────────────────────────────────────────────
    for i, c in enumerate(ohlcv[-N_CANDLES:]):
        op = c.get('open')  or c.get('close') or 0
        cl = c.get('close') or op
        hi = c.get('high')  or max(op, cl)
        lo = c.get('low')   or min(op, cl)
        x      = start_x + i * SLOT_W
        y_high = to_y(hi)
        y_low  = to_y(lo)
        y_top  = to_y(max(op, cl))
        y_bot  = max(to_y(min(op, cl)), y_top + 1)
        draw.line([(x, y_high), (x, y_low)], fill=C_UP_WICK)
        draw.rectangle([x, y_top, x + BODY_W - 1, y_bot], fill=C_UP)

    # ── 2.5. action zone cross markers — 2×2 dot at every EMA12/26 cross ────
    disp_e12 = ema12[-N_CANDLES:]
    disp_e26 = ema26[-N_CANDLES:]

    for j in range(1, N_CANDLES):
        e12p, e26p = disp_e12[j - 1], disp_e26[j - 1]
        e12c, e26c = disp_e12[j],     disp_e26[j]
        if None in (e12p, e26p, e12c, e26c):
            continue
        if (e12c > e26c) == (e12p > e26p):
            continue
        is_bull = e12c > e26c
        c_cross = ohlcv[-N_CANDLES:][j]
        x_dot   = start_x + j * SLOT_W
        hi_cross = c_cross.get('high') or c_cross.get('close') or 0
        lo_cross = c_cross.get('low')  or c_cross.get('close') or 0
        if is_bull:
            y_dot = to_y(hi_cross) - 3
            color = C_SPOT_UP
        else:
            y_dot = to_y(lo_cross) + 2
            color = C_SPOT_DOWN
        if cy <= y_dot <= cy + ch:
            draw.rectangle([x_dot, y_dot, x_dot + 1, y_dot + 1], fill=color)

    # ── 3. EMA 200 — indigo dot, every 2nd slot (hidden if >5% outside range)
    for i, v in enumerate(ema200[-N_CANDLES:]):
        if v is None or i % 2 != 0:
            continue
        if v > ema200_hi_cut or v < ema200_lo_cut:
            continue
        y = to_y(v)
        if cy <= y <= cy + ch:
            draw.point((start_x + i * SLOT_W + 1, y), fill=C_EMA200)

    # ── 4. EMA 12 ───────────────────────────────────────────────────────────
    for i, v in enumerate(ema12[-N_CANDLES:]):
        if v is None:
            continue
        y = to_y(v)
        if cy <= y <= cy + ch:
            draw.point((start_x + i * SLOT_W, y), fill=C_EMA12)

    # ── 5. EMA 26 ───────────────────────────────────────────────────────────
    for i, v in enumerate(ema26[-N_CANDLES:]):
        if v is None:
            continue
        y = to_y(v)
        if cy <= y <= cy + ch:
            draw.point((start_x + i * SLOT_W + 1, y), fill=C_EMA26)

    # ── 6. price labels ──────────────────────────────────────────────────────
    chart_right  = cx + cw
    p_start      = int((pmin // PRICE_STEP + 1) * PRICE_STEP)
    last_label_y = -99

    for p in range(p_start, int(pmax) + 1, PRICE_STEP):
        y = to_y(p)
        if y < cy + 2 or y > cy + ch - 1:
            continue
        if abs(y - last_label_y) < 5 * S + 2:  # min spacing = font height + gap
            continue
        draw.line([(chart_right, y), (chart_right + 2, y)], fill=C_TICK)
        label = f'{round(p / 1000)}K'
        _draw_px_text(draw, GRID_W - 2, y - 5, label, C_PRICE_LABEL, align='right')
        last_label_y = y

    # ── 7. month labels ──────────────────────────────────────────────────────
    edge_min = start_x + 11
    edge_max = start_x + total_w - 11

    for i, c in enumerate(ohlcv[-N_CANDLES:]):
        d_str = c.get('date', '')
        if not d_str:
            continue
        try:
            dt = datetime.strptime(d_str, '%Y-%m-%d') if '-' in d_str \
                 else datetime.strptime(d_str, '%b %d, %Y')
        except Exception:
            continue
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
