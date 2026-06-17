#!/usr/bin/env python
"""
Completely fresh exploration — no gap strategy, no day-of-week, no RSI regime bias.
Looking for ONE hidden trade that makes money.
"""
import json, itertools, sys
from collections import defaultdict
import numpy as np

data = json.load(open('data.json'))
stocks = list(data['stocks'].keys())
alldates = data['stocks'][stocks[0]]['dates']
ndates = len(alldates)

# Build a unified dataframe for all stocks
records = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(len(s['dates'])):
        rec = {
            'sym': sym,
            'date': s['dates'][i],
            'open': s['open'][i],
            'high': s['high'][i],
            'low': s['low'][i],
            'close': s['close'][i],
            'volume': s['volume'][i],
        }
        if s.get('ema9') and i < len(s['ema9']):
            rec['ema9'] = s['ema9'][i]
        if s.get('ema21') and i < len(s['ema21']):
            rec['ema21'] = s['ema21'][i]
        if s.get('rsi14') and i < len(s['rsi14']):
            rec['rsi14'] = s['rsi14'][i]
        records.append(rec)

print(f"Total records: {len(records)}")

# Convert to numpy arrays for fast computation
syms = np.array([r['sym'] for r in records])
dates_arr = np.array([r['date'] for r in records])
opens = np.array([r['open'] for r in records])
highs = np.array([r['high'] for r in records])
lows = np.array([r['low'] for r in records])
closes = np.array([r['close'] for r in records])
volumes = np.array([r['volume'] for r in records], dtype=float)
ema9s = np.array([r.get('ema9', np.nan) or r['close'] for r in records], dtype=float)
ema21s = np.array([r.get('ema21', np.nan) or r['close'] for r in records], dtype=float)
rsis = np.array([r.get('rsi14', np.nan) or 50 for r in records], dtype=float)

# Compute returns
today_ret = np.array([(c - o) / o * 100 for o, c in zip(opens, closes)])
day_range = np.array([(h - l) / l * 100 for h, l in zip(highs, lows)])
upper_wick = np.array([(h - c) / h * 100 if h > c else 0 for h, c in zip(highs, closes)])
lower_wick = np.array([(c - l) / l * 100 if c > l else 0 for c, l in zip(closes, lows)])

# ============================================================
# PERSPECTIVE 1: The "Inside Day" + Low Vol Squeeze
# ============================================================
print("\n=== PERSPECTIVE 1: Inside Day Squeeze ===")
# An inside day is when high < prev high AND low > prev low
# Combined with low range = potential breakout
inside_results = []
for i in range(1, ndates):
    day_idx = {d:idx for idx,d in enumerate(alldates)}
    for sym in stocks:
        s = data['stocks'][sym]
        if i >= len(s['dates']): continue
        prev_h = s['high'][i-1] if i-1 < len(s['high']) else 0
        prev_l = s['low'][i-1] if i-1 < len(s['low']) else 0
        cur_h = s['high'][i]
        cur_l = s['low'][i]
        cur_o = s['open'][i]
        cur_c = s['close'][i]
        range_pct = (cur_h - cur_l) / cur_l * 100
        
        inside = cur_h < prev_h and cur_l > prev_l
        if inside and range_pct < 2.0:
            # Next day's return
            if i + 1 < len(s['dates']):
                nxt_c = s['close'][i+1]
                nxt_o = s['open'][i+1]
                nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
                inside_results.append({
                    'sym': sym, 'date': s['dates'][i],
                    'range': round(range_pct, 2),
                    'next_ret': round(nxt_ret, 2),
                    'trend': 'UP' if nxt_ret > 0 else 'DOWN'
                })

if inside_results:
    n = len(inside_results)
    ups = sum(1 for r in inside_results if r['next_ret'] > 0)
    avg_ret = np.mean([r['next_ret'] for r in inside_results])
    best = max(inside_results, key=lambda r: r['next_ret'])
    worst = min(inside_results, key=lambda r: r['next_ret'])
    print(f"  Inside days found: {n}")
    print(f"  Next day positive: {ups}/{n} ({ups/n*100:.1f}%)")
    print(f"  Avg next ret: {avg_ret:.3f}%")
    print(f"  Best: {best['sym']} on {best['date']} -> {best['next_ret']:+.2f}%")
    print(f"  Worst: {worst['sym']} on {worst['date']} -> {worst['next_ret']:+.2f}%")

