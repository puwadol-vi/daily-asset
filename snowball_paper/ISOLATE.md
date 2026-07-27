# Binance Isolated USD-M Futures — reference

What isolated margin actually is, what actions you can take on an isolated position, how each
is calculated, and how every column in `calc.csv` maps back to these real exchange concepts
(some don't map 1:1 — flagged explicitly where this project's accounting diverges from what
Binance's own UI would show).

---

## 1. Core concepts

- **USD-M Futures**: perpetual/futures contracts margined in a stablecoin (USDT/USDC), as
  opposed to COIN-M (margined in the coin itself). `LEVERAGE`/sizing throughout this project
  assumes USD-M.
- **Isolated margin mode**: the margin backing a position on one symbol (e.g. BTCUSDT) is
  walled off from every other symbol and from your Cross wallet. A liquidation on BTCUSDT
  cannot touch your ETHUSDT position or your spot balance — only the isolated margin you've
  allocated to that specific symbol is at risk.
- **Isolated Margin** (a real dollar balance, per symbol): the cash actually deposited/retained
  as collateral for that position. Changes only via explicit actions (§2) — never
  auto-recalculated from price.
- **Position Amount / position_size**: how many coins the position holds (e.g. 0.53 BTC).
  Changes only via explicit actions — buying more (adds) or selling some/all (reduces).
- **Mark Price**: the reference price used for PnL/liquidation calculations (not always
  identical to the last traded price — Binance uses a mark price to resist manipulation; this
  project simplifies by using the daily close).
- **Unrealized PnL**: `(mark_price − avg_entry_price) × position_size` for a long. Floats with
  price, not yet real money until the position (or part of it) closes.
- **Margin Balance**: `isolated_margin + unrealized_PnL` — your true current equity on that
  position if you had to value it right now.
- **Maintenance Margin (MMR)**: the minimum margin balance required to keep the position open.
  Real Binance MMR is **tiered by notional size** (bigger positions require a higher %,
  published in Binance's own tier tables); this project uses a flat placeholder (`MMR = 0.5%`)
  — a simplification, see Open Items in `BACKTEST_PLAN_V2.md`.
- **Liquidation Price**: the mark price at which margin balance would exactly equal the
  maintenance margin requirement — cross it, and the exchange force-closes the position.

---

## 2. Actions on an isolated position, and how each is calculated

| Action | What changes | Formula |
|---|---|---|
| **Open** | Deposit initial margin, choose leverage, position opens | `position_size = (margin × leverage) / entry_price`; `notional = position_size × entry_price` |
| **Add margin** (deposit more) | `isolated_margin` increases; `position_size` untouched | Leverage falls (`notional / new_margin`); liquidation price moves *further* away |
| **Remove margin** (withdraw) | `isolated_margin` decreases; `position_size` untouched | Leverage rises; liquidation price moves *closer* — this is the real mechanic behind this project's Secure Profit (§4) |
| **Increase position** (add to it) | `position_size` grows; `avg_entry_price` becomes the size-weighted average of old and new fills | `new_avg_entry = (old_size×old_avg + added_size×fill_price) / (old_size+added_size)` |
| **Reduce position** (partial close) | `position_size` shrinks; the closed portion's PnL is realized at the fill price; `avg_entry_price` on the *remaining* size is unchanged | `realized = (fill_price − avg_entry_price) × size_closed` |
| **Close position** (full) | `position_size → 0`; entire remaining PnL realized | `realized = (fill_price − avg_entry_price) × position_size` |
| **Liquidation** (forced, not user-initiated) | Exchange force-closes at/near the liquidation price when margin balance breaches MMR | Same as a full close, but `fill_price = liquidation_price`, and most/all of `isolated_margin` is typically lost |

**Reference formulas**:

```
notional              = position_size × mark_price
leverage (real-time)  = notional / margin_balance
margin_balance         = isolated_margin + (mark_price − avg_entry_price) × position_size
liquidation_price      = (avg_entry_price × position_size − isolated_margin)
                          / (position_size × (1 − MMR))          [long, ignoring funding]
```

The critical thing "Add margin" / "Remove margin" makes possible, that a lot of people miss:
**you can pull profit out of a position without selling any of the underlying coins.**
Position size and margin are independent knobs — that's what §4 below relies on.

---

## 3. `calc.csv` column reference

| Column | Binance-native equivalent | This project's formula | Notes |
|---|---|---|---|
| `avg_entry_price` | Position tab → Entry Price | size-weighted average of open layers' entry prices | Only changes on an add (scale-in); untouched by a margin withdrawal |
| `position_size` | Position tab → Position Amount | sum of open layers' size | **Only** changes via scale-in or a full close — never via Secure Profit |
| `liquidate_price` | Position tab → Liq. Price | `(avg_entry×size − margin) / (size×(1−MMR))` | Fixed until size/margin/avg-entry actually change (never recomputed off today's price) |
| `notional` | Position tab → Position Value / Cost | `position_size × price` | |
| `leverage` | *Not the static leverage you selected* — this is the real-time margin-balance-based ratio | `notional / (margin + unrealized_raw)` | Falls as the position gains, rises as it loses — the opposite of a naive notional/fixed-margin ratio |
| `position` | Position tab → Isolated Margin | `isolated_margin` | Grows via Secure Profit top-ups (§4), grows via new layers, drops to 0 on a close |
| `unrealized` | **Not the same as Binance's own Unrealized PnL field** | `(price − checkpoint_price) × position_size` | Binance's own field is always relative to `avg_entry_price`; this project measures from the *last Secure Profit event* instead, specifically so already-withdrawn profit is never double-counted. See §4. |
| `available_for_scaling` | No native equivalent | running pool, +50% of each withdrawal, drawn to zero by the next scale-in | Real, already-withdrawn cash (see §4) held aside for the next layer, not still-at-risk unrealized value |
| `secure_profit_trim` | Closest native analog: a "Reduce Margin" transaction log entry | the $ amount withdrawn *that specific day* | Blank on days nothing was withdrawn |
| `secured_profit_total` | No single native field — reconstructable from your margin-withdrawal + realized-PnL history | cumulative sum of every withdrawal + every full-close settlement | The permanent ledger — a later loss on the open position can never reduce this |
| `profit` | No native equivalent | `unrealized + available_for_scaling` | Deliberately excludes `secured_profit_total` — this is only the *not-yet-permanently-banked* value |
| `total` | No native equivalent (closest: Wallet Balance + all open positions' Margin Balance, if you tracked nothing else) | `position + profit + secured_profit_total` | The complete, honest account value for this cycle at that moment |
| `today_change` | No native equivalent | `total[n] − total[n−1]` | Day-over-day change in the complete account value, not just mark-to-market PnL |
| `action` | Order History / Position History / Margin Adjustment History, combined into one log line | free text | Entry, scale-in, Secure Profit withdrawal, whole-system exit, or liquidation |

---

## 4. How Secure Profit maps to real actions (§2 applied)

Every Secure Profit event in `calc.csv` is, mechanically, a **Remove Margin** action, computed
as: top `isolated_margin` up to `required_margin = (position_size × price) / LEVERAGE` first
(what a fresh position of this size would need at today's price), then withdraw everything
above that floor, split 50/50 into `secured_profit_total` (moved out permanently — modeling an
actual transfer to spot/another wallet) and `available_for_scaling` (withdrawn too, but held
aside specifically to fund the next scale-in's **Increase position** action). `position_size`
never appears on either side of this — consistent with §2's "Remove margin" row.

A whole-system exit or liquidation is a **Close position** action per §2 — the only two places
in this project where `position_size` actually drops to zero.

_Not financial advice._
