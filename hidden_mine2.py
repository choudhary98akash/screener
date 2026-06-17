#!/usr/bin/env python
"""
Deep hidden pattern mining — find ONE trade the data screams but humans miss.
NO gap strategies. NO day-of-week primary. Looking for multi-factor combos.
"""
import json, itertools, sys
from collections import defaultdict
from datetime import datetime
import numpy as np

data = json.load(open('data.json'))
stocks = list(data['stocks'].keys())
alldates = data['stocks'][stocks[0]]['dates']
ndates = len(alldates)

def safe(v, default=0):
    return v if v is not None and not (isinstance(v, float) and np.isnan(v)) else default

# Build enhanced records
all_recs = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(len(s['dates'])):
        rec = {
            'sym': sym, 'date': s['dates'][i],
            'open': s['open'][i], 'high': s['high'][i],
            'low': s['low'][i], 'close': s['close'][i],
            'volume': s['volume'][i],
            'ema9': safe(s.get('ema9', [None]*len(s['dates']))[i] if i < len(s.get('ema9', [])) else None),
            'ema21': safe(s.get('ema21', [None]*len(s['dates']))[i] if i < len(s.get('ema21', [])) else None),
            'rsi14': safe(s.get('rsi14', [None]*len(s['dates']))[i] if i < len(s.get('rsi14', [])) else None),
            'gap': safe(s.get('gaps', [{}]*len(s['dates']))[i].get('gap_pct') if i < len(s.get('gaps', [])) else None),
            'prev_close': s['prev_close'] if i == len(s['dates'])-1 else (s['close'][i-1] if i > 0 else s['open'][i]),
        }
        all_recs.append(rec)

print(f"Total records: {len(all_recs)}")

# ============================================================
# 1. The "Fakeout" — Open strong, close weak (and vice versa)
# ============================================================
print("\n=== 1. FAKEOUT PATTERN ===")
fakeout = []
for i in range(1, len(all_recs)):
    r = all_recs[i]
    ret = (r['close'] - r['open']) / r['open'] * 100 if r['open'] else 0
    gap = r.get('gap', 0) or 0
    # "Fakeout": gaps up more than 0.5% but closes below open (bearish engulfing at open)
    fakeout_up = gap > 0.5 and ret < -0.5
    fakeout_dn = gap < -0.5 and ret > 0.5
    if fakeout_up or fakeout_dn:
        fakeout.append({
            'sym': r['sym'], 'date': r['date'],
            'gap': round(gap, 2), 'ret': round(ret, 2),
            'type': 'UP_FAKE' if fakeout_up else 'DN_FAKE',
            'rsi': r['rsi14'], 'ema9': r['ema9'],
        })

print(f"Fakeouts found: {len(fakeout)}")
for ftype in ['UP_FAKE', 'DN_FAKE']:
    subset = [f for f in fakeout if f['type'] == ftype]
    if subset:
        print(f"  {ftype}: {len(subset)} events")
        print(f"    Avg ret: {np.mean([f['ret'] for f in subset]):.2f}%")
        print(f"    Avg gap: {np.mean([f['gap'] for f in subset]):.2f}%")

# ============================================================
# 2. Stock × Date — specific anomalies
# ============================================================
print("\n=== 2. STOCK-SPECIFIC HIDDEN RHYTHMS ===")
# For each stock, find the dates where it behaves most predictably
for sym in stocks:
    s = data['stocks'][sym]
    rets = [(s['close'][i] - s['open'][i]) / s['open'][i] * 100 for i in range(min(15, len(s['dates'])))]
    recs = [r for r in all_recs if r['sym'] == sym]
    
    # Calculate: which day of month does this stock perform best?
    day_perf = defaultdict(list)
    for r in recs:
        dt = datetime.strptime(r['date'], '%Y-%m-%d')
        day_key = dt.day
        ret = (r['close'] - r['open']) / r['open'] * 100 if r['open'] else 0
        day_perf[day_key].append(ret)
    
    best_days = []
    for day, rets_list in day_perf.items():
        if len(rets_list) >= 2:
            avg = np.mean(rets_list)
            best_days.append((day, avg, len(rets_list)))
    best_days.sort(key=lambda x: x[1], reverse=True)

