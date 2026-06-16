# The Day-Wise Strategy v2 — RSI Regime First

> Based on real yfinance data from 49 Nifty 50 stocks, Mar 16 – Jun 15 2026.
> RSI regime OVERRIDES day-of-week. This is the overlooked pattern the data screams.

---

## The Single Most Important Rule

**RSI regime determines direction. Day-of-week determines confidence.**

| RSI | Gap Direction | Action | Why | Fill Rate | Avg OC (when filled) |
|-----|-----------|--------|-----|-----------|---------------------|
| **<30 (oversold)** | Up | **SHORT** | Stock is in downtrend. Gap fill is a bull trap. | 83.5% | −0.75% |
| **<30 (oversold)** | Down | **SKIP** | No bounce edge. Stock keeps falling even when gap fills. | 75.5% | −0.18% |
| **>70 (overbought)** | Down | **LONG** | Stock is in uptrend. Gap fill is a buying opportunity. | 84.8% | +0.40% |
| **>70 (overbought)** | Up | **SKIP** | Momentum survives. Gap-ups don't reverse reliably. | 68.9% | +0.31% |
| 30–70 | Normal | Per day-wise | Market is in balance. Day-of-week effect dominates. | Varies | Varies |

---

## Day-Wise Rules (for RSI 30–70 only)

| Day | Avg Ret | Personality | Trade Gap-Up? | Trade Gap-Down? | Best Setup |
|-----|---------|-------------|:---:|:---:|------------|
| **Mon** | −0.28% | Weak, toxic | ⚠️ Low vol only (62% fill) | ❌ Skip (45%) | Gap-up + low vol → SHORT |
| **Tue** | +0.18% | Golden day | ✅ Low vol (73%) | ✅ Low vol (82%) | Gap-down + low vol → LONG |
| **Wed** | **+0.80%** | Bullish | 🚫 NEVER (35%) | ✅ BEST (75–85%) | **Gap-down → LONG (84.7% fill)** |
| **Thu** | **−0.28%** | Bearish | ✅ Short (71–79%) | ❌ Skip (52%) | Gap-up + low vol → SHORT |
| **Fri** | −0.05% | Neutral | ⚠️ High vol only (78%) | ✅ Low vol (81%) | Gap-down + low vol → LONG |

---

## What the Data Actually Says (Ignoring All Bias)

### 1. LOW RSI Regime (<30) — The Overlooked Truth

The day-wise strategy says "long gap-downs" on certain days. **For oversold stocks, this loses money.**

| Day + Gap Direction | Standard Strategy | RSI-Regime Actually Says | EV Difference |
|---------------------|------------------|------------------------|--------------|
| Wed gap-down (the "best" setup) | LONG (+0.80% bias) | **SKIP for RSI<30** (OC=−0.46%) | −0.84% |
| Tue gap-down | LONG (82.1% fill) | **SKIP for RSI<30** (OC=−0.69%) | −0.93% |
| Fri gap-down + low vol | LONG (80.6% fill) | **SKIP for RSI<30** (OC=−0.54%) | −0.82% |
| Mon gap-up + low vol | SHORT (62.6% fill) | **SHORT** (EV=+0.98%) | +0.36% |
| Wed gap-up | SKIP (35% fill) | **SHORT RSI<30** (EV=+0.72%) | +0.72% |

### 2. HIGH RSI Regime (>70) — The Momentum Truth

Conventional wisdom says "overbought = reversal." The data says the opposite — momentum survives.

| Day + Gap Direction | Standard Strategy | RSI-Regime Actually Says | EV |
|---------------------|------------------|------------------------|---|
| Mon gap-down | SKIP (45% fill) | **LONG for RSI>70** | **+0.93%** |
| Wed gap-down | LONG | **LONG for RSI>70** | +0.65% |
| Thu gap-down | SKIP (52%) | **LONG for RSI>70** | +0.58% |
| Tue gap-down | LONG | **LONG for RSI>70** | +0.56% |

### 3. MID RSI Regime (30–70) — Day-Wise Works

The original day-wise strategy is valid for this regime:
- Wed gap-down → LONG: 85.5% fill, OC=+0.42%, EV=+0.36%
- Mon gap-up → SHORT: 62% fill, OC=−0.81%, EV=+0.50%
- Thu gap-up → SHORT: 77.8% fill, OC=−0.62%, EV=+0.48%

---

## Daily Checklist (RSI-Regime Aware)

### Every Morning: Check RSI First
```
1. Scan RSI for all stocks
2. Identify RSI<30 → these are SHORT-ONLY if gap-up, SKIP if gap-down
3. Identify RSI>70 → these are LONG-ONLY if gap-down, SKIP if gap-up
4. Rest (30-70) → use day-wise rules below
```

### Monday
```
□ RSI<30 gap-up? → SHORT (EV=+0.98%) ← BEST MONDAY SETUP
□ RSI>70 gap-down? → LONG (EV=+0.93%)
□ 30-70 gap-up + vol<0.8x → SHORT
□ Everything else → SKIP
```

### Tuesday
```
□ RSI<30 gap-up? → SHORT (EV=+0.34%)
□ RSI>70 gap-down? → LONG (EV=+0.56%)
□ 30-70 + gap-down + vol<0.8x → LONG (82.1% fill)
□ 30-70 + gap-up + vol<0.8x → SHORT (73.2% fill)
□ 30-70 + gap<0.5% + any vol → TRADE
```

### Wednesday — Best Day
```
□ RSI<30 gap-up? → SHORT (EV=+0.72%, 95.5% fill!) ← Best Wed setup
□ RSI>70 gap-down? → LONG (EV=+0.65%)
□ 30-70 + gap-down (any vol) → LONG (85.5% fill, 74.6% even with high vol)
□ NEVER touch gap-ups in 30-70 regime (45% fill)
```

### Thursday
```
□ RSI<30 gap-up? → SHORT (EV=+0.44%)
□ RSI>70 gap-down? → LONG (EV=+0.58%)
□ 30-70 + gap-up → SHORT (77.8% fill, EV=+0.48%)
□ 30-70 + gap-down → SKIP (72% fill but OC=+0.04%)
```

### Friday
```
□ RSI<30 gap-up? → SHORT (EV=+0.75%)
□ RSI>70 gap-down? → LONG (EV=+0.29%)
□ RSI>70 gap-up? → SHORT (94.6% fill, EV=+0.27%)
□ 30-70 + gap-down + vol<0.8x → LONG (84.3% fill)
□ 30-70 + gap-up + high vol>1.5x → SHORT (78.1% fill)
□ Close all by 3:10 PM
```

---

## Golden Rules

1. **Gap size: 0.3% to 0.8% ONLY** — smaller gaps fill more reliably (monotonic relationship)
2. **Volume 0–0.5x = 69% fill** — the quieter the better
3. **Volume >3x = 47% fill** — high volume destroys edge
4. **Never trade against a 70%+ tide** — when 91% of stocks gap same direction, individual gap analysis is useless
5. **RSI < 30 means TREND, not reversal** — the gap fill is a trap, not a signal
6. **Unfilled gaps are time bombs** — 83% fill within 1 day, 91% within 5 days

---

*Data: yfinance for 49 Nifty 50 stocks, Mar 16 – Jun 15 2026 (2,988 gap events).*
*Key source: `findings.md` sections 11.5 (RSI), 11.1 (volume), 13.3 (smart money pattern).*
