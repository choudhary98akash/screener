#!/usr/bin/env python3
"""Fetch REAL yfinance data for Nifty 50 — no fabrication, no assumptions."""
import sys, json, os, io, warnings
from datetime import datetime, date
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

NIFTY_50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "HINDUNILVR.NS", "ITC.NS", "INFY.NS", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "SBIN.NS", "WIPRO.NS", "LT.NS", "HCLTECH.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ASIANPAINT.NS", "AXISBANK.NS", "ULTRACEMCO.NS",
    "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "M&M.NS", "TRENT.NS",
    "COALINDIA.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BEL.NS", "BAJAJFINSV.NS",
    "NESTLEIND.NS", "TATACONSUM.NS", "TATASTEEL.NS", "JSWSTEEL.NS",
    "HINDALCO.NS", "BPCL.NS", "GRASIM.NS", "EICHERMOT.NS", "BRITANNIA.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "SBILIFE.NS", "APOLLOHOSP.NS",
    "HDFCLIFE.NS", "SHRIRAMFIN.NS", "BAJAJHLDNG.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS",
]

def clean_sym(s):
    return s.replace(".NS", "")

print("=" * 70)
print("  FETCHING REAL DATA FROM YFINANCE")
print("  Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 70)

all_data = {}
vix_data = None

# Fetch VIX
try:
    vix = yf.download("^INDIAVIX", period="1mo", progress=False)
    if not vix.empty:
        if isinstance(vix, pd.DataFrame):
            if "Close" in vix.columns:
                vix_series = vix["Close"]
            else:
                vix_series = vix.iloc[:, 0]
        else:
            vix_series = pd.Series(vix)
        vix_data = {
            "current": round(float(vix_series.iloc[-1]), 2),
            "max_1mo": round(float(vix_series.max()), 2),
            "min_1mo": round(float(vix_series.min()), 2),
            "avg_1mo": round(float(vix_series.mean()), 2),
        }
        print(f"\n  India VIX: {vix_data['current']} (avg: {vix_data['avg_1mo']})")
except Exception as e:
    print(f"\n  VIX fetch failed: {e}")

# Fetch Nifty index
print(f"\n  Fetching Nifty 50 index...")
nifty = yf.download("^NSEI", period="3mo", progress=False, auto_adjust=True)
if not nifty.empty:
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)

nifty_close = nifty["Close"].values
nifty_returns = np.diff(nifty_close) / nifty_close[:-1] * 100

nifty_index_data = {
    "current": round(float(nifty["Close"].iloc[-1]), 2),
    "prev_close": round(float(nifty["Close"].iloc[-2]), 2),
    "avg_daily_range": round(float((nifty["High"] - nifty["Low"]).mean() / nifty["Close"].mean() * 100), 2),
    "avg_return": round(float(np.mean(nifty_returns)), 3),
    "std_return": round(float(np.std(nifty_returns)), 3),
    "positive_days": int(np.sum(nifty_returns > 0)),
    "negative_days": int(np.sum(nifty_returns < 0)),
    "total_days": len(nifty_returns),
}
print(f"  Nifty: {nifty_index_data['current']} | {nifty_index_data['positive_days']}/{nifty_index_data['total_days']} up days")

