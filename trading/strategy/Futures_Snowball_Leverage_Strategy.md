# Futures Snowball Leverage Strategy

---

## Overview

One isolated long position on Binance USD-M Futures. Start at 3× leverage. Each time the market confirms a new HH + HL structure, add contracts **at the new HL** and increase leverage — snowballing into 5×, then 10×. Profits are extracted at each confirmation: 40% permanently to spot BTC, the rest recycles as re-entry capital.

The stop is a **stop-loss order** placed at 5% below the structural HL — not the liquidation price. Because entries and adds always happen **at the HL**, the liquidation price sits naturally 10–33% below HL, well below the 5% stop. The stop always fires before liquidation at any leverage ≤ 10×.

---

## The 3 Capital Groups

| Group | Source | Purpose | Can return to trade? |
|---|---|---|---|
| **In Position** | Deployed from Hold USD | Active futures margin | Yes — via re-entry |
| **Outside Strategy** | Profit only | Spot BTC, held permanently | No — never |
| **Hold USD** | Monthly DCA + profit share | Entry and re-entry pool | Yes — this is the deployment pool |

### Capital flow

```
Monthly DCA ──────────────────────────────────────► Hold USD
                                                         │
                                     Entry / Re-entry    │
                                          ┌──────────────┘
                                          ▼
                                    In Position
                                  (isolated futures)
                                          │
                             HH+HL fires — profit realized
                                    ┌─────┴──────┐
                                    ▼             ▼
                             40% Outside      60% available:
                             Strategy       ┌── add contracts (snowball)
                            (spot BTC,      └── remainder → Hold USD
                            permanent)
```

---

## Entry Conditions — ALL FOUR must be true

| Condition | How to check |
|---|---|
| Price above EMA 200 | Daily chart — `ta.ema(close,200).iloc[-1]` |
| ADX (14) above 20 | Daily ADX line — `ta.adx(H,L,C,14)['ADX_14'].iloc[-1]` |
| Action Zone 🟢 — EMA 12 above EMA 26 | Last EMA cross is bullish |
| BOS intact — HH/HL structure, no LH forming | Last 3 swing highs each higher |

If any fails → Hold USD stays idle. Wait.

---

## First Entry — 3×

**Where to enter:** At the most recent confirmed HL (buy structural support, not the breakout high).

**Why at HL:** With 3× leverage, liq sits 33% below HL. Stop is only 5% below HL. Stop always fires first. ✓

### Sizing — calculated backwards

Decide the maximum dollar loss you accept if the stop fires on this entry.

```
Margin to deploy = Acceptable_loss_$ ÷ (5% × 3)
                 = Acceptable_loss_$ ÷ 0.15
```

Example: willing to lose $300 → deploy $300 ÷ 0.15 = **$2,000 margin at 3×**

Source: Hold USD.

### Stop-loss order

Place a stop-loss market order at: **HL × 0.95** (5% below entry HL).

| Leverage | Distance to stop | Margin loss if stop hits |
|---|---|---|
| 3× | 5% | **15%** |

---

## Snowball — HH+HL Action Sequence

### When to act

Wait for price to:
1. Make a new confirmed swing high (HH) — higher than all recent swing highs
2. Pull back and form a new confirmed swing low (HL) — higher than the previous HL

**Only act after the HL has formed and stabilized.** Do not act at the HH. Entry is always at the HL.

---

### First HH+HL → upgrade to 5×

**Step 1 — Calculate unrealized profit on current position**

```
Profit = Position_size_BTC × (Current_price − Entry_price)
```

**Step 2 — Take 40% outside**

```
Outside_Strategy += 40% × Profit   (buy spot BTC immediately)
Available = 60% × Profit
```

**Step 3 — Change leverage setting to 5× on Binance**

**Step 4 — Add contracts AT the new HL price**

Size the add using the same backwards calculation:

```
Add_margin = Acceptable_extra_loss_$ ÷ (5% × 5)
           = Acceptable_extra_loss_$ ÷ 0.25
```

Source priority: use Available (60% of profit) first → supplement from Hold USD if needed.

**Step 5 — Update stop-loss order**

