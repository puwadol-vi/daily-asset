import sys
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from generate_chart_btc import _px_text_width, _draw_px_text, MONTH_NAMES, S

GRID_W, GRID_H = 400, 200
SCALE = 3  # → 1200 × 600

C_BG          = (13,  13,  13)
C_CLOSE       = (247, 147, 26)   # orange  #F7931A
C_CLOSE_WICK  = (184, 108, 16)   # dark orange (wick)
C_REALIZED    = (99,  102, 241)  # blue    #6366f1
C_STH         = (239, 68,  68)   # red     #ef4444
C_LTH         = (34,  197, 94)   # green   #22c55e
C_TMM         = (160, 160, 176)  # lt gray #a0a0b0
C_PRICE_LABEL = (74,  74,  90)
C_MONTH_LABEL = (58,  58,  74)
C_TICK        = (34,  34,  34)
C_MONTH_TICK  = (41,  41,  51)

MARGIN_TOP    = 16
MARGIN_LEFT   = 8
MARGIN_RIGHT  = 32
MARGIN_BOTTOM = 26
N_POINTS      = 120
BODY_W        = 2
SLOT_W        = 3

ONCHAIN_LINES = [
    ('realized', C_REALIZED),
    ('sth',      C_STH),
    ('lth',      C_LTH),
    ('tmm',      C_TMM),
]

LEGEND = [
    ('TMM',  C_TMM),
    ('LTH',  C_LTH),
    ('STH',  C_STH),
    ('REAL', C_REALIZED),
]


def generate(history: list, output_path: str = '/tmp/btc_onchain.png') -> str:
    """Draw BTC candles + 4 onchain lines from price_history entries."""
    img  = Image.new('RGB', (GRID_W, GRID_H), C_BG)
    draw = ImageDraw.Draw(img)

    cx = MARGIN_LEFT
    cy = MARGIN_TOP
    cw = GRID_W - MARGIN_LEFT - MARGIN_RIGHT   # 360
    ch = GRID_H - MARGIN_TOP  - MARGIN_BOTTOM  # 158

    entries  = history[-N_POINTS:]
    n        = len(entries)
    total_w  = n * SLOT_W
    start_x  = cx + cw - total_w   # right-align: newest data on right

    # ── price scale ──────────────────────────────────────────────────────────
    all_vals = []
    for e in entries:
        for k in ('high', 'low', 'close', 'realized', 'sth', 'lth', 'tmm'):
            v = e.get(k)
            if v is not None:
                all_vals.append(v)

    if not all_vals:
        img.resize((GRID_W * SCALE, GRID_H * SCALE), Image.NEAREST).save(output_path)
        return output_path

    pmax = max(all_vals) * 1.01
    pmin = min(all_vals) * 0.99
    pr   = pmax - pmin

    price_range = pmax - pmin
    if price_range < 10_000:    PRICE_STEP = 2_000
    elif price_range < 25_000:  PRICE_STEP = 5_000
    elif price_range < 50_000:  PRICE_STEP = 10_000
    else:                       PRICE_STEP = 20_000

    def to_y(price: float) -> int:
        return int(cy + (pmax - price) / pr * ch)

    # ── 0. header ────────────────────────────────────────────────────────────
    last_date = entries[-1].get('date', '') if entries else ''
    try:
        lbl_dt   = datetime.strptime(last_date, '%Y-%m-%d')
        lbl_text = 'BTC ONCHAIN ' + lbl_dt.strftime('%d%b%Y').upper()
    except Exception:
        lbl_text = 'BTC ONCHAIN'
    _draw_px_text(draw, cx + 1, 2, lbl_text, C_PRICE_LABEL, align='left')

    # ── 1. BTC candles ───────────────────────────────────────────────────────
    for i, entry in enumerate(entries):
        cl = entry.get('close')
        if cl is None:
            continue
        op = entry.get('open') or cl
        hi = entry.get('high') or max(cl, op)
        lo = entry.get('low')  or min(cl, op)
        x      = start_x + i * SLOT_W
        y_high = max(cy, min(cy + ch, to_y(hi)))
        y_low  = max(cy, min(cy + ch, to_y(lo)))
        y_top  = max(cy, min(cy + ch, to_y(max(op, cl))))
        y_bot  = max(cy, min(cy + ch, to_y(min(op, cl))))
        y_bot  = max(y_bot, y_top + 1)  # min 1px body
        draw.line([(x, y_high), (x, y_low)], fill=C_CLOSE_WICK)
        draw.rectangle([x, y_top, x + BODY_W - 1, y_bot], fill=C_CLOSE)

    _FIELD_LABEL = {'realized': 'REAL', 'sth': 'STH', 'lth': 'LTH', 'tmm': 'TMM'}

    # ── 2. onchain dots (every 2nd slot, like EMA200) ────────────────────────
    for field, color in ONCHAIN_LINES:
        label     = _FIELD_LABEL[field]
        first_lbl = True
        for i, entry in enumerate(entries):
            v = entry.get(field)
            if v is None:
                continue
            x = start_x + i * SLOT_W + 1
            y = max(cy, min(cy + ch, to_y(v)))
            if first_lbl:
                _draw_px_text(draw, x, max(cy + 1, y - 5 * S - 2), label, color, align='left')
                first_lbl = False
            if i % 2 == 0:
                draw.point((x, y), fill=color)

    # ── 3. price labels ──────────────────────────────────────────────────────
    chart_right  = cx + cw
    p_start      = int((pmin // PRICE_STEP + 1) * PRICE_STEP)
    last_label_y = -99
    for p in range(p_start, int(pmax) + 1, PRICE_STEP):
        y = to_y(p)
        if y < cy + 2 or y > cy + ch - 1:
            continue
        if abs(y - last_label_y) < 5 * S + 2:
            continue
        draw.line([(chart_right, y), (chart_right + 2, y)], fill=C_TICK)
        _draw_px_text(draw, GRID_W - 2, y - 5,
                      f'{round(p / 1000)}K', C_PRICE_LABEL, align='right')
        last_label_y = y

    # ── 4. month labels ──────────────────────────────────────────────────────
    edge_min = start_x
    edge_max = start_x + total_w - SLOT_W
    for i, entry in enumerate(entries):
        d_str = entry.get('date', '')
        if not d_str:
            continue
        try:
            dt = datetime.strptime(d_str, '%Y-%m-%d')
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
