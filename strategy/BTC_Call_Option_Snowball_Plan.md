# BTC Call Option DCA Snowball Plan

---

## Overview

A long-term Bitcoin call option strategy using monthly DCA to build a compounding
position through rolling profits. No futures liquidation risk. No leverage margin
calls. Max loss per entry is always the premium paid.

---

## Core Parameters

| Parameter             | Value                                        |
| --------------------- | -------------------------------------------- |
| Monthly entry amount  | $100 USD                                     |
| Option type           | Call (long)                                  |
| Expiry at entry       | 3 or 6 months out                            |
| Target delta at entry | ~0.40                                        |
| Strike selection      | Whichever strike gives delta closest to 0.40 |
| Platform              | Binance Options or Deribit                   |
| Plan end date         | June 2029                                    |

---

## Entry Rules

### When to enter

Every **first Monday of the month**.

### 3 month Entry conditions — ALL THREE must be true

IF 21W EMA condition fails, skip
If rest condition fails, open 6 month instead

| Condition                                  | How to check                      | Tool        | if fail      |
| ------------------------------------------ | --------------------------------- | ----------- | ------------ |
| BTC weekly close above 21W EMA             | Check weekly chart                | TradingView | skip         |
| Weekly volume above 10-week average volume | Check volume bars on weekly       | TradingView | open 6 month |
| Weekly ADX above 20                        | Add ADX indicator to weekly chart | TradingView | open 6 month |

### If skipped

Roll the $100 into next month. Three consecutive skips = $300 available on
next valid entry. Do not force entry — saved capital is stronger entry later.

---

## Strike Selection (each entry)

1. Open the option chain on Binance or Deribit
2. Select expiry 3 or 6 months out
3. Find the strike where delta is closest to 0.40
4. Buy $100 worth of that contract (fractional contracts allowed on Deribit)
5. Note down: entry date, strike, expiry date, premium paid, delta at entry

---

## Roll Rules

Three triggers. **First trigger that fires wins.** Check in this order every week.

### Rule 1 — Time (primary)

**Trigger:** Less than 6 weeks remaining to expiry
**Action:** Roll on the next first Monday entry day
**Why:** Theta accelerates sharply in final 6 weeks. Exit before decay becomes expensive.
**Note:** If remaining value is less than $20 — let it expire, do not pay roll fee.

### Rule 2 — Theta (early warning)

**Trigger:** Daily theta exceeds 1% of remaining option value
**How to check:** Look up current theta on option chain. Divide by current option value.
If result is above 0.01 (1%) — trigger is active.
**Action:** Roll on the next first Monday entry day
**Why:** This catches a position that has lost significant value but still has months
remaining — it is bleeding slowly to zero. Rolling recovers remaining value and redeploys.
**Note:** For a healthy 6-month option this rarely triggers before Rule 1. It mainly
catches deeply underwater positions.

### Rule 3 — Delta (profit optimizer)

**Trigger:** Delta rises above 0.70
**How to check:** Look up current delta on option chain every Monday
**Action:** Roll into a new 3-month call at delta 0.40 on that Monday
**Why roll:** Above 0.70 delta the option behaves increasingly like spot BTC — leverage
advantage is fading. Rolling back to 0.40 delta resets leverage while the trend is
strong, letting you compound more aggressively into the continuation. Delta above 0.70
already confirms trend — no need to recheck entry conditions.
**Note:** If Rule 3 fires on the first Monday of the month, this roll counts as that
month's entry. Do not open an additional $100 position on the same day.

### Roll mechanics (applies to all three rules)

- Sell the existing option
- Take proceeds + that month's $100 DCA → buy new call at delta 0.40
- Rule 1 and Rule 2: roll into 6-month expiry
- Rule 3: roll into 3-month expiry

---

**How to calculate "move profit out" amount:**
Only the profit portion is split 30% out — not the full roll proceeds.

Example: bought option for $100, roll proceeds = $400

- Profit = $400 − $100 = $300
- Move out = 30% of $300 = $90
- Redeploy into new call = $400 − $90 = $310

---

## Exit Rules

**Trigger:** June 2029
**Action:** Sell all positions regardless of status in June 2029.
Do not roll any position past June 2029 expiry.
**Why June 2029:** Targets 4–6 months before estimated next cycle top
(next halving April 2028, historical top 12–18 months after = mid to late 2029).

---

## Sideways Protection

Three conditions are already your primary sideways filter (entry conditions above).
Additional behavior:

- **Two consecutive months expire worthless:** pause new entries.
  Resume only when a clear weekly higher high forms AND all three entry
  conditions pass simultaneously.
- **Saved capital during pause:** stacks and deploys as one larger entry
  on resumption. Do not split into small entries — deploy the full saved
  amount on the confirmed re-entry.

---

## Weekly Checklist (every Monday)

1. Check delta of each open position → is any above 0.70? (Rule 3)
2. Check theta/value ratio of each open position → is any above 1%? (Rule 2)
3. Check days to expiry of each open position → is any under 42 days? (Rule 1)
4. If it is the first Monday: check 21W EMA + Volume + ADX → enter if all pass
5. Log any changes in position tracker

---

## Position Tracker (log each entry)

| Entry date | Strike | Expiry | Premium paid | Delta at entry | Current value | Status |
| ---------- | ------ | ------ | ------------ | -------------- | ------------- | ------ |
|            |        |        |              |                |               |        |

Status options: Open / Roll pending / Rolled / Expired worthless / Exited

---

## Maximum Loss

Each monthly entry has a hard maximum loss equal to the premium paid ($100).
No margin calls. No liquidation cascade. No position affects any other position.
Total maximum loss across the entire plan = sum of all premiums paid.

---

## Plan Summary (one page)

| Decision        | Rule                                                                             |
| --------------- | -------------------------------------------------------------------------------- |
| Entry timing    | First Monday of each month                                                       |
| Entry amount    | $100 (stack skipped months)                                                      |
| Entry condition | 21W EMA must pass (else skip). Volume + ADX must pass for 3-month (else 6-month) |
| Option          | Call, 3-month or 6-month expiry, delta ~0.40                                     |
| Roll — time     | Less than 6 weeks remaining → roll next Monday                                   |
| Roll — theta    | Daily theta above 1% of value → roll next Monday                                 |
| Roll — delta    | Delta above 0.70 → roll that Monday into 3-month call                            |
| Profit out      | 30% of profit                                                                    |
| Sideways pause  | 2 consecutive worthless expirations → pause until higher high                    |
| Exit            | June 2029 → close everything                                                     |