# ============================================================
# 3. MULTI-FACTOR GRID SEARCH — Find the highest EV setup
# ============================================================
print("\n=== 3. MULTI-FACTOR GRID SEARCH (non-gap focused) ===")
# Factors to combine (none are gap-primary):
# - Volume trend (increasing/decreasing over 5 days)
# - RSI zone (<30, 30-50, 50-70, >70)
# - MA position (above/below/bouncing)
# - Price relative to prev day's range
# - Consecutive green/red days
# - Time of month

# Build feature vectors
features = []
for i in range(5, len(all_recs)):
    r = all_recs[i]
    r_prev = all_recs[i-1]
    r_prev2 = all_recs[i-2]
    
    ret_today = (r['close'] - r['open']) / r['open'] * 100 if r['open'] else 0
    ret_prev = (r_prev['close'] - r_prev['open']) / r_prev['open'] * 100 if r_prev['open'] else 0
    ret_prev2 = (r_prev2['close'] - r_prev2['open']) / r_prev2['open'] * 100 if r_prev2['open'] else 0
    
    # Volume trend (ratio of vol last 5 days to 5 before that)
    vol_hist = [all_recs[j]['volume'] for j in range(max(0,i-10), i) if all_recs[j]['volume'] > 0]
    vol_ratio = r['volume'] / np.mean(vol_hist[-5:]) if len(vol_hist) >= 5 and np.mean(vol_hist[-5:]) > 0 else 1
    
    # MA distance
    dist_9 = (r['close'] - r['ema9']) / r['ema9'] * 100 if r['ema9'] and r['ema9'] != 0 else 0
    dist_21 = (r['close'] - r['ema21']) / r['ema21'] * 100 if r['ema21'] and r['ema21'] != 0 else 0
    
    # Range contraction
    range_today = (r['high'] - r['low']) / r['low'] * 100 if r['low'] else 0
    range_prev = (r_prev['high'] - r_prev['low']) / r_prev['low'] * 100 if r_prev['low'] else 0
    
    # Close position in day's range (0=low, 1=high)
    close_pos = (r['close'] - r['low']) / (r['high'] - r['low']) if (r['high'] - r['low']) > 0 else 0.5
    
    # Next day's return (what we want to predict)
    if i + 1 < len(all_recs):
        nxt = all_recs[i+1]
        # Use same-symbol check
        if nxt['sym'] == r['sym']:
            nxt_open = nxt['open']
            nxt_close = nxt['close']
            nxt_ret = (nxt_close - nxt_open) / nxt_open * 100 if nxt_open else 0
        else:
            nxt_ret = 0
    else:
        nxt_ret = 0
    
    dt = datetime.strptime(r['date'], '%Y-%m-%d')
    
    features.append({
        'sym': r['sym'], 'date': r['date'],
        'rsi': r['rsi14'] or 50,
        'dist9': dist_9, 'dist21': dist_21,
        'ret_today': round(ret_today, 2),
        'ret_prev': round(ret_prev, 2),
        'vol_ratio': round(vol_ratio, 2),
        'range_pct': round(range_today, 2),
        'range_prev': round(range_prev, 2),
        'close_pos': round(close_pos, 3),
        'day': dt.day, 'month': dt.month,
        'dow': dt.weekday(),
        'nxt_ret': round(nxt_ret, 2),
        'nxt_up': nxt_ret > 0,
    })

print(f"Feature vectors: {len(features)}")

# Now search for high-WR combos
# Instead of brute force, use targeted hypotheses