# ============================================================
# PERSPECTIVE 2: Consecutive Green/Red Days (not gaps)
# ============================================================
print("\n=== PERSPECTIVE 2: Streak Detection ===")
# If a stock has been red 3+ days, what happens next?
streak_results = defaultdict(list)
for sym in stocks:
    s = data['stocks'][sym]
    streak = 0
    streak_dir = None
    for i in range(len(s['dates'])):
        o, c = s['open'][i], s['close'][i]
        ret = (c - o) / o * 100
        is_up = ret > 0
        is_down = ret < 0
        
        if is_up:
            if streak_dir == 'UP':
                streak += 1
            else:
                streak = 1
                streak_dir = 'UP'
        elif is_down:
            if streak_dir == 'DOWN':
                streak += 1
            else:
                streak = 1
                streak_dir = 'DOWN'
        else:
            streak = 0
            streak_dir = None
        
        if i + 1 < len(s['dates']):
            nxt_o = s['open'][i+1]
            nxt_c = s['close'][i+1]
            nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
            if streak >= 3 and streak_dir:
                streak_results[f"{streak}d {streak_dir}"].append({
                    'sym': sym, 'date': s['dates'][i],
                    'streak': streak, 'dir': streak_dir,
                    'next_ret': round(nxt_ret, 2)
                })

for key, results in sorted(streak_results.items()):
    n = len(results)
    ups = sum(1 for r in results if r['next_ret'] > 0)
    avg = np.mean([r['next_ret'] for r in results])
    best = max(results, key=lambda r: r['next_ret'])
    print(f"  {key}: {n} events, {ups/n*100:.1f}% pos, avg={avg:.3f}%, best={best['sym']} {best['date']} {best['next_ret']:+.2f}%")

