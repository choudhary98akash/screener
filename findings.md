# Pure Data Findings

> No strategy. No bias. No interpretation. Just what the data says.
> Source: Real yfinance data for 49 Nifty 50 stocks, Mar 16 – Jun 15 2026 (62 trading days, 2,988 observations)

---

## 1. The Day-of-Week Effect (Strongest Signal in the Data)

| Day | Avg Return | % Positive | Personality |
|-----|-----------|-----------|-------------|
| Monday | **−0.283%** | 45.4% | Weak, bearish |
| Tuesday | **+0.180%** | 53.8% | Mildly bullish |
| **Wednesday** | **+0.798%** | **65.0%** | **Strongly bullish** |
| **Thursday** | **−0.280%** | **37.6%** | **Strongly bearish** |
| Friday | −0.046% | 45.8% | Neutral, weak |

Wednesday is the outlier: stocks go up 65% of the time, averaging +0.80%.
Thursday is the mirror: stocks go down 62.4% of the time.
The swing between Wednesday and Thursday is **1.08%** — the largest predictable pattern in the dataset.

---

## 2. Gap Size vs Fill Rate (Monotonic Relationship)

| Gap Range | Events | Filled | Fill Rate |
|-----------|--------|--------|-----------|
| 0.0–0.3% | 1,073 | 975 | 90.9% |
| 0.3–0.5% | 436 | 324 | 74.3% |
| 0.5–0.8% | 482 | 312 | 64.7% |
| 0.8–1.2% | 448 | 220 | 49.1% |
| 1.2–2.0% | 365 | 128 | 35.1% |
| 2.0–5.0% | 172 | 44 | 25.6% |
| >5.0% | 12 | 1 | 8.3% |

The relationship is clean and monotonic: **smaller gaps fill more often, larger gaps fill less often.** There is no threshold where this reverses — every step up in gap size reduces fill probability.

---

## 3. Gap Fill Rate by Day of Week

| Day | Gaps | Filled | Fill Rate |
|-----|------|--------|-----------|
| Monday | 637 | 363 | 57.0% |
| **Tuesday** | **539** | **418** | **77.6%** |
| Wednesday | 637 | 390 | 61.2% |
| Thursday | 588 | 412 | 70.1% |
| Friday | 587 | 421 | 71.7% |

Tuesday is the best day for gap fills (77.6%). Monday is the worst (57.0%).

---

## 4. Gap Fill Rate vs Previous Day's Range

| Prev Day Range | Gaps | Filled | Fill Rate |
|---------------|------|--------|-----------|
| 0.0–1.0% | 184 | 147 | 79.9% |
| 1.0–1.5% | 398 | 278 | 69.8% |
| 1.5–2.0% | 688 | 488 | 70.9% |
| 2.0–3.0% | 1,044 | 670 | 64.2% |
| >3.0% | 674 | 421 | 62.5% |

When the previous day was calm (range <1%), gaps fill 79.9% of the time. When the previous day was volatile (range >3%), gaps fill only 62.5%.

---

## 5. Gap Direction + Previous Day Direction

| Pattern | Gaps | Filled | Fill Rate |
|---------|------|--------|-----------|
| Gap continues prev day trend | 1,173 | 745 | 63.5% |
| Gap reverses prev day trend | 999 | 521 | 52.2% |

Gaps that continue the trend fill more often (63.5%) than gaps that reverse the trend (52.2%). This contradicts the assumption that "reversal gaps fill more."

---

## 6. Gap-Up vs Gap-Down

| | Events | Avg OC Return | Avg Fill % | Filled |
|--|--------|--------------|-----------|--------|
| Gap-Up | 1,463 | +0.035% | 79.4% | 63.0% |
| Gap-Down | 1,260 | −0.052% | 80.4% | 64.9% |

Gap-down days fill slightly more often (64.9% vs 63.0%). Both directions see ~80% average fill percentage (including partial fills).

---

## 7. What Correlates with Next Day's Return?

| Factor | Correlation (r) |
|--------|----------------|
| Today's gap size | **−0.103** |
| Today's return | −0.053 |
| Today's volume vs average | −0.039 |
| Today's range | +0.039 |

Gap size has the strongest (negative) correlation with next day's return: larger gaps today predict lower returns tomorrow.

---

## 8. Stock Personalities

### Most Volatile (Highest Avg Daily Range)
| Stock | Avg Range | Avg Gap | Gap Fill % |
|-------|-----------|---------|-----------|
| ADANIENT | 3.21% | 0.94% | 57.8% |
| SHRIRAMFIN | 3.04% | 1.15% | 39.6% |
| TRENT | 2.99% | 0.87% | 47.4% |
| BPCL | 2.85% | 1.23% | 36.6% |
| BAJAJHLDNG | 2.79% | 0.66% | 48.8% |

### Most Stable (Lowest Avg Daily Range)
| Stock | Avg Range | Avg Gap | Gap Fill % |
|-------|-----------|---------|-----------|
| ITC | 1.70% | 0.43% | 52.9% |
| RELIANCE | 1.99% | 0.68% | 64.1% |
| ICICIBANK | 2.00% | 0.68% | 38.5% |
| BRITANNIA | 2.05% | 0.51% | 53.3% |
| CIPLA | 2.06% | 0.52% | 67.5% |

### Best Gap Fill Stocks
| Stock | Fill Rate |
|-------|-----------|
| ONGC | 79.3% |
| NESTLEIND | 76.7% |
| BHARTIARTL | 75.6% |
| NTPC | 74.4% |
| COALINDIA | 73.1% |

### Worst Gap Fill Stocks
| Stock | Fill Rate |
|-------|-----------|
| LT | 33.3% |
| BPCL | 36.6% |
| INDUSINDBK | 38.1% |
| ICICIBANK | 38.5% |
| M&M | 39.1% |

---

## 9. Outliers

### Largest Gap-Ups (all unfilled)
| Stock | Date | Gap |
|-------|------|-----|
| ADANIENT | 2026-04-08 | +6.26% |
| ADANIPORTS | 2026-04-08 | +6.08% |
| LT | 2026-04-08 | +6.04% |
| HINDALCO | 2026-04-15 | +5.90% |
| BPCL | 2026-04-08 | +5.78% |

### Largest Gap-Downs
| Stock | Date | Gap | Filled? |
|-------|------|-----|---------|
| HDFCBANK | 2026-03-19 | −8.66% | No |
| HCLTECH | 2026-04-22 | −6.68% | No |
| COALINDIA | 2026-05-27 | −6.36% | Yes |
| WIPRO | 2026-06-05 | −6.26% | No |
| BPCL | 2026-04-13 | −5.04% | No |

---

## 10. Summary Statistics

| Metric | Value |
|--------|-------|
| Total observations | 2,988 stock-day events |
| Average daily return | +0.078% |
| Median daily return | +0.000% |
| Std dev of daily return | 1.871% |
| Average daily range | 2.37% |
| Average absolute gap | 0.72% |
| % positive days | 49.6% |
| % flat days | 3.3% |
| Largest single-day move | 10.5% |
| Largest gap | 8.7% (down) |
| Overall gap fill rate (>0.3%) | 53.7% |
| Overall gap fill rate (>0.5%) | 47.7% |
| Best correlation with next day | Gap size (r = −0.10) |

---

*Generated from real yfinance data. No fabricated numbers. No strategy assumptions. Just what the data says.*