Cancel old stop order. Place new stop-loss market order at: **New_HL × 0.95**

**Step 6 — Hold USD receives remainder**

```
Hold_USD += max(0, Available − Add_margin)
```

**Result after upgrade:**

| Leverage | Distance to stop | Margin loss if stop hits |
|---|---|---|
| 5× | 5% | **25%** |

Liquidation at 5× = 20% below HL. Stop at 5% below HL. Stop fires first. ✓

---

### Second HH+HL → upgrade to 10×

Same sequence as above. Change leverage to 10×. Add at new HL.

```
Add_margin = Acceptable_extra_loss_$ ÷ (5% × 10)
           = Acceptable_extra_loss_$ ÷ 0.50
```

Update stop-loss order to: **New_HL × 0.95**

**Result after upgrade:**

| Leverage | Distance to stop | Margin loss if stop hits |
|---|---|---|
| 10× | 5% | **50%** |

Liquidation at 10× = 10% below HL. Stop at 5% below HL. Stop fires first. ✓

The 50% loss is acceptable — 40% of profits from two prior extractions is already outside permanently.

---

### Further HH+HL at 10× (already at max leverage)

No leverage increase. No contract add.

1. Take 40% of profit → Outside Strategy
2. Cancel old stop order. Set new stop at **New_HL × 0.95**
3. Remaining 60% → Hold USD

Repeat every time a new HH+HL forms at the 10× stage.

---

## Price Action Between HH+HL Events

| Price does | Action |
|---|---|
| Goes up, no new HH+HL yet | Do nothing. Hold position. Watch for structure. |
| Pulls back but stays above stop | Do nothing. Stop order protects you. |
| Hits stop | Full position closes → see below |

---

## When Stop Fires

The stop-loss order triggers. The full position closes at market.

### What happens to capital

| Contract tranche | Result when stop fires |
|---|---|
| Original 3× contracts (lowest entry) | Exits at a gain — original entry was far below stop price |
| 5× add contracts (mid entry) | Exits near breakeven or small gain |
| 10× add contracts (most recent, highest entry) | Exits at −50% of that add's margin |

Overall: the 10× add takes the biggest hit. Earlier entries exit profitably because the stop is always above their entry price (stop = 5% below a HL that formed after they were entered).

### Capital routing after stop

```
Realized P&L from all contracts (net) → Hold USD
(Outside Strategy profits already extracted before the stop — untouched)
```

---

## Re-entry

Re-entry is identical to first entry. No exceptions.

1. Wait for all 4 entry conditions to realign
2. Identify the current confirmed HL
3. Enter at that HL with 3× leverage
4. Size using: `margin = acceptable_loss ÷ 0.15`
5. Place stop at HL × 0.95
6. Build the snowball again from scratch

**No shortcut to 5× or 10× on re-entry.** The market must prove itself again through a new HH+HL event before leverage increases.

---

## Scenarios — Bad Cases

### Scenario A — Enter 3×, price drops immediately to stop

```
Enter at HL ($90,000) at 3× → Stop at $85,500 (5% below)
Price falls → stop fires at $85,500
Loss = 15% of margin
Remaining capital → Hold USD
Re-entry: wait for all 4 conditions to reset
```

No profit was extracted yet. Total loss = 15% of the initial margin deployed. Acceptable at this stage because position was small.

---

### Scenario B — Enter 3×, first HH+HL fires (→5×), price drops to stop

```
Enter 3× at HL1 ($90,000) → stop at $85,500
New HH at $100,000. New HL at $95,000.

Action at HL2:
  → 40% of profit → Outside Strategy ✓
  → Upgrade to 5×, add at $95,000
  → New stop at $90,250 (5% below $95,000)

Price falls → stop fires at $90,250
  3× contracts ($90,000 entry): exit at $90,250 → tiny gain ≈ 0.3% × margin
  5× contracts ($95,000 entry): loss = 5% × 5 = 25% of add margin
Net: small gain on 3× tranche, 25% loss on 5× tranche
40% of first profit is already permanently outside
Remaining capital → Hold USD
Re-entry: back to 3×
```

---