# ============================================================
# PERSPECTIVE 3: The "Close Above Open × 3 Days" Pattern
# ============================================================
print("\n=== PERSPECTIVE 3: 3-Day Close-Above-Open Pattern ===")
results_3up = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(2, len(s['dates']) - 1):
        r1 = (s['close'][i-2] - s['open'][i-2]) / s['open'][i-2] * 100
        r2 = (s['close'][i-1] - s['open'][i-1]) / s['open'][i-1] * 100
        r3 = (s['close'][i] - s['open'][i]) / s['open'][i] * 100
        nxt_o = s['open'][i+1]
        nxt_c = s['close'][i+1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
        results_3up.append({
            'sym': sym, 'date': s['dates'][i],
            'd1': round(r1, 2), 'd2': round(r2, 2), 'd3': round(r3, 2),
            'nxt': round(nxt_ret, 2)
        })

# Split by pattern
for label, cond in [("All", lambda r: True),
                     ("3 green days", lambda r: r['d1'] > 0 and r['d2'] > 0 and r['d3'] > 0),
                     ("3 red days", lambda r: r['d1'] < 0 and r['d2'] < 0 and r['d3'] < 0),
                     ("Green, green, red", lambda r: r['d1'] > 0 and r['d2'] > 0 and r['d3'] < 0),
                     ("Red, red, green", lambda r: r['d1'] < 0 and r['d2'] < 0 and r['d3'] > 0)]:
    subset = [r for r in results_3up if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt'] > 0)
        avg = np.mean([r['nxt'] for r in subset])
        print(f"  {label}: {n} events, {ups/n*100:.1f}% pos, avg={avg:.3f}%")

# ============================================================
# PERSPECTIVE 4: Opening Price as Signal (not just gap)
# ============================================================
print("\n=== PERSPECTIVE 4: Open Relative to Previous Day ===")
# Open near previous high, open near previous low, etc.
open_signals = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(1, len(s['dates']) - 1):
        prev_h = s['high'][i-1]
        prev_l = s['low'][i-1]
        prev_c = s['close'][i-1]
        prev_range = prev_h - prev_l
        cur_o = s['open'][i]
        cur_c = s['close'][i]
        cur_h = s['high'][i]
        cur_l = s['low'][i]
        nxt_o = s['open'][i+1]
        nxt_c = s['close'][i+1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
        
        if prev_range == 0: continue
        
        # Where does open fall in prev day's range? (0 = at low, 1 = at high)
        open_pos = (cur_o - prev_l) / prev_range
        
        open_signals.append({
            'sym': sym, 'date': s['dates'][i],
            'open_pos': round(open_pos, 3),
            'cur_ret': round((cur_c - cur_o) / cur_o * 100, 2),
            'nxt_ret': round(nxt_ret, 2)
        })

# Buckets
for label, lo, hi in [("Open below prev low (<0)", -999, 0),
                       ("Open 0-25% of range", 0, 0.25),
                       ("Open 25-50%", 0.25, 0.50),
                       ("Open 50-75%", 0.50, 0.75),
                       ("Open 75-100%", 0.75, 1.0),
                       ("Open above prev high (>1)", 1.0, 999)]:
    subset = [r for r in open_signals if lo <= r['open_pos'] < hi]
    if subset:
        n = len(subset)
        cur_avg = np.mean([r['cur_ret'] for r in subset])
        nxt_ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        nxt_avg = np.mean([r['nxt_ret'] for r in subset])
        best = max(subset, key=lambda r: r['nxt_ret'])
        print(f"  {label}: {n} events, cur_avg={cur_avg:.2f}%, nxt_pos={nxt_ups/n*100:.1f}%, nxt_avg={nxt_avg:.3f}%")

# ============================================================
# PERSPECTIVE 5: Wicks tell the story
# ============================================================
print("\n=== PERSPECTIVE 5: Wick Patterns ===")
wick_data = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(len(s['dates']) - 1):
        o = s['open'][i]
        h = s['high'][i]
        l = s['low'][i]
        c = s['close'][i]
        body = abs(c - o)
        total_range = h - l
        if total_range == 0: continue
        
        upper_wick_pct = (h - max(o, c)) / total_range * 100 if h > max(o,c) else 0
        lower_wick_pct = (min(o, c) - l) / total_range * 100 if l < min(o,c) else 0
        body_pct = body / total_range * 100
        
        nxt_o = s['open'][i+1]
        nxt_c = s['close'][i+1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
        
        # Categorize candle type
        is_bull = c > o
        is_bear = c < o
        
        wick_data.append({
            'sym': sym, 'date': s['dates'][i],
            'body_pct': body_pct,
            'upper_wick': upper_wick_pct,
            'lower_wick': lower_wick_pct,
            'is_bull': is_bull,
            'range': total_range / l * 100,
            'nxt_ret': round(nxt_ret, 2)
        })

for label, cond in [
    ("Hammer (small body, long lower wick)", lambda r: r['body_pct'] < 40 and r['lower_wick'] > 60 and r['is_bull']),
    ("Doji (tiny body)", lambda r: r['body_pct'] < 10),
    ("Marubozu (no wick, big body)", lambda r: r['body_pct'] > 90 and r['range'] > 2),
    ("Shooting star (small body, long upper)", lambda r: r['body_pct'] < 40 and r['upper_wick'] > 60 and r['is_bear']),
]:
    subset = [r for r in wick_data if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        avg = np.mean([r['nxt_ret'] for r in subset])
        best = max(subset, key=lambda r: r['nxt_ret'])
        print(f"  {label}: {n} events, {ups/n*100:.1f}% pos, avg={avg:.3f}%")

# ============================================================
# PERSPECTIVE 6: The Tuesday Effect — but what about ORB?
# ============================================================
print("\n=== PERSPECTIVE 6: First 30-min Range Expansion ===")
# Simulate: if open > prev high (breakout), what happens?
# Or if open < prev low (breakdown)?
breakout_data = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(1, len(s['dates']) - 1):
        prev_h = s['high'][i-1]
        prev_l = s['low'][i-1]
        o = s['open'][i]
        h = s['high'][i]
        l = s['low'][i]
        c = s['close'][i]
        nxt_o = s['open'][i+1]
        nxt_c = s['close'][i+1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
        
        is_breakup = o > prev_h
        is_breakdown = o < prev_l
        # Did it sustain?
        sustained_up = is_breakup and c > o  # opened above prev high AND closed up
        sustained_dn = is_breakdown and c < o  # opened below prev low AND closed down
        
        breakout_data.append({
            'sym': sym, 'date': s['dates'][i],
            'type': 'breakup' if is_breakup else ('breakdown' if is_breakdown else 'inside'),
            'sustained': 'up' if sustained_up else ('down' if sustained_dn else 'no'),
            'cur_ret': round((c-o)/o*100, 2),
            'nxt_ret': round(nxt_ret, 2)
        })

for label, cond in [
    ("Opened above prev high", lambda r: r['type'] == 'breakup'),
    ("Opened below prev low", lambda r: r['type'] == 'breakdown'),
    ("Breakup + closed green", lambda r: r['sustained'] == 'up'),
    ("Breakdown + closed red", lambda r: r['sustained'] == 'down'),
    ("Breakup but closed red (failed)", lambda r: r['type'] == 'breakup' and r['sustained'] in ('no', 'down')),
    ("Breakdown but closed green (failed)", lambda r: r['type'] == 'breakdown' and r['sustained'] in ('no', 'up')),
]:
    subset = [r for r in breakout_data if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        avg = np.mean([r['nxt_ret'] for r in subset])
        best = max(subset, key=lambda r: r['nxt_ret'])
        print(f"  {label}: {n}, {ups/n*100:.1f}% pos, avg={avg:.3f}%")

# ============================================================
# PERSPECTIVE 7: Volume + Price Action — The "Quiet Accumulation"
# ============================================================
print("\n=== PERSPECTIVE 7: Volume Patterns ===")
vol_data = []
for sym in stocks:
    s = data['stocks'][sym]
    vols = np.array(s['volume'], dtype=float)
    for i in range(1, len(s['dates']) - 1):
        if i < 5: continue
        avg_vol_10 = np.mean(vols[max(0,i-10):i])
        if avg_vol_10 == 0: continue
        vol_ratio = s['volume'][i] / avg_vol_10
        o, c, h, l = s['open'][i], s['close'][i], s['high'][i], s['low'][i]
        ret = (c - o) / o * 100
        nxt_o = s['open'][i+1]
        nxt_c = s['close'][i+1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
        
        vol_data.append({
            'sym': sym, 'date': s['dates'][i],
            'vol_ratio': vol_ratio,
            'ret': round(ret, 2),
            'nxt_ret': round(nxt_ret, 2)
        })

# Very specific pattern: low vol + green = quiet accumulation
for label, cond in [
    ("Low vol (<0.5x) + green", lambda r: r['vol_ratio'] < 0.5 and r['ret'] > 0),
    ("Low vol (<0.5x) + red", lambda r: r['vol_ratio'] < 0.5 and r['ret'] < 0),
    ("High vol (>2x) + green", lambda r: r['vol_ratio'] > 2 and r['ret'] > 0),
    ("High vol (>2x) + red", lambda r: r['vol_ratio'] > 2 and r['ret'] < 0),
    ("Expanding vol (1.5x+) + green after 2 red", lambda r: r['vol_ratio'] > 1.5 and r['ret'] > 0),
]:
    subset = [r for r in vol_data if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        avg = np.mean([r['nxt_ret'] for r in subset])
        print(f"  {label}: {n}, {ups/n*100:.1f}% pos, avg={avg:.3f}%")

# ============================================================
# PERSPECTIVE 8: RSI Divergence (hidden)
# ============================================================
print("\n=== PERSPECTIVE 8: RSI Divergence ===")
divergence = []
for sym in stocks:
    s = data['stocks'][sym]
    rsi_vals = s.get('rsi14', [])
    if not rsi_vals: continue
    for i in range(2, len(s['dates']) - 1):
        if i >= len(rsi_vals): continue
        close_i = s['close'][i]
        close_i1 = s['close'][i-1]
        close_i2 = s['close'][i-2]
        rsi_i = rsi_vals[i]
        rsi_i1 = rsi_vals[i-1]
        rsi_i2 = rsi_vals[i-2]
        
        if None in (rsi_i, rsi_i1, rsi_i2): continue
        
        # Bullish divergence: price makes lower low, RSI makes higher low
        if close_i < close_i2 and rsi_i > rsi_i2:
            nxt_o = s['open'][i+1] if i+1 < len(s['open']) else 0
            nxt_c = s['close'][i+1] if i+1 < len(s['close']) else 0
            nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
            divergence.append({
                'sym': sym, 'date': s['dates'][i],
                'type': 'bullish',
                'nxt_ret': round(nxt_ret, 2)
            })
        
        # Bearish divergence: price makes higher high, RSI makes lower high
        if close_i > close_i2 and rsi_i < rsi_i2:
            nxt_o = s['open'][i+1] if i+1 < len(s['open']) else 0
            nxt_c = s['close'][i+1] if i+1 < len(s['close']) else 0
            nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
            divergence.append({
                'sym': sym, 'date': s['dates'][i],
                'type': 'bearish',
                'nxt_ret': round(nxt_ret, 2)
            })

for div_type in ['bullish', 'bearish']:
    subset = [r for r in divergence if r['type'] == div_type]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        avg = np.mean([r['nxt_ret'] for r in subset])
        best = max(subset, key=lambda r: r['nxt_ret'])
        print(f"  {div_type}: {n}, {ups/n*100:.1f}% pos, avg={avg:.3f}%, best={best['sym']} {best['date']} {best['nxt_ret']:+.2f}%")

# ============================================================
# PERSPECTIVE 9: Price vs MA interaction
# ============================================================
print("\n=== PERSPECTIVE 9: MA Crossover / Touch ===")
ma_data = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(1, len(s['dates']) - 1):
        if i >= len(s.get('ema9', [])) or i >= len(s.get('ema21', [])): continue
        ema9 = s['ema9'][i]
        ema21 = s['ema21'][i]
        if ema9 is None or ema21 is None: continue
        close = s['close'][i]
        open_ = s['open'][i]
        
        # Distance from MAs
        dist_9 = (close - ema9) / ema9 * 100
        dist_21 = (close - ema21) / ema21 * 100
        
        # Crossover signal
        prev_ema9 = s['ema9'][i-1] if i-1 < len(s['ema9']) else ema9
        prev_ema21 = s['ema21'][i-1] if i-1 < len(s['ema21']) else ema21
        
        golden_cross = prev_ema9 <= prev_ema21 and ema9 > ema21
        death_cross = prev_ema9 >= prev_ema21 and ema9 < ema21
        
        # Touch and bounce: close touched within 0.1% of MA
        touch_9_bounce = abs(dist_9) < 0.3
        
        nxt_o = s['open'][i+1] if i+1 < len(s['open']) else 0
        nxt_c = s['close'][i+1] if i+1 < len(s['close']) else 0
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
        
        ma_data.append({
            'sym': sym, 'date': s['dates'][i],
            'dist_9': dist_9, 'dist_21': dist_21,
            'golden_cross': golden_cross,
            'death_cross': death_cross,
            'touch_9': touch_9_bounce,
            'nxt_ret': round(nxt_ret, 2)
        })

for label, cond in [
    ("Golden cross (9>21 EMA)", lambda r: r['golden_cross']),
    ("Death cross (9<21 EMA)", lambda r: r['death_cross']),
    ("Touch EMA9 (±0.3%)", lambda r: abs(r['dist_9']) < 0.3),
    ("Price > EMA9 +3% (extended)", lambda r: r['dist_9'] > 3),
    ("Price < EMA9 -3% (compressed)", lambda r: r['dist_9'] < -3),
    ("Price > EMA21 +3% (extended)", lambda r: r['dist_21'] > 3),
    ("Price < EMA21 -3% (compressed)", lambda r: r['dist_21'] < -3),
]:
    subset = [r for r in ma_data if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        avg = np.mean([r['nxt_ret'] for r in subset])
        best = max(subset, key=lambda r: r['nxt_ret'])
        print(f"  {label}: {n}, {ups/n*100:.1f}% pos, avg={avg:.3f}%")

# ============================================================
# PERSPECTIVE 10: The "Consecutive Lower Highs" Pattern
# ============================================================
print("\n=== PERSPECTIVE 10: Consecutive Higher Highs / Lower Lows ===")
hhll_data = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(2, len(s['dates']) - 1):
        hh = s['high'][i] > s['high'][i-1] > s['high'][i-2]
        ll = s['low'][i] < s['low'][i-1] < s['low'][i-2]
        lh = s['high'][i] < s['high'][i-1]  # lower high
        hl = s['low'][i] > s['low'][i-1]    # higher low
        
        nxt_o = s['open'][i+1] if i+1 < len(s['open']) else 0
        nxt_c = s['close'][i+1] if i+1 < len(s['close']) else 0
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
        
        hhll_data.append({
            'sym': sym, 'date': s['dates'][i],
            'hh': hh, 'll': ll, 'lh': lh, 'hl': hl,
            'nxt_ret': round(nxt_ret, 2)
        })

for label, cond in [
    ("3 higher highs (uptrend)", lambda r: r['hh']),
    ("3 lower lows (downtrend)", lambda r: r['ll']),
    ("2 lower highs + 2 higher lows (tightening)", lambda r: r['lh'] and r['hl']),
    ("Higher high + higher low (constructive)", lambda r: not r['hh'] and not r['ll'] and not r['lh'] and r['hl']),
]:
    subset = [r for r in hhll_data if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        avg = np.mean([r['nxt_ret'] for r in subset])
        best = max(subset, key=lambda r: r['nxt_ret'])
        print(f"  {label}: {n}, {ups/n*100:.1f}% pos, avg={avg:.3f}%")

# ============================================================
# PERSPECTIVE 11: The "Relative Strength" angle (cross-sectional)
# ============================================================
print("\n=== PERSPECTIVE 11: Cross-Sectional Relative Strength ===")
# On each day, find the top/bottom performing stocks and see what they do next
from datetime import datetime

rs_data = defaultdict(list)
for date_idx, date in enumerate(alldates):
    day_records = []
    for sym in stocks:
        s = data['stocks'][sym]
        if date_idx < len(s['dates']) and s['dates'][date_idx] == date:
            o, c = s['open'][date_idx], s['close'][date_idx]
            ret = (c - o) / o * 100
            day_records.append({'sym': sym, 'ret': ret, 'date': date})
    
    if not day_records: continue
    day_records.sort(key=lambda r: r['ret'])
    
    # Bottom 5 and top 5
    bottom5 = day_records[:5]
    top5 = day_records[-5:]
    
    for rec in bottom5 + top5:
        sym = rec['sym']
        s = data['stocks'][sym]
        next_idx = date_idx + 1
        if next_idx < len(s['dates']) and s['dates'][next_idx] == alldates[next_idx]:
            nxt_o = s['open'][next_idx]
            nxt_c = s['close'][next_idx]
            nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
            rec['nxt_ret'] = round(nxt_ret, 2)
            rs_data[rec['sym']].append(rec)

for label, recs in [("Top 5 (strongest)", [r for r in sum([recs for recs in rs_data.values()], []) if r in [x for day_recs in [sorted([r for rlist in rs_data.values() for r in rlist], key=lambda x: x['ret'])[-5:]] for x in day_recs]])]:
    pass

# Simplified: just show the pattern
all_day_results = []
for date_idx, date in enumerate(alldates):
    day_recs = []
    for sym in stocks:
        s = data['stocks'][sym]
        if date_idx < len(s['dates']) and s['dates'][date_idx] == date:
            o, c = s['open'][date_idx], s['close'][date_idx]
            ret = (c - o) / o * 100
            nxt_idx = date_idx + 1
            if nxt_idx < len(s['dates']):
                nxt_o = s['open'][nxt_idx]
                nxt_c = s['close'][nxt_idx]
                nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
                day_recs.append({'ret': ret, 'nxt_ret': nxt_ret})
    
    if day_recs:
        day_recs.sort(key=lambda r: r['ret'])
        all_day_results.append({
            'date': date,
            'bottom5_avg': np.mean([r['nxt_ret'] for r in day_recs[:5]]),
            'top5_avg': np.mean([r['nxt_ret'] for r in day_recs[-5:]]),
            'mid_avg': np.mean([r['nxt_ret'] for r in day_recs[5:-5]]) if len(day_recs) > 10 else 0
        })

bottom_avgs = [r['bottom5_avg'] for r in all_day_results]
top_avgs = [r['top5_avg'] for r in all_day_results]
print(f"  Bottom 5 next-day avg: {np.mean(bottom_avgs):.3f}%")
print(f"  Top 5 next-day avg: {np.mean(top_avgs):.3f}%")
print(f"  Bottom 5 positive: {sum(1 for r in bottom_avgs if r > 0)}/{len(bottom_avgs)} ({sum(1 for r in bottom_avgs if r > 0)/len(bottom_avgs)*100:.1f}%)")
print(f"  Top 5 positive: {sum(1 for r in top_avgs if r > 0)}/{len(top_avgs)} ({sum(1 for r in top_avgs if r > 0)/len(top_avgs)*100:.1f}%)")

# ============================================================
# PERSPECTIVE 12: The "Mean Reversion vs Trend" — by autocorrelation
# ============================================================
print("\n=== PERSPECTIVE 12: Stock-Specific Personality Trades ===")
# Use autocorrelation to determine if stock trends or reverts
# Then find the best specific trade for each type

autocorrs = {}
for sym in stocks:
    s = data['stocks'][sym]
    closes = s['close']
    if len(closes) < 10: continue
    rets = [(closes[i] - s['open'][i]) / s['open'][i] * 100 for i in range(len(closes))]
    # Lag-1 autocorrelation
    rets_arr = np.array(rets)
    corr = np.corrcoef(rets_arr[:-1], rets_arr[1:])[0, 1] if len(rets) > 2 else 0
    autocorrs[sym] = corr if not np.isnan(corr) else 0

# Show best mean-reverters and best trenders
sorted_ac = sorted(autocorrs.items(), key=lambda x: x[1])
print("  Top 5 mean-reverters (negative autocorr):")
for sym, ac in sorted_ac[:5]:
    s = data['stocks'][sym]
    rets = [(s['close'][i] - s['open'][i]) / s['open'][i] * 100 for i in range(len(s['dates']))]
    # After a red day
    red_days = [i for i in range(1, len(rets)) if rets[i-1] < -1.0]
    nxt_after_red = [rets[i] for i in red_days if i < len(rets)]
    avg_after_red = np.mean(nxt_after_red) if nxt_after_red else 0
    print(f"    {sym}: ac={ac:.3f}, after -1% day -> next avg={avg_after_red:.3f}%")

print("  Top 5 trenders (positive autocorr):")
for sym, ac in sorted_ac[-5:]:
    s = data['stocks'][sym]
    rets = [(s['close'][i] - s['open'][i]) / s['open'][i] * 100 for i in range(len(s['dates']))]
    green_days = [i for i in range(1, len(rets)) if rets[i-1] > 1.0]
    nxt_after_green = [rets[i] for i in green_days if i < len(rets)]
    avg_after_green = np.mean(nxt_after_green) if nxt_after_green else 0
    print(f"    {sym}: ac={ac:.3f}, after +1% day -> next avg={avg_after_green:.3f}%")

# ============================================================
# PERSPECTIVE 13: Monthly / Biweekly Patterns
# ============================================================
print("\n=== PERSPECTIVE 13: Calendar Month Patterns ===")
# Last week of month, first week, mid-month
month_data = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(len(s['dates']) - 1):
        date_str = s['dates'][i]
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        day = dt.day
        month = dt.month
        
        o = s['open'][i]
        c = s['close'][i]
        ret = (c - o) / o * 100
        nxt_o = s['open'][i+1]
        nxt_c = s['close'][i+1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
        
        month_data.append({
            'sym': sym, 'date': date_str,
            'day': day, 'month': month,
            'ret': round(ret, 2),
            'nxt_ret': round(nxt_ret, 2),
            'week': 'first' if day <= 7 else ('last' if day >= 22 else 'mid')
        })

for label, cond in [
    ("First 5 days of month", lambda r: r['day'] <= 5),
    ("Last 5 days of month", lambda r: r['day'] >= 25),
    ("Mid-month (10-20)", lambda r: 10 <= r['day'] <= 20),
    ("Day 1 of month", lambda r: r['day'] == 1),
    ("Day 15 of month (expiry)", lambda r: r['day'] == 15),
    ("3rd week (15-21)", lambda r: 15 <= r['day'] <= 21),
]:
    subset = [r for r in month_data if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        cur_ups = sum(1 for r in subset if r['ret'] > 0)
        avg_cur = np.mean([r['ret'] for r in subset])
        avg = np.mean([r['nxt_ret'] for r in subset])
        print(f"  {label}: {n}, same_day_pos={cur_ups/n*100:.1f}%, cur_avg={avg_cur:.3f}%, nxt_pos={ups/n*100:.1f}%, nxt_avg={avg:.3f}%")

# ============================================================
# PERSPECTIVE 14: Volume Spike after MA Touch
# ============================================================
print("\n=== PERSPECTIVE 14: Combined MA Touch + Volume ===")
combined = []
for sym in stocks:
    s = data['stocks'][sym]
    vols = np.array(s['volume'], dtype=float)
    for i in range(5, len(s['dates']) - 1):
        if i >= len(s.get('ema9', [])): continue
        ema9 = s['ema9'][i]
        if ema9 is None: continue
        
        close = s['close'][i]
        open_ = s['open'][i]
        dist = (close - ema9) / ema9 * 100
        vol_ratio = s['volume'][i] / np.mean(vols[i-5:i]) if np.mean(vols[i-5:i]) > 0 else 1
        
        nxt_o = s['open'][i+1]
        nxt_c = s['close'][i+1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
        
        combined.append({
            'sym': sym, 'date': s['dates'][i],
            'dist': dist, 'vol_ratio': vol_ratio,
            'nxt_ret': round(nxt_ret, 2)
        })

for label, cond in [
    ("Touch MA9 + low vol + green", lambda r: abs(r['dist']) < 0.5 and r['vol_ratio'] < 0.8 and r['nxt_ret'] > 0),
    ("Bounce from MA9 (-1 to -3%)", lambda r: -3 < r['dist'] < -1),
    ("Reject from MA9 (+1 to +3%)", lambda r: 1 < r['dist'] < 3),
    ("Far below MA9 (-5%) + low vol", lambda r: r['dist'] < -5 and r['vol_ratio'] < 1.0),
    ("Far above MA9 (+5%) + high vol", lambda r: r['dist'] > 5 and r['vol_ratio'] > 1.5),
]:
    subset = [r for r in combined if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        avg = np.mean([r['nxt_ret'] for r in subset])
        print(f"  {label}: {n}, {ups/n*100:.1f}% pos, avg={avg:.3f}%")

# ============================================================
# PERSPECTIVE 15: Winning the most — the SIMPLEST non-gap trade
# ============================================================
print("\n=== PERSPECTIVE 15: Summary of Best Hidden Patterns ===")
print("""
Criteria: Must have >100 events, win rate >55%, avg return >0.2%, 
and NOT rely on gap filling or day-of-week as primary signal.
""")
