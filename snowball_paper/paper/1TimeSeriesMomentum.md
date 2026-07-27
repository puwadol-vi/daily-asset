# Time Series Momentum

**Moskowitz, Ooi & Pedersen (2012), *Journal of Financial Economics* 104, 228–250**
Source PDF: `snowball/paper/1TimeSeriesMomentum.pdf` (converted via [microsoft/markitdown](https://github.com/microsoft/markitdown))

---

## Summary

**Data**: 58 of the most liquid futures contracts — 24 commodities, 12 cross-currency
pairs, 9 developed equity indexes, 13 developed government bonds — January 1965
through December 2009.

**Core claim ("time series momentum")**: an instrument's own trailing return predicts
its own future return, independent of how it's doing relative to other instruments
(that's the *different*, older "cross-sectional momentum" literature — Jegadeesh &
Titman). Positive for **every one of the 58 instruments tested**, not just on average.

**Shape of the effect**:
- Persistence/continuation for roughly **1 to 12 months** after formation.
- **Partial reversal** over the following ~1–4 years (total pattern: ~1yr momentum,
  then several years of fading/reversing).
- Robust across every (look-back, holding-period) combination tested, both 1–60
  months.

**Position sizing (the important mechanical detail)**: every position — long or
short — is sized to a **constant ex-ante annualized volatility target (40%)**,
i.e. `position_size = target_vol / instrument_ex_ante_vol`. This is deliberate
volatility-normalization, not conviction sizing: it exists purely so returns are
comparable/aggregable across wildly different instruments (e.g. bonds vs.
commodities), not because higher-vol assets are being avoided as a risk call.

**Ex-ante volatility estimator**: an exponentially-weighted moving average (EWMA)
of squared daily returns (like a simple univariate GARCH / RiskMetrics model),
annualized, with the decay parameter chosen so the weights' center of mass is
60 days. Uses only lagged (t-1) data — no look-ahead.

**Diversified portfolio result**: an equal-weighted combination of the single-
instrument TSM strategies across **all 58 instruments / 4 asset classes** produces
a Sharpe ratio **> 1**, roughly **2.5×** the Sharpe of a passive equity market
portfolio, with low correlation to standard risk factors (market, SMB, HML) — this
is the central "why diversify the pyramid across many trending things instead of
one" result.

**Performs best in extreme markets**: TSM's return is largest during the biggest
up *and* down months for the overall market — a convex, crash-hedge-like payoff
profile, not a linear risk-on bet. This is presented as a genuine puzzle for
risk-based explanations of the premium.

**Not fully explained by other known factors**: regressing the diversified TSM
factor on MSCI World + Fama-French SMB/HML/UMD leaves a large, significant alpha
(~1.58%/month). Repeating against Asness-Moskowitz-Pedersen's cross-asset
"value and momentum everywhere" factors still leaves alpha (~1.09%/month) — TSM
loads significantly on cross-sectional momentum (UMD) but isn't subsumed by it.

**Who's on which side**: using CFTC positioning data, speculators are shown to
trade *with* time series momentum (net long when trailing return is positive,
scaling out as the trend reverses) and profit from it; hedgers take the other
side and are the ones paying for it.

---

## Formulas as given in the paper

Ex-ante annualized variance (EWMA of squared daily returns, center of mass = 60
trading days, uses only data through t-1):

```
σ²_t = 261 * Σ_{i=0}^{∞} (1-δ) * δ^i * (r_{t-1-i} - r̄)²
```

Per-instrument TSMOM strategy return (12-month look-back, 1-month hold, scaled
to 40% ex-ante vol):

```
r_TSMOM,s(t,t+1) = sign(r_s(t-12,t)) * (40% / σ_s,t) * r_s(t,t+1)
```

Diversified TSMOM factor = equal-weighted average of `r_TSMOM,s` across all
instruments/asset classes.

---

## Logic / pseudo-code

`[indicator/logic] => [result/target]`

```
trailing_12m_excess_return(instrument) > 0
    => go/stay LONG instrument next month (time series momentum signal = up)

trailing_12m_excess_return(instrument) < 0
    => go/stay SHORT instrument next month (time series momentum signal = down)

sign(trailing_12m_excess_return) unchanged vs last month's sign
    => hold existing position, no rebalance needed

sign(trailing_12m_excess_return) flips vs last month's sign
    => flip position direction at next month's start

ex_ante_vol(instrument) = EWMA_60d(daily_return^2) annualized
    => position_size(instrument) = target_annual_vol (e.g. 40%) / ex_ante_vol(instrument)

ex_ante_vol(instrument) rises
    => position_size(instrument) shrinks proportionally (inverse-vol sizing --
       same "dynamic leverage from volatility" idea used elsewhere in this project)

ex_ante_vol(instrument) falls
    => position_size(instrument) grows proportionally, same target risk maintained

combine sign(trailing_12m_return)-sized positions, equal-weighted,
across many uncorrelated instruments/asset classes
    => diversified TSMOM factor: Sharpe > 1, ~2.5x a single passive equity portfolio,
       low correlation to market/SMB/HML

|market_return_this_month| is extreme (large up OR large down)
    => TSM strategy's return tends to be largest that month (convex / crash-hedge payoff,
       not a linear risk-on bet)

look_back_period in [1..12] months AND holding_period in [1..12] months
    => sign(trailing_return) signal produces positive average return for essentially
       every (look_back, holding_period) combination tested -- the effect is not
       fragile to the exact parameter choice

horizon since formation > ~12 months (out to ~1-4 years)
    => expected forward return from the same signal partially reverses (fades/flips
       sign) -- momentum is a 1-year-ish phenomenon, don't expect it to keep
       compounding on the same signal indefinitely without re-checking it monthly

net_speculator_position(instrument) is positive and rising
    => consistent with instrument's own trailing return recently positive (speculators
       trade WITH time series momentum, not against it)
```

---

## Relevance to Snowball

Directly supports the **"strength of trend"** leg of the Snowball three-factor
read (discount → momentum → continuity), and is the clearest academic precedent
for two mechanical choices already in this project:

- **Volatility-scaled position sizing** (`position_size ∝ 1/ex_ante_vol`) is
  exactly the "dynamic leverage adjustment using volatility" idea from V6 —
  this paper is where that idea is formally validated, just phrased as sizing
  to a constant vol target rather than a discrete LOW/MEDIUM/HIGH regime.
- **Diversification across many trending instruments** beats concentrating in
  one, even though every individual instrument's TSM strategy is profitable on
  its own — worth keeping in mind if Snowball is ever extended beyond a single
  asset (BTC).
- The **~12-month decay / partial reversal** finding is a caution: a trend
  signal isn't a "hold forever" input — it has a shelf life, which is a
  reasonable prior for how often Snowball's own trend/momentum read should be
  re-evaluated rather than trusted indefinitely once confirmed.