hypotheses = [
    # Hypothesis 1: RSI between 40-60 + close in top 40% of range + low vol
    ("RSI 40-60 + close_pos>0.6 + vol<0.8", 
     lambda f: 40 <= f['rsi'] <= 60 and f['close_pos'] > 0.6 and f['vol_ratio'] < 0.8),
    
    # Hypothesis 2: 2 red days + today green + vol expanding
    ("2 red days then green + vol>1.2", 
     lambda f: f['ret_prev'] < 0 and f['ret_today'] > 0 and f['vol_ratio'] > 1.2),
    
    # Hypothesis 3: Big range contraction + close near high
    ("Range halved + close_pos>0.7", 
     lambda f: f['range_pct'] < f['range_prev'] * 0.5 and f['close_pos'] > 0.7),
    
    # Hypothesis 4: Below both MAs but closing up (potential reversal)
    ("Below EMA9 & EMA21 + green day", 
     lambda f: f['dist9'] < 0 and f['dist21'] < 0 and f['ret_today'] > 0),
    
    # Hypothesis 5: Above both MAs + RSI 50-70 + low vol (quiet strength)
    ("Above MAs + RSI 50-70 + vol<0.7", 
     lambda f: f['dist9'] > 0 and f['dist21'] > 0 and 50 <= f['rsi'] <= 70 and f['vol_ratio'] < 0.7),
    
    # Hypothesis 6: RSI oversold (<35) + green day (reversal start)
    ("RSI<35 + green day (reversal)", 
     lambda f: f['rsi'] < 35 and f['ret_today'] > 0),
    
    # Hypothesis 7: After big red day (-2%) + today small green (+0 to +1%)
    ("After -2% day + tiny bounce (+0 to +0.5%)", 
     lambda f: f['ret_prev'] < -2 and 0 <= f['ret_today'] <= 0.5),
    
    # Hypothesis 8: 3 narrow range days + expanding today
    ("3 narrow range days + vol>1.5", 
     lambda f: False),  # Need more context
    
    # Hypothesis 9: Expiry week (15-20th) + RSI 40-60
    ("Expiry week (15-20) + RSI 40-60", 
     lambda f: 15 <= f['day'] <= 20 and 40 <= f['rsi'] <= 60),
    
    # Hypothesis 10: Tuesday + RSI 30-50 + close_pos > 0.7
    ("Tue + RSI 30-50 + close_pos>0.7", 
     lambda f: f['dow'] == 1 and 30 <= f['rsi'] <= 50 and f['close_pos'] > 0.7),
]

for hname, hfunc in hypotheses:
    subset = [f for f in features if hfunc(f)]
    if subset:
        n = len(subset)
        ups = sum(1 for f in subset if f['nxt_up'])
        avg_nxt = np.mean([f['nxt_ret'] for f in subset])
        best = max(subset, key=lambda f: f['nxt_ret'])
        if n >= 10:
            print(f"  {hname}: n={n}, WR={ups/n*100:.1f}%, avg_nxt={avg_nxt:.3f}%")

# ============================================================
# 4. BRUTE FORCE: 2-factor grid
# ============================================================
print("\n=== 4. GRID SEARCH: Top 2-Factor Combos ===")
results = []

# Bucket by RSI zones
rsi_buckets = [(0, 30, 'RSI<30'), (30, 50, 'RSI 30-50'), (50, 70, 'RSI 50-70'), (70, 100, 'RSI>70')]
vol_buckets = [(0, 0.5, 'Vol<0.5'), (0.5, 0.8, 'Vol 0.5-0.8'), (0.8, 1.2, 'Vol 0.8-1.2'), (1.2, 3, 'Vol>1.2')]
dist_buckets = [(-999, -3, 'Far below MA'), (-3, -1, 'Below MA'), (-1, 1, 'Near MA'), (1, 3, 'Above MA'), (3, 999, 'Far above MA')]
close_pos_buckets = [(0, 0.25, 'Close bottom'), (0.25, 0.5, 'Close low-mid'), (0.5, 0.75, 'Close high-mid'), (0.75, 1, 'Close top')]
ret_buckets = [(-999, -2, 'Big red'), (-2, -0.5, 'Red'), (-0.5, 0.5, 'Flat'), (0.5, 2, 'Green'), (2, 999, 'Big green')]