### Scenario C — Reaches 10×, stop fires

```
3× entry at HL1 ($80,000)
HH+HL #1 → 5× add at HL2 ($90,000), 40% profit extracted #1
HH+HL #2 → 10× add at HL3 ($95,000), 40% profit extracted #2
Stop now at $90,250 (5% below $95,000)

Price falls → stop fires at $90,250
  3× contracts ($80,000 entry): exit at $90,250 → profit
  5× contracts ($90,000 entry): exit at $90,250 → small profit
  10× contracts ($95,000 entry): exit at $90,250 → loss = 50% of 10× add margin

Net: gains on earlier tranches partially offset 10× loss
Two rounds of 40% profit already in Outside Strategy — untouched
Remaining capital → Hold USD
Re-entry: back to 3×
```

---

### Scenario D — At 10×, another HH+HL forms, then stop fires later

```
Already at 10×. New HH+HL forms.
→ Take 40% of profit → Outside Strategy (third extraction)
→ Trail stop to new HL × 0.95 (no leverage change)
→ Remaining → Hold USD

Price later drops to new stop → full close
Three rounds of 40% profit extracted. Position closes profitably or near breakeven overall.
Hold USD receives remaining position capital.
```

---

## Stop-Loss Order Rules

- **Always** have exactly one active stop-loss market order on the position
- Stop price = most recent confirmed HL × 0.95
- Update the stop order immediately when a new HH+HL is confirmed and you take action
- Never remove the stop order without replacing it with a new one at the same or higher price
- Stop only moves **up** — never lower

**Liquidation price is a safety backstop only.** It should never be the intended exit. If somehow liquidation fires before the stop (network outage, extreme slippage), that is a failure condition — ensure the stop order is always active.

---

## Capital Tracker

### Group balances

| Group | Balance | Last updated |
|---|---|---|
| In Position — margin deposited | | |
| In Position — leverage setting | | |
| Outside Strategy — spot BTC value | | |
| Hold USD | | |

### Position entries log

| Tranche | Date | HL entry price | Margin | Leverage | Stop order price | Status |
|---|---|---|---|---|---|---|
| 1 (initial 3×) | | | | 3× | | Open / Closed |
| 2 (5× add) | | | | 5× | | Open / Closed |
| 3 (10× add) | | | | 10× | | Open / Closed |

### Profit extractions log

| Date | HH+HL # | Profit | 40% → Outside | To add | To Hold USD |
|---|---|---|---|---|---|
| | 1st | | | | |
| | 2nd | | | | |
| | 3rd+ | | | | |

---

## Weekly Checklist

1. Has a new HH formed since last check?
2. Has a new HL formed and stabilized since last check?
3. If yes to both → run snowball action sequence
4. Is the stop-loss order still active at the correct price? Confirm on Binance.
5. Check 4 entry conditions — still all passing?
6. Update group balances in tracker

## Monthly Checklist

1. Add DCA amount to Hold USD balance
2. Review Outside Strategy — confirm spot BTC purchase was made from all extracted profits

---

## Plan Summary

| Decision | Rule |
|---|---|
| Instrument | Binance USD-M Futures — isolated margin |
| Entry / add timing | Always at the confirmed HL — never at HH |
| First entry | 3× leverage · margin = loss_$ ÷ 0.15 |
| Stop | Stop-loss market order at HL × 0.95 |
| Liquidation | Natural backstop only — always below stop at ≤10× |
| HH+HL fires | Take 40% profit outside → add at new HL → increase leverage → update stop |
| Leverage path | 3× → 5× → 10× (one step per HH+HL event) |
| Loss if stop fires | 3× = 15% · 5× = 25% · 10× = 50% (of that tranche's margin) |
| Max leverage | 10× — never exceed |
| At 10× HH+HL | Extract 40% profit + trail stop only. No further leverage increase. |
| Stop fires | Full close → capital to Hold USD → re-entry at 3× from scratch |
| 40% profit | → Outside Strategy (buy spot BTC immediately, never returns) |
| Remaining profit | → Fund next tranche add first → remainder to Hold USD |
| Monthly DCA | → Hold USD only |
