# RSI Regime Gap Trader — Nifty 50

Automated paper trader for Nifty 50 gap-filling strategy, driven by RSI regime awareness.

## Core Insight

RSI regime overrides day-of-week. The day-wise strategy works for normal (RSI 30-70) stocks only:
- **RSI < 30**: SHORT gap-ups, SKIP gap-downs (downtrend, gap fills are bull traps)
- **RSI > 70**: LONG gap-downs, SKIP gap-ups (uptrend, momentum survives the fill)
- **RSI 30-70**: Use day-wise rules (Wed gap-down best, Thu gap-up short, etc.)

## Files

| File | Purpose |
|------|---------|
| `paper_trader/trader.py` | Daily paper trader — runs via GitHub Actions |
| `paper_trader/ledger.json` | Trade history |
| `data.json` | Historical data (49 Nifty stocks, Mar–Jun 2026) |
| `findings.md` | Full data analysis (14 sections) |
| `strategy-day-wise.md` | Day-wise playbook with RSI regime rules |

## Data Sources

- yfinance for Nifty 50 stocks
- 62 trading days, 2,988 gap events
- Covers Mar 16 – Jun 15 2026
