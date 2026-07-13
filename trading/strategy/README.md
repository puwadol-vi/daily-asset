---
description: 5 strategies
---

# strategy

***

## Bitcoin Options Income Strategy

`Bitcoin_Options_Income_Strategy.md`

Sell options close to the money (0.30–0.40 delta) to collect large premiums daily. A 3-layer filter stack — ADX, Stochastic RSI, and VPVR volume nodes — must all align before any trade opens, targeting >90% directional win rate. Sell a put at structural support when momentum is exhausted to the downside; sell a call at structural resistance when buying pressure dies. Short duration (3–7 DTE) maximizes theta decay and keeps capital free to redeploy. If a level breaks, roll the option to the next weekly cycle at a safer strike for a net credit rather than taking the full loss.

***

## Bitcoin Call Snowball Strategy

`BTC_Call_Option_Snowball_Plan.md`

Buy a long-dated BTC call option ($100/month, delta \~0.40) every first Monday and roll profits back into a larger position over time. Three entry conditions (21W EMA, volume, ADX) gate each monthly entry — a failed check delays or downsizes the position, never forces it. Three roll rules govern when to exit and reopen: time decay accelerating (< 6 weeks left), delta rising above 0.70 (leverage fading), or theta bleeding > 1%/day. 30% of each roll's profit is moved out; the rest compounds into the next call. Maximum loss per entry is always the premium paid — no liquidation, no margin calls.

***

## Multi-Coin Allocation Strategy

`MultiCoin_Allocation_Plan.md`

A daily-buying spot portfolio across BTC, ETH, BNB, SOL, XRP, steered by two signals: a slow weekly signal sets how much of each coin to hold (weighted by distance above the 200D EMA on ratio charts), and a fast daily signal picks which coin to buy today (round-robin EMA12/26 crossover on all 10 pair ratios). The coin most underweight its target allocation among today's winners gets the daily buy. When a coin's ratio has been above the 200D EMA for 30+ days at 15%+ distance, a 3× futures long (50% of that coin's spot value) is layered on top — closed when ratio weakens. A BTC put option hedge is added only when a market-wide stress trigger fires (market cap -20%, round-robin collapse, or BTC ratio below -15%).

***

## Bitcoin Futures Snowball Strategy

`Futures_Snowball_Leverage_Strategy.md`

One isolated long on Binance USD-M Futures, starting at 3× and snowballing to 5× then 10× — each upgrade triggered by a confirmed new HH+HL, with new contracts always added at the HL price. The stop is a stop-loss order at 5% below the structural HL; because entries happen at the HL, liquidation naturally sits 10–33% below it, so the stop always fires before liquidation at any leverage ≤ 10×. At each HH+HL event: 40% of profit goes permanently to spot BTC (Outside Strategy), the rest funds the next leverage add, remainder to Hold USD. Loss if stop fires scales with leverage: 15% at 3×, 25% at 5×, 50% at 10× — on that tranche only; earlier entries exit at a profit since stop is always above their entry. After any stop, re-entry starts fresh at 3× with the same 4-condition filter.

***

## Bitcoin Grid Option Hedge Strategy

`Grid_Option_Hedge_Strategy.md`

Set a 10-level spot price grid between the nearest support (lower bound) and resistance (upper bound) — minimum 10% range — and let it passively buy dips and sell bounces within the range. A protective put option is not open by default; it is only purchased when a risk trigger fires: price drops into the lower 40% of the grid, 6+ buy levels are filled with no sells, BTC closes below the 21W EMA, or ADX rises above 30 while price falls. The hedge covers the grid lower bound (3% of grid capital, 3–4 week expiry) and is sold as soon as the risk condition clears or the put reaches 2× value. If price closes below the lower bound on two consecutive days, the entire grid is closed and the active put (if ITM) is sold to offset inventory losses. Only one hedge is active at a time; if a second trigger fires while a hedge is open, that is a signal to close the grid rather than stack more puts.
