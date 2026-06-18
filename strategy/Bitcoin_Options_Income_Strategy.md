# Bitcoin Options Income Strategy: High-Frequency Technical Filter

## 1. Strategy Core Concept

- **Objective:** want high-frequency income, meaning you want a position open almost every single day to maximize the number of times you collect premium. To survive doing this daily, your absolute priority is an incredibly high win rate
- **The Solution:** Sell options closer to the money (**0.30 to 0.40 Delta**) to collect substantial, high-yield premiums.
- **The Edge:** Achieve a >90% directional win rate not by hiding far away from the price, but by using a multi-layered **Technical Filter Stack** that accurately identifies momentum exhaustion, trend weakness, and structural price floors/ceilings before entering.

---

## 2. The Indicator Filter Stack

To open a position, all three components of the filter stack must align simultaneously.

1. **Trend Strength Filter:** Average Directional Index (**ADX 14**)
   - _Purpose:_ Ensures the market is sideways or that an active trend is dying out. Prevents entering during a runaway breakout or a vertical liquidation cascade.
2. **Momentum Exhaustion Filter:** Stochastic RSI (**Stoch RSI 14, 14, 3, 3**)
   - _Purpose:_ Captures precision short-term turning points where buying or selling pressure is completely spent.
3. **Structural Support/Resistance Filter:** Volume Profile Visible Range (**VPVR**)
   - _Purpose:_ Pinpoints High Volume Nodes (HVN)—price levels where massive institutional orders have historical memory, acting as physical barriers.

---

## 3. Operational Setup Checklists

### Checklist A: Cash-Secured Put (CSP)

_Execute when the market attempts to push down but completely runs out of breath at structural support._

- [ ] **Timeframe:** 4-Hour or 1-Day chart.
- [ ] **ADX (14):** Must be **Below 25** (sideways market) OR **Above 40 but clearly rolling downward** (bearish momentum is dying).
- [ ] **Stochastic RSI:** Must be **Below 20** (Oversold territory) AND the blue %K line has crossed above the orange %D line (_Bullish Cross_).
- [ ] **Structural Confirmation:** Price is pulling back into a major **High Volume Node (HVN)** on the Volume Profile.
- [ ] **Execution:** Sell a **3 to 7 DTE Put** with a strike price tucked **just below** that High Volume Node level (targeting a ~0.30 Delta).

### Checklist B: Covered Call (CC)

_Execute when the market pumps into a heavy wall of overhead resistance and buying pressure aggressively dies._

- [ ] **Timeframe:** 4-Hour or 1-Day chart.
- [ ] **ADX (14):** Must be **Below 25** (sideways market) OR **Above 40 but clearly rolling downward** (bullish momentum is dying).
- [ ] **Stochastic RSI:** Must be **Above 80** (Overbought territory) AND the blue %K line has crossed below the orange %D line (_Bearish Cross_).
- [ ] **Structural Confirmation:** Price is tapping the upper edge of the **Value Area High (VAH)** or a major horizontal resistance level.
- [ ] **Execution:** Sell a **3 to 7 DTE Call** with a strike price tucked **just above** that resistance barrier (targeting a ~0.30 Delta).

### Checklist C: The "Do Nothing" Filter

_If any of these conditions are met, do not open a trade. Cash/Cold Storage is a valid position._

- [ ] **ADX is rising sharply above 30:** Indicates a powerful breakout trend is forming. Oscillators _will_ fail here.
- [ ] **Stochastic RSI is in no man's land (between 20 and 80):** No edge on momentum execution.
- [ ] **Price is floating between High Volume Nodes:** Lacks structural protection; vulnerable to erratic daily noise.

---

## 4. Key Rules for High-Frequency Management

- **The ADX Rule is Absolute:** Never sell a Put if the ADX is climbing vertically, even if the Stoch RSI says it is heavily oversold. Runaway momentum will blow past a 0.30 Delta strike effortlessly.
- **Short-Duration Compounding:** By utilizing 1-3 DTE options, you take advantage of rapid weekend/overnight time decay (Theta). Capital frees up multiple times a week to redeploy into fresh setups.
- **Risk Mitigation (The Roll):** Because you are selling close to the money for premium efficiency, if a structural level breaks, do not take the full loss. Buy back the option and **Roll it out** to the next weekly cycle at a safer, adjusted strike price for a net credit.