all_buckets = [
    ('rsi', rsi_buckets), ('vol_ratio', vol_buckets), ('dist9', dist_buckets),
    ('close_pos', close_pos_buckets), ('ret_today', ret_buckets),
    ('ret_prev', ret_buckets)
]

# Try all pairs
for i in range(len(all_buckets)):
    for j in range(i+1, len(all_buckets)):
        name1, buck1 = all_buckets[i]
        name2, buck2 = all_buckets[j]
        for lo1, hi1, label1 in buck1:
            for lo2, hi2, label2 in buck2:
                subset = [f for f in features 
                         if lo1 <= f[name1] < hi1 and lo2 <= f[name2] < hi2]
                if len(subset) >= 20:
                    ups = sum(1 for f in subset if f['nxt_up'])
                    avg_nxt = np.mean([f['nxt_ret'] for f in subset])
                    wr = ups / len(subset) * 100
                    if wr >= 60 or avg_nxt >= 0.3:
                        results.append({
                            'label': f"{label1} + {label2}",
                            'n': len(subset), 'wr': round(wr, 1),
                            'avg': round(avg_nxt, 3)
                        })

results.sort(key=lambda r: r['avg'], reverse=True)
print(f"  Total combos found: {len(results)}")
for r in results[:20]:
    print(f"  {r['label']}: n={r['n']}, WR={r['wr']}%, avg={r['avg']:+.3f}%")

# ============================================================
# 5. THE SINGLE BEST TRADE: Most predictable stock-date combo
# ============================================================
print("\n=== 5. THE SINGLE TRADE: Most Predictable Setup ===")
# For each stock, find which conditions predict next-day return best
stock_best = {}
for sym in stocks:
    sym_features = [f for f in features if f['sym'] == sym]
    if len(sym_features) < 20: continue
    
    # Try RSI + close_pos combos per stock
    best_wr = 0
    best_cond = ""
    best_n = 0
    best_avg = 0
    
    for lo_r, hi_r, r_label in [(0, 30, 'LowRSI'), (30, 50, 'MidLowRSI'), (50, 70, 'MidHighRSI'), (70, 100, 'HighRSI')]:
        for lo_c, hi_c, c_label in [(0, 0.3, 'Bot'), (0.3, 0.5, 'Low'), (0.5, 0.7, 'Mid'), (0.7, 1, 'Top')]:
            subset = [f for f in sym_features 
                     if lo_r <= f['rsi'] < hi_r and lo_c <= f['close_pos'] < hi_c]
            if len(subset) >= 3:
                ups = sum(1 for f in subset if f['nxt_up'])
                avg = np.mean([f['nxt_ret'] for f in subset])
                wr = ups / len(subset) * 100
                if wr >= 75 and len(subset) >= 3:
                    if avg > best_avg or (abs(avg - best_avg) < 0.01 and wr > best_wr):
                        best_wr = wr
                        best_cond = f"{r_label}+{c_label}"
                        best_n = len(subset)
                        best_avg = avg
    
    if best_n >= 3:
        stock_best[sym] = {'cond': best_cond, 'wr': best_wr, 'n': best_n, 'avg': best_avg}

# Show best per stock
stock_ranked = sorted(stock_best.items(), key=lambda x: x[1]['avg'], reverse=True)
print("  Top stock-specific patterns (by avg next ret):")
for sym, info in stock_ranked[:10]:
    print(f"    {sym}: {info['cond']} — WR={info['wr']:.0f}%, n={info['n']}, avg_next={info['avg']:+.3f}%")