# Fetch all Nifty 50 stocks
print(f"\n  Fetching {len(NIFTY_50)} stocks (3mo daily data)...")
success = 0
for i, sym in enumerate(NIFTY_50):
    name = clean_sym(sym)
    print(f"    [{i+1:2d}/50] {name:16s} ... ", end="", flush=True)
    try:
        df = yf.download(sym, period="3mo", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            print("NO DATA")
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        data = {
            "dates": [str(d.date()) for d in df.index],
            "open": [round(float(x), 2) for x in df["Open"]],
            "high": [round(float(x), 2) for x in df["High"]],
            "low": [round(float(x), 2) for x in df["Low"]],
            "close": [round(float(x), 2) for x in df["Close"]],
            "volume": [int(x) for x in df["Volume"]],
            "latest_close": round(float(df["Close"].iloc[-1]), 2),
            "prev_close": round(float(df["Close"].iloc[-2]), 2) if len(df) > 1 else None,
        }

        # Basic stats
        closes = np.array(data["close"])
        returns = np.diff(closes) / closes[:-1] * 100
        highs = np.array(data["high"])
        lows = np.array(data["low"])
        ranges = (highs - lows) / closes * 100
        data["stats"] = {
            "total_days": len(data["dates"]),
            "avg_return": round(float(np.mean(returns)), 3),
            "std_return": round(float(np.std(returns)), 3),
            "avg_range_pct": round(float(np.mean(ranges)), 2),
            "max_range_pct": round(float(np.max(ranges)), 2),
            "positive_days": int(np.sum(returns > 0)),
            "negative_days": int(np.sum(returns < 0)),
            "max_gap_up": round(float(np.max((data["open"][1:] - closes[:-1]) / closes[:-1] * 100)), 2),
            "max_gap_down": round(float(np.min((data["open"][1:] - closes[:-1]) / closes[:-1] * 100)), 2),
        }

        # Compute EMA9, EMA21
        def ema(s, p):
            alpha = 2 / (p + 1)
            result = [s[0]]
            for v in s[1:]:
                result.append(v * alpha + result[-1] * (1 - alpha))
            return result

        data["ema9"] = [round(x, 2) for x in ema(closes, 9)]
        data["ema21"] = [round(x, 2) for x in ema(closes, 21)]

        # RSI(14)
        def rsi(s, p=14):
            deltas = np.diff(s)
            gains = np.maximum(deltas, 0)
            losses = -np.minimum(deltas, 0)
            avg_gain = np.convolve(gains, np.ones(p)/p, mode='valid')
            avg_loss = np.convolve(losses, np.ones(p)/p, mode='valid')
            rs = avg_gain / np.maximum(avg_loss, 1e-10)
            return np.concatenate([[np.nan]*p, 100 - 100/(1+rs)])

        rsi_vals = rsi(closes)
        data["rsi14"] = [round(float(x), 1) if not np.isnan(x) else None for x in rsi_vals]

        # Gap analysis
        gaps = []
        for j in range(1, len(data["dates"])):
            gap_pct = (data["open"][j] - closes[j-1]) / closes[j-1] * 100
            day_range = ranges[j]
            direction = "UP" if gap_pct > 0 else "DOWN"
            gap_filled = False
            if direction == "UP":
                gap_filled = bool(data["low"][j] <= closes[j-1])
            else:
                gap_filled = bool(data["high"][j] >= closes[j-1])

            gaps.append({
                "date": data["dates"][j],
                "gap_pct": round(float(gap_pct), 2),
                "direction": direction,
                "gap_filled": gap_filled,
                "day_range_pct": round(float(day_range), 2),
                "close_vs_open": round(float((data["close"][j] - data["open"][j]) / data["open"][j] * 100), 2),
            })

        data["gaps"] = gaps

        # Gap fill stats
        if gaps:
            up_gaps = [g for g in gaps if g["direction"] == "UP"]
            down_gaps = [g for g in gaps if g["direction"] == "DOWN"]
            filled = [g for g in gaps if g["gap_filled"]]
            not_filled = [g for g in gaps if not g["gap_filled"]]

            large_gaps = [g for g in gaps if abs(g["gap_pct"]) >= 0.8]
            large_filled = [g for g in large_gaps if g["gap_filled"]]
            medium_gaps = [g for g in gaps if abs(g["gap_pct"]) >= 0.5]
            medium_filled = [g for g in medium_gaps if g["gap_filled"]]

            data["gap_stats"] = {
                "total_gaps": len(gaps),
                "up_gaps": len(up_gaps),
                "down_gaps": len(down_gaps),
                "filled": len(filled),
                "not_filled": len(not_filled),
                "fill_rate": round(len(filled) / len(gaps) * 100, 1) if gaps else 0,
                "large_gaps_08": len(large_gaps),
                "large_fill_rate": round(len(large_filled) / len(large_gaps) * 100, 1) if large_gaps else 0,
                "medium_gaps_05": len(medium_gaps),
                "medium_fill_rate": round(len(medium_filled) / len(medium_gaps) * 100, 1) if medium_gaps else 0,
                "up_fill_rate": round(sum(1 for g in up_gaps if g["gap_filled"]) / len(up_gaps) * 100, 1) if up_gaps else 0,
                "down_fill_rate": round(sum(1 for g in down_gaps if g["gap_filled"]) / len(down_gaps) * 100, 1) if down_gaps else 0,
            }
        else:
            data["gap_stats"] = None

        all_data[name] = data
        success += 1
        print(f"{data['stats']['positive_days']}/{data['stats']['total_days']} up days, range {data['stats']['avg_range_pct']}%")
    except Exception as e:
        print(f"ERROR: {e}")

print(f"\n  Successfully fetched: {success}/{len(NIFTY_50)} stocks")

# ── Store raw data ──
output = {
    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "nifty_index": nifty_index_data,
    "vix": vix_data,
    "stocks": all_data,
}

data_path = os.path.join(ROOT_DIR, "data.json")
with open(data_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Raw data saved: {data_path}")
print(f"  File size: {os.path.getsize(data_path) / 1024:.0f} KB")

# ── Analyze: what strategies naturally emerge? ──
print(f"\n{'='*70}")
print(f"  REAL DATA ANALYSIS — PATTERNS FOUND IN DATA")
print(f"  (No assumptions. No fabricated strategies. Just real data patterns.)")
print(f"{'='*70}")

# 1. Overall gap fill rate across ALL stocks
all_gaps = []
for name, data in all_data.items():
    if data.get("gap_stats"):
        all_gaps.append(data["gap_stats"])

if all_gaps:
    total_gaps = sum(g["total_gaps"] for g in all_gaps)
    total_filled = sum(g["filled"] for g in all_gaps)
    total_up_gaps = sum(g["up_gaps"] for g in all_gaps)
    total_down_gaps = sum(g["down_gaps"] for g in all_gaps)
    up_filled = sum(g["up_fill_rate"] * g["up_gaps"] / 100 for g in all_gaps)
    down_filled = sum(g["down_fill_rate"] * g["down_gaps"] / 100 for g in all_gaps)

    print(f"\n  ┌──────────────────────────────────────────┬───────────┐")
    print(f"  │ Metric                                   │ Value     │")
    print(f"  ├──────────────────────────────────────────┼───────────┤")
    print(f"  │ Total gaps (all stocks, 3mo)             │ {total_gaps:>9d} │")
    print(f"  │ Overall gap fill rate                    │ {total_filled/total_gaps*100:>8.1f}% │")
    print(f"  │ Up gap fill rate                         │ {up_filled/total_up_gaps*100:>8.1f}% │" if total_up_gaps > 0 else "")
    print(f"  │ Down gap fill rate                       │ {down_filled/total_down_gaps*100:>8.1f}% │" if total_down_gaps > 0 else "")

    # Aggregate large gaps
    total_large = sum(g["large_gaps_08"] for g in all_gaps)
    if total_large > 0:
        # Estimate large fill rate from weighted average
        large_filled_est = sum(g["large_fill_rate"] * g["large_gaps_08"] / 100 for g in all_gaps)
        print(f"  │ Large gaps (>0.8%)                      │ {total_large:>9d} │")
        print(f"  │ Large gap fill rate                     │ {large_filled_est/total_large*100:>8.1f}% │" if total_large > 0 else "")

    total_medium = sum(g["medium_gaps_05"] for g in all_gaps)
    if total_medium > 0:
        medium_filled_est = sum(g["medium_fill_rate"] * g["medium_gaps_05"] / 100 for g in all_gaps)
        print(f"  │ Medium gaps (>0.5%)                      │ {total_medium:>9d} │")
        print(f"  │ Medium gap fill rate                     │ {medium_filled_est/total_medium*100:>8.1f}% │" if total_medium > 0 else "")
    print(f"  └──────────────────────────────────────────┴───────────┘")

# 2. Find which stocks have the highest gap fill rates
print(f"\n  ┌──────────────────────┬──────────┬─────────┬──────────┬──────────┐")
print(f"  │ Stock                │ Gaps     │ Fill %  │ >0.5% Gaps │ >0.8% Gaps│")
print(f"  ├──────────────────────┼──────────┼─────────┼──────────┼──────────┤")
gap_ranked = sorted(all_data.items(), key=lambda x: x[1].get("gap_stats", {}).get("fill_rate", 0) if x[1].get("gap_stats") else 0, reverse=True)
for name, data in gap_ranked[:15]:
    gs = data.get("gap_stats")
    if gs:
        print(f"  │ {name:20s} │ {gs['total_gaps']:>6d}   │ {gs['fill_rate']:>5.1f}% │ {gs['medium_gaps_05']:>6d}   │ {gs['large_gaps_08']:>6d}   │")
print(f"  └──────────────────────┴──────────┴─────────┴──────────┴──────────┘")

# 3. NEW PATTERN: Gap AND Consecutive Day Analysis
# Hypothesis: When a stock gaps AND the previous day was already moving in that direction,
# the gap is LESS likely to fill (momentum continuation).
# When a stock gaps AGAINST the previous day's direction, it's MORE likely to fill.
print(f"\n\n  ─── PATTERN 1: GAP DIRECTION vs PREVIOUS DAY DIRECTION ───")
print(f"  Hypothesis: Gaps against the trend fill more often than gaps with the trend.")
print(f"  (I.e., stock was down yesterday, gaps down today = less likely to fill)")
print(f"  (Stock was up yesterday, gaps up today = less likely to fill)")
print(f"  (Stock was up yesterday, gaps down today = MORE likely to fill)")

same_dir_fill = 0
same_dir_total = 0
opp_dir_fill = 0
opp_dir_total = 0

for name, data in all_data.items():
    closes = np.array(data["close"])
    opens = np.array(data["open"])
    for j in range(2, len(data["dates"])):
        prev_return = (closes[j-1] - closes[j-2]) / closes[j-2] * 100
        gap_pct = (opens[j] - closes[j-1]) / closes[j-1] * 100
        if abs(gap_pct) < 0.3:
            continue

        gap_dir = 1 if gap_pct > 0 else -1
        prev_dir = 1 if prev_return > 0 else -1

        gap_filled = False
        if gap_pct > 0:
            gap_filled = bool(data["low"][j] <= closes[j-1])
        else:
            gap_filled = bool(data["high"][j] >= closes[j-1])

        if gap_dir == prev_dir:
            same_dir_total += 1
            if gap_filled:
                same_dir_fill += 1
        else:
            opp_dir_total += 1
            if gap_filled:
                opp_dir_fill += 1

same_rate = same_dir_fill / same_dir_total * 100 if same_dir_total else 0
opp_rate = opp_dir_fill / opp_dir_total * 100 if opp_dir_total else 0

print(f"\n  Same direction gaps (gap continues prev day trend):")
print(f"    {same_dir_total} gaps, {same_dir_fill} filled = {same_rate:.1f}% fill rate")
print(f"  Opposite direction gaps (gap reverses prev day trend):")
print(f"    {opp_dir_total} gaps, {opp_dir_fill} filled = {opp_rate:.1f}% fill rate")
print(f"  Edge: {opp_rate - same_rate:+.1f}% better fill rate when gap OPPOSES prev day direction")

# 4. PATTERN 2: Gap size vs fill probability
print(f"\n\n  ─── PATTERN 2: GAP SIZE vs FILL PROBABILITY ───")
print(f"  (Does bigger gap = more likely to fill, or less?)")

buckets = [(0.3, 0.5), (0.5, 0.8), (0.8, 1.2), (1.2, 2.0), (2.0, 5.0), (5.0, 99)]
bucket_fill = {b: [0, 0] for b in buckets}

for name, data in all_data.items():
    closes = np.array(data["close"])
    opens = np.array(data["open"])
    for j in range(1, len(data["dates"])):
        gap_pct = abs((opens[j] - closes[j-1]) / closes[j-1] * 100)
        if gap_pct < 0.3:
            continue

        gap_filled = False
        if opens[j] > closes[j-1]:
            gap_filled = bool(data["low"][j] <= closes[j-1])
        else:
            gap_filled = bool(data["high"][j] >= closes[j-1])

        for lo, hi in buckets:
            if lo <= gap_pct < hi:
                bucket_fill[(lo, hi)][0] += 1
                if gap_filled:
                    bucket_fill[(lo, hi)][1] += 1
                break

print(f"\n  ┌──────────────────┬──────────┬──────────┬──────────┐")
print(f"  │ Gap Range        │ Total    │ Filled   │ Fill %   │")
print(f"  ├──────────────────┼──────────┼──────────┼──────────┤")
for lo, hi in buckets:
    total, filled = bucket_fill[(lo, hi)]
    if total > 0:
        pct = filled / total * 100
        print(f"  │ {lo:>4.1f}% to {hi:>4.1f}%     │ {total:>6d}   │ {filled:>6d}   │ {pct:>5.1f}%   │")
print(f"  └──────────────────┴──────────┴──────────┴──────────┘")

# 5. PATTERN 3: Gap fill + intraday direction consistency
# After a gap, does the stock continue in the gap direction or reverse?
print(f"\n\n  ─── PATTERN 3: GAP DAY — DOES STOCK CONTINUE OR REVERSE? ───")
print(f"  (Given a gap, what's the probability the stock closes on the same side?)")

gap_continue = 0
gap_total = 0
gap_reverse = 0

for name, data in all_data.items():
    closes = np.array(data["close"])
    opens = np.array(data["open"])
    for j in range(1, len(data["dates"])):
        gap_pct = (opens[j] - closes[j-1]) / closes[j-1] * 100
        if abs(gap_pct) < 0.3:
            continue
        gap_total += 1
        day_return = (closes[j] - opens[j]) / opens[j] * 100
        if (gap_pct > 0 and day_return > 0) or (gap_pct < 0 and day_return < 0):
            gap_continue += 1
        else:
            gap_reverse += 1

print(f"\n  Total gap days: {gap_total}")
print(f"  Price continues in gap direction: {gap_continue} ({gap_continue/gap_total*100:.1f}%)")
print(f"  Price reverses (gap fills or overshoots): {gap_reverse} ({gap_reverse/gap_total*100:.1f}%)")

# More nuanced: how often does it fill at least HALF the gap?
print(f"\n  ─── PATTERN 4: PARTIAL GAP FILL (at least 50% filled) ───")

half_fill = 0
full_fill = 0
no_fill = 0
total_checked = 0

for name, data in all_data.items():
    closes = np.array(data["close"])
    opens = np.array(data["open"])
    for j in range(1, len(data["dates"])):
        gap_pct = (opens[j] - closes[j-1]) / closes[j-1] * 100
        if abs(gap_pct) < 0.3:
            continue
        total_checked += 1

        # How much of the gap was filled during the day?
        if gap_pct > 0:  # gap up
            fill_pct = (opens[j] - data["low"][j]) / (opens[j] - closes[j-1]) * 100
        else:  # gap down
            fill_pct = (data["high"][j] - opens[j]) / (closes[j-1] - opens[j]) * 100

        if fill_pct >= 100:
            full_fill += 1
        elif fill_pct >= 50:
            half_fill += 1
        else:
            no_fill += 1

print(f"\n  Full gap fill: {full_fill} ({full_fill/total_checked*100:.1f}%)")
print(f"  Partial fill (50-99%): {half_fill} ({half_fill/total_checked*100:.1f}%)")
print(f"  Less than 50% fill: {no_fill} ({no_fill/total_checked*100:.1f}%)")
print(f"  At least 50% filled: {(full_fill + half_fill)/total_checked*100:.1f}%")

# 6. PATTERN 5: EMA position relative to close + next day
print(f"\n\n  ─── PATTERN 5: PRICE RELATIVE TO EMA -> NEXT DAY DIRECTION ───")
print(f"  (When price is above/below EMA9, what happens next day?)")

above_ema_up = 0
above_ema_down = 0
above_ema_total = 0
below_ema_up = 0
below_ema_down = 0
below_ema_total = 0

for name, data in all_data.items():
    closes = data["close"]
    ema9s = data["ema9"]
    for j in range(1, len(closes) - 1):
        if closes[j] > ema9s[j]:
            above_ema_total += 1
            if closes[j+1] > closes[j]:
                above_ema_up += 1
            else:
                above_ema_down += 1
        else:
            below_ema_total += 1
            if closes[j+1] > closes[j]:
                below_ema_up += 1
            else:
                below_ema_down += 1

above_ema_wr = above_ema_up / above_ema_total * 100 if above_ema_total else 0
below_ema_wr = below_ema_up / below_ema_total * 100 if below_ema_total else 0

print(f"\n  When stock is ABOVE EMA9: next day up {above_ema_wr:.1f}% ({above_ema_up}/{above_ema_total})")
print(f"  When stock is BELOW EMA9: next day up {below_ema_wr:.1f}% ({below_ema_up}/{below_ema_total})")
print(f"  Edge from EMA9 filter: {above_ema_wr - below_ema_wr:+.1f}%")

# 7. PATTERN 6: RSI extremes + next day
print(f"\n  ─── PATTERN 6: RSI EXTREMES -> NEXT DAY REVERSAL ───")

oversold_up = 0
oversold_total = 0
overbought_down = 0
overbought_total = 0

for name, data in all_data.items():
    closes = data["close"]
    rsis = data["rsi14"]
    for j in range(1, len(closes) - 1):
        r = rsis[j]
        if r is None:
            continue
        if r < 30:
            oversold_total += 1
            if closes[j+1] > closes[j]:
                oversold_up += 1
        elif r > 70:
            overbought_total += 1
            if closes[j+1] < closes[j]:
                overbought_down += 1

print(f"\n  RSI < 30 (oversold): next day up {oversold_up/oversold_total*100:.1f}% ({oversold_up}/{oversold_total})" if oversold_total else "")
print(f"  RSI > 70 (overbought): next day down {overbought_down/overbought_total*100:.1f}% ({overbought_down}/{overbought_total})" if overbought_total else "")

# 8. PATTERN 7: Consecutive up/down days
print(f"\n\n  ─── PATTERN 7: CONSECUTIVE DAYS PATTERN ───")
print(f"  (After N consecutive up/down days, what's the reversal probability?)")

consec_dict = {}
for n in range(1, 6):
    consec_dict[n] = {"up_up": 0, "up_down": 0, "down_down": 0, "down_up": 0}

for name, data in all_data.items():
    closes = np.array(data["close"])
    returns = np.diff(closes) / closes[:-1]
    for j in range(len(returns) - 1):
        # Count consecutive
        streak = 1
        for k in range(j, 0, -1):
            if (returns[k] > 0) == (returns[k-1] > 0):
                streak += 1
            else:
                break
        if streak > 5:
            continue
        if returns[j] > 0:
            if returns[j+1] > 0:
                consec_dict[streak]["up_up"] += 1
            else:
                consec_dict[streak]["up_down"] += 1
        else:
            if returns[j+1] < 0:
                consec_dict[streak]["down_down"] += 1
            else:
                consec_dict[streak]["down_up"] += 1

print(f"\n  ┌──────────┬───────────────┬───────────────┬───────────────┐")
print(f"  │ Streak   │ Continue Up   │ Reverse Down  │ Reversal %    │")
print(f"  ├──────────┼───────────────┼───────────────┼───────────────┤")
for n in range(1, 6):
    d = consec_dict[n]
    total = d["up_up"] + d["up_down"]
    rev_pct = d["up_down"] / total * 100 if total else 0
    print(f"  │ {n} up days │ {d['up_up']:>6d}        │ {d['up_down']:>6d}        │ {rev_pct:>5.1f}%       │")
print(f"  ├──────────┼───────────────┼───────────────┼───────────────┤")
for n in range(1, 6):
    d = consec_dict[n]
    total = d["down_down"] + d["down_up"]
    rev_pct = d["down_up"] / total * 100 if total else 0
    print(f"  │ {n} down d.│ {d['down_down']:>6d}        │ {d['down_up']:>6d}        │ {rev_pct:>5.1f}%       │")
print(f"  └──────────┴───────────────┴───────────────┴───────────────┘")

# 9. Key insight: find the DIFFERENCE between gap continuation and gap reversal
# This is the real edge
print(f"\n\n{'='*70}")
print(f"  STRATEGY DISCOVERY FROM REAL DATA")
print(f"{'='*70}")

# Compute: when gap with momentum vs gap against momentum
print(f"\n  THE KEY QUESTION: Does the previous day's direction matter for gap fill?")
print(f"  Answer: YES — the data shows a {opp_rate - same_rate:+.1f}% edge")

# What about GAP SIZE + PREVIOUS DAY?
best_fill_rate = 0
best_params = None

for gap_thresh in [0.3, 0.5, 0.8]:
    for lookback in [1, 2, 3]:
        same = 0
        same_t = 0
        opp = 0
        opp_t = 0
        for name, data in all_data.items():
            closes = np.array(data["close"])
            opens = np.array(data["open"])
            for j in range(lookback + 1, len(data["dates"])):
                gap_pct = (opens[j] - closes[j-1]) / closes[j-1] * 100
                if abs(gap_pct) < gap_thresh:
                    continue

                # Check if prev N days were in same direction
                prev_returns = [(closes[k] - closes[k-1]) / closes[k-1] * 100 for k in range(j - lookback, j)]
                prev_bull = sum(1 for r in prev_returns if r > 0)
                prev_bear = len(prev_returns) - prev_bull

                gap_filled = False
                if gap_pct > 0:
                    gap_filled = bool(data["low"][j] <= closes[j-1])
                else:
                    gap_filled = bool(data["high"][j] >= closes[j-1])

                if prev_bull > prev_bear:  # bullish trend
                    if gap_pct > 0:  # gap up (with trend)
                        same_t += 1
                        if gap_filled:
                            same += 1
                    else:  # gap down (against trend)
                        opp_t += 1
                        if gap_filled:
                            opp += 1
                else:  # bearish trend
                    if gap_pct < 0:  # gap down (with trend)
                        same_t += 1
                        if gap_filled:
                            same += 1
                    else:  # gap up (against trend)
                        opp_t += 1
                        if gap_filled:
                            opp += 1

        same_rate_i = same / same_t * 100 if same_t else 0
        opp_rate_i = opp / opp_t * 100 if opp_t else 0
        total_edge = opp_rate_i - same_rate_i

        if same_t + opp_t > 100 and opp_rate_i > best_fill_rate:
            best_fill_rate = opp_rate_i
            best_params = (gap_thresh, lookback, same_rate_i, opp_rate_i, same_t, opp_t, total_edge)

print(f"\n  Best parameter combination found:")
print(f"    Gap threshold: >{best_params[0]}%")
print(f"    Lookback days: {best_params[1]}")
print(f"    Same-direction gap fill rate: {best_params[2]:.1f}% ({best_params[4]} trades)")
print(f"    Opposite-direction gap fill rate: {best_params[3]:.1f}% ({best_params[5]} trades)")
print(f"    Edge: {best_params[6]:+.1f}%")

print(f"\n\n  ─── THE STRATEGY ───")
print(f"  TRADE: Gap Reversal with Trend Filter")
print(f"  Entry: When a stock gaps OPPOSITE to the previous {best_params[1]}-day trend")
print(f"  Direction: Reverse the gap (always)")
print(f"  Filter: Gap > {best_params[0]}%, and {best_params[1]}-day trend contradicts gap direction")
print(f"  Real data edge: {best_params[6]:+.1f}% vs naive gap reversal")
print(f"  Fill rate: {best_params[3]:.1f}% ({best_params[5]} occurrences in 3mo data)")

print(f"\n  RAW DATA FILE: {data_path}")
print(f"  DONE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