# ============================================================
# 6. THE ULTIMATE: Find if there's a stock that always does X on Y day
# ============================================================
print("\n=== 6. DATE-SPECIFIC ANOMALIES ===")
# Look for stocks that have a specific pattern on the SAME calendar date across months
# e.g., "RELIANCE always up on the 15th"
date_anomalies = []
for sym in stocks:
    sym_recs = [r for r in all_recs if r['sym'] == sym]
    day_buckets = defaultdict(list)
    for r in sym_recs:
        dt = datetime.strptime(r['date'], '%Y-%m-%d')
        ret = (r['close'] - r['open']) / r['open'] * 100 if r['open'] else 0
        day_buckets[dt.day].append(ret)
    
    for day, rets in day_buckets.items():
        if len(rets) >= 2:
            avg = np.mean(rets)
            pos = sum(1 for r in rets if r > 0)
            if pos == len(rets) and len(rets) >= 2:  # 100% win rate!
                date_anomalies.append({
                    'sym': sym, 'day': day,
                    'n': len(rets), 'avg': round(avg, 2),
                    'rets': [round(r,2) for r in rets]
                })

date_anomalies.sort(key=lambda x: x['avg'], reverse=True)
print("  100% win rate on same calendar day:")
for a in date_anomalies[:15]:
    print(f"    {a['sym']} on day {a['day']}: n={a['n']}, avg={a['avg']:+.2f}%, all={a['rets']}")

# ============================================================
# 7. THE "NOBODY LOOKED AT THIS" — Price × Volume Divergence
# ============================================================
print("\n=== 7. PRICE-VOLUME DIVERGENCE ===")
# Price making higher highs but volume declining = divergence
pv_div = []
for i in range(5, len(all_recs)):
    r = all_recs[i]
    if r['volume'] == 0: continue
    
    vol_hist = [all_recs[j]['volume'] for j in range(i-5, i) if all_recs[j]['volume'] > 0]
    close_hist = [all_recs[j]['close'] for j in range(i-5, i+1)]
    open_hist = [all_recs[j]['open'] for j in range(i-5, i+1)]
    
    if len(vol_hist) < 4 or len(close_hist) < 5: continue
    
    vol_trend = np.polyfit(range(len(vol_hist)), vol_hist, 1)[0]  # slope of volume
    price_trend = np.polyfit(range(len(close_hist)), close_hist, 1)[0]  # slope of price
    
    # Also check next day
    if i + 1 < len(all_recs) and all_recs[i+1]['sym'] == r['sym']:
        nxt = all_recs[i+1]
        nxt_ret = (nxt['close'] - nxt['open']) / nxt['open'] * 100 if nxt['open'] else 0
    else:
        continue
    
    pv_div.append({
        'sym': r['sym'], 'date': r['date'],
        'price_slope': price_trend,
        'vol_slope': vol_trend,
        'nxt_ret': round(nxt_ret, 2),
        'type': 'bullish' if price_trend > 0 and vol_trend < 0 else
                'bearish' if price_trend < 0 and vol_trend > 0 else
                'normal'
    })

for div_type in ['bullish', 'bearish', 'normal']:
    subset = [d for d in pv_div if d['type'] == div_type]
    if subset:
        n = len(subset)
        ups = sum(1 for d in subset if d['nxt_ret'] > 0)
        avg = np.mean([d['nxt_ret'] for d in subset])
        print(f"  {div_type}: n={n}, WR={ups/n*100:.1f}%, avg={avg:.3f}%")
        if n <= 100:
            best = max(subset, key=lambda d: d['nxt_ret'])
            print(f"    Best: {best['sym']} {best['date']} -> {best['nxt_ret']:+.2f}%")

# ============================================================
# 8. BONUS: The "Monday was down hard, buy these specific stocks Tue"
# ============================================================
print("\n=== 8. MONDAY DOWNSHIFT PATTERN ===")
# After a bad Monday, which specific stocks bounce hardest on Tuesday?
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(1, len(s['dates'])-1):
        dt = datetime.strptime(s['dates'][i-1], '%Y-%m-%d')
        if dt.weekday() != 0: continue  # Monday
        mon_ret = (s['close'][i-1] - s['open'][i-1]) / s['open'][i-1] * 100
        if mon_ret < -1:  # Bad Monday
            tue_ret = (s['close'][i] - s['open'][i]) / s['open'][i] * 100
            # This would need more structure, skip for now
            pass

print("\nDone.")
