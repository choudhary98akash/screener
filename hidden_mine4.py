#!/usr/bin/env python
"""
ULTIMATE DEEP MINE: Truly hidden patterns.
Looking for the single weirdest, most profitable, non-obvious trade.
"""
import json, itertools
from collections import defaultdict
from datetime import datetime
import numpy as np

data = json.load(open('data.json'))
stocks = list(data['stocks'].keys())
alldates = data['stocks'][stocks[0]]['dates']

def safe(v, default=0):
    return v if v is not None and not (isinstance(v, float) and np.isnan(v)) else default

# ============================================================
# PATTERN 1: When a stock's behavior contradicts the market
# ============================================================
print("="*70)
print("PATTERN 1: Contrarian Stock — Go against the crowd")
print("="*70)
# When most stocks are up, this stock is down (or vice versa) — what happens next?

contrarian = []
for date_idx, date in enumerate(alldates):
    day_stocks = []
    for sym in stocks:
        s = data['stocks'][sym]
        if date_idx < len(s['dates']) and s['dates'][date_idx] == date:
            o, c = s['open'][date_idx], s['close'][date_idx]
            ret = (c - o) / o * 100 if o else 0
            day_stocks.append({'sym': sym, 'ret': ret})
    
    if len(day_stocks) < 20: continue
    
    # Market direction
    avg_ret = np.mean([d['ret'] for d in day_stocks])
    market_up = avg_ret > 0.2
    market_down = avg_ret < -0.2
    
    for d in day_stocks:
        # Contrarian: market up but this stock down >0.5%
        if market_up and d['ret'] < -0.5:
            nxt_idx = date_idx + 1
            s = data['stocks'][d['sym']]
            if nxt_idx < len(s['dates']) and s['dates'][nxt_idx] == alldates[nxt_idx]:
                nxt_o = s['open'][nxt_idx]
                nxt_c = s['close'][nxt_idx]
                nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
                contrarian.append({
                    'sym': d['sym'], 'date': date,
                    'type': 'MARKET_UP_STOCK_DN',
                    'stock_ret': round(d['ret'], 2),
                    'market_ret': round(avg_ret, 2),
                    'nxt_ret': round(nxt_ret, 2)
                })
        
        # Contrarian: market down but this stock up >0.5%
        if market_down and d['ret'] > 0.5:
            nxt_idx = date_idx + 1
            s = data['stocks'][d['sym']]
            if nxt_idx < len(s['dates']) and s['dates'][nxt_idx] == alldates[nxt_idx]:
                nxt_o = s['open'][nxt_idx]
                nxt_c = s['close'][nxt_idx]
                nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
                contrarian.append({
                    'sym': d['sym'], 'date': date,
                    'type': 'MARKET_DN_STOCK_UP',
                    'stock_ret': round(d['ret'], 2),
                    'market_ret': round(avg_ret, 2),
                    'nxt_ret': round(nxt_ret, 2)
                })

for ctype in ['MARKET_UP_STOCK_DN', 'MARKET_DN_STOCK_UP']:
    subset = [c for c in contrarian if c['type'] == ctype]
    if subset:
        n = len(subset)
        ups = sum(1 for c in subset if c['nxt_ret'] > 0)
        avg = np.mean([c['nxt_ret'] for c in subset])
        print(f"  {ctype}: n={n}, WR={ups/n*100:.1f}%, avg={avg:.3f}%")
        
        # Per-stock breakdown
        sym_perf = defaultdict(list)
        for c in subset:
            sym_perf[c['sym']].append(c['nxt_ret'])
        
        best_syms = sorted(sym_perf.items(), key=lambda x: np.mean(x[1]), reverse=True)[:5]
        for sym, rets in best_syms:
            wr = sum(1 for r in rets if r > 0) / len(rets) * 100
            print(f"    {sym}: n={len(rets)}, WR={wr:.0f}%, avg={np.mean(rets):.3f}%")

# ============================================================
# PATTERN 2: The "2-day RSI reset"
# ============================================================
print("\n" + "="*70)
print("PATTERN 2: RSI Reset — Oversold bounce on day 2 of recovery")
print("="*70)
# Stock was oversold (RSI<30), then has 1 green day, then what?
rsi_reset = []
for sym in stocks:
    s = data['stocks'][sym]
    rsi_vals = s.get('rsi14', [])
    if not rsi_vals: continue
    for i in range(2, len(s['dates']) - 1):
        if i >= len(rsi_vals): continue
        rsi_2d = rsi_vals[i-2] if i-2 < len(rsi_vals) else 50
        rsi_1d = rsi_vals[i-1] if i-1 < len(rsi_vals) else 50
        rsi_td = rsi_vals[i] if i < len(rsi_vals) else 50
        
        if None in (rsi_2d, rsi_1d, rsi_td): continue
        
        # Was oversold 2 days ago, now coming back
        if rsi_2d < 35 and rsi_1d < rsi_td:  # RSI rising
            # Today
            o, c = s['open'][i], s['close'][i]
            ret_today = (c - o) / o * 100 if o else 0
            # Next day
            nxt_o = s['open'][i+1] if i+1 < len(s['open']) else 0
            nxt_c = s['close'][i+1] if i+1 < len(s['close']) else 0
            nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
            
            rsi_reset.append({
                'sym': sym, 'date': s['dates'][i],
                'rsi_2d': round(rsi_2d, 1), 'rsi_td': round(rsi_td, 1),
                'ret_today': round(ret_today, 2),
                'nxt_ret': round(nxt_ret, 2)
            })

print(f"  Total events: {len(rsi_reset)}")
if rsi_reset:
    n = len(rsi_reset)
    ups = sum(1 for r in rsi_reset if r['nxt_ret'] > 0)
    avg = np.mean([r['nxt_ret'] for r in rsi_reset])
    print(f"  WR: {ups/n*100:.1f}%, avg: {avg:.3f}%")
    
    sym_perf = defaultdict(list)
    for r in rsi_reset:
        sym_perf[r['sym']].append(r['nxt_ret'])
    
    best_syms = sorted(sym_perf.items(), key=lambda x: np.mean(x[1]), reverse=True)[:10]
    print("  Best stocks:")
    for sym, rets in best_syms:
        if len(rets) >= 2:
            wr = sum(1 for r in rets if r > 0) / len(rets) * 100
            print(f"    {sym}: n={len(rets)}, WR={wr:.0f}%, avg={np.mean(rets):+.3f}%")

# ============================================================
# PATTERN 3: The "Tuesday is Golden" — Stock-specific deep dive
# ============================================================
print("\n" + "="*70)
print("PATTERN 3: Tuesday Stock-Specific Deep Dive (n>5, WR>75%)")
print("="*70)

tuesday_data = defaultdict(list)
for f_idx in range(len(alldates)):
    date = alldates[f_idx]
    dt = datetime.strptime(date, '%Y-%m-%d')
    if dt.weekday() != 1: continue  # Tuesday
    
    for sym in stocks:
        s = data['stocks'][sym]
        if f_idx + 1 >= len(s['dates']): continue
        if s['dates'][f_idx] != date: continue
        
        o = s['open'][f_idx]
        c = s['close'][f_idx]
        ret = (c - o) / o * 100 if o else 0
        
        nxt_o = s['open'][f_idx + 1]
        nxt_c = s['close'][f_idx + 1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
        
        tuesday_data[sym].append({
            'date': date,
            'ret': round(ret, 2),
            'nxt_ret': round(nxt_ret, 2),
        })

print(f"{'Stock':<15} {'N':<5} {'WinRate':<10} {'AvgRet':<10} {'SumRet':<10} {'Best':<10}")
print("-"*65)
for sym, records in sorted(tuesday_data.items(), key=lambda x: np.mean([r['nxt_ret'] for r in x[1]]), reverse=True):
    n = len(records)
    if n < 6: continue
    ups = sum(1 for r in records if r['nxt_ret'] > 0)
    wr = ups / n * 100
    avg = np.mean([r['nxt_ret'] for r in records])
    total = sum(r['nxt_ret'] for r in records)
    best = max(records, key=lambda r: r['nxt_ret'])
    if wr >= 70:
        print(f"{sym:<15} {n:<5} {wr:<10.1f} {avg:<+10.3f} {total:<+10.2f} {best['nxt_ret']:<+10.2f}")

# ============================================================
# PATTERN 4: The "Wednesday Reversal"
# ============================================================
print("\n" + "="*70)
print("PATTERN 4: The Forbidden Wednesday Pattern (Contrarian)")
print("="*70)
# Known: Wednesday gap-downs fill at 84.7%.
# Unknown: What about stocks that gapped UP on Wednesday? (The "forbidden" pattern)
# The strategy says NEVER touch gap-ups on Wednesday.
# But what if we look at it differently — not by gap, but by price action?

wed_data = []
for f_idx in range(len(alldates)):
    date = alldates[f_idx]
    dt = datetime.strptime(date, '%Y-%m-%d')
    if dt.weekday() != 2: continue  # Wednesday
    
    for sym in stocks:
        s = data['stocks'][sym]
        if f_idx + 1 >= len(s['dates']): continue
        if s['dates'][f_idx] != date: continue
        
        o = s['open'][f_idx]
        h = s['high'][f_idx]
        l = s['low'][f_idx]
        c = s['close'][f_idx]
        prev_c = s['close'][f_idx - 1] if f_idx > 0 else o
        
        gap = (o - prev_c) / prev_c * 100 if prev_c else 0
        ret = (c - o) / o * 100 if o else 0
        close_pos = (c - l) / (h - l) if (h - l) > 0 else 0.5
        
        nxt_o = s['open'][f_idx + 1]
        nxt_c = s['close'][f_idx + 1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
        
        wed_data.append({
            'sym': sym, 'date': date,
            'gap': round(gap, 2), 'ret': round(ret, 2),
            'close_pos': round(close_pos, 3),
            'nxt_ret': round(nxt_ret, 2),
            'gap_dir': 'UP' if gap > 0 else ('DN' if gap < 0 else 'FLAT'),
            'ret_dir': 'UP' if ret > 0 else ('DN' if ret < 0 else 'FLAT'),
        })

# Strange combos on Wednesday
for label, cond in [
    ("Opened up but closed down (fakeout)", lambda r: r['gap'] > 0 and r['ret'] < -0.5),
    ("Opened down but closed up (reversal)", lambda r: r['gap'] < 0 and r['ret'] > 0.5),
    ("Gapped up + closed green (allowed?)", lambda r: r['gap'] > 0.3 and r['ret'] > 0.3),
    ("Gapped down + closed red (continues)", lambda r: r['gap'] < -0.3 and r['ret'] < -0.3),
]:
    subset = [r for r in wed_data if cond(r)]
    if subset:
        n = len(subset)
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        avg = np.mean([r['nxt_ret'] for r in subset])
        print(f"  {label}: n={n}, WR={ups/n*100:.1f}%, avg={avg:.3f}%")

# ============================================================
# PATTERN 5: The "Contrarian Volume" — After a huge volume day
# ============================================================
print("\n" + "="*70)
print("PATTERN 5: After a Volume Explosion — What happens next?")
print("="*70)

# When volume is 2x+ normal AND the stock made a big move — exhaustion?
vol_exhaustion = []
for sym in stocks:
    s = data['stocks'][sym]
    vols = np.array(s['volume'], dtype=float)
    for i in range(10, len(s['dates']) - 1):
        avg_vol = np.mean(vols[max(0,i-10):i])
        if avg_vol == 0: continue
        vol_ratio = s['volume'][i] / avg_vol
        
        if vol_ratio >= 2:
            o, c = s['open'][i], s['close'][i]
            ret = (c - o) / o * 100 if o else 0
            h, l = s['high'][i], s['low'][i]
            close_pos = (c - l) / (h - l) if (h - l) > 0 else 0.5
            
            nxt_o = s['open'][i+1]
            nxt_c = s['close'][i+1]
            nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
            
            vol_exhaustion.append({
                'sym': sym, 'date': s['dates'][i],
                'vol': round(vol_ratio, 1),
                'ret': round(ret, 2),
                'close_pos': round(close_pos, 3),
                'nxt_ret': round(nxt_ret, 2),
            })

print(f"  Total: {len(vol_exhaustion)}")
for vrange, label in [(0, "All"), (2, "2-3x"), (3, "3-5x"), (5, "5x+")]:
    if vrange == 0:
        subset = vol_exhaustion
    else:
        subset = [v for v in vol_exhaustion if vrange <= v['vol'] < next_val]
    # This is getting complex, just show all
    pass

# Show by volume bucket
for lo, hi, label in [(2, 3, '2-3x'), (3, 5, '3-5x'), (5, 999, '5x+')]:
    subset = [v for v in vol_exhaustion if lo <= v['vol'] < hi]
    if subset:
        n = len(subset)
        ups = sum(1 for v in subset if v['nxt_ret'] > 0)
        avg = np.mean([v['nxt_ret'] for v in subset])
        red_nxt = sum(1 for v in subset if v['nxt_ret'] < -0.5)
        green_nxt = sum(1 for v in subset if v['nxt_ret'] > 0.5)
        print(f"  {label}: n={n}, WR={ups/n*100:.1f}%, avg={avg:.3f}%")

# Split by direction
for move_dir, label in [("up", "after big green day"), ("dn", "after big red day")]:
    if move_dir == "up":
        subset = [v for v in vol_exhaustion if v['ret'] > 1.5 and v['close_pos'] > 0.7]
    else:
        subset = [v for v in vol_exhaustion if v['ret'] < -1.5 and v['close_pos'] < 0.3]
    
    if subset:
        n = len(subset)
        ups = sum(1 for v in subset if v['nxt_ret'] > 0)
        avg = np.mean([v['nxt_ret'] for v in subset])
        print(f"  {label}: n={n}, WR={ups/n*100:.1f}%, avg={avg:.3f}%")

# ============================================================
# PATTERN 6: The "Monday-Friday Link" — Cross-week momentum
# ============================================================
print("\n" + "="*70)
print("PATTERN 6: Weekend Effect by Stock — Who bounces from Monday?")
print("="*70)

weekend_data = []
for sym in stocks:
    s = data['stocks'][sym]
    for i in range(1, len(s['dates']) - 2):
        dt = datetime.strptime(s['dates'][i], '%Y-%m-%d')
        if dt.weekday() != 0: continue  # Monday
        
        # Monday performance
        mon_ret = (s['close'][i] - s['open'][i]) / s['open'][i] * 100 if s['open'][i] else 0
        mon_low = s['low'][i]
        mon_close = s['close'][i]
        
        # Tuesday
        tue_o = s['open'][i+1]
        tue_c = s['close'][i+1]
        tue_ret = (tue_c - tue_o) / tue_o * 100 if tue_o else 0
        
        weekend_data.append({
            'sym': sym, 'date': s['dates'][i],
            'mon_ret': round(mon_ret, 2),
            'mon_closed_low': mon_close < (s['high'][i] + s['low'][i]) / 2,
            'mon_range': (s['high'][i] - s['low'][i]) / s['low'][i] * 100 if s['low'][i] else 0,
            'tue_ret': round(tue_ret, 2),
        })

# After a bad Monday, who bounces hardest on Tuesday?
bad_monday = [w for w in weekend_data if w['mon_ret'] < -1]
if bad_monday:
    print(f"  Bad Mondays (< -1%): {len(bad_monday)}")
    
    sym_perf = defaultdict(list)
    for w in bad_monday:
        sym_perf[w['sym']].append(w['tue_ret'])
    
    print(f"\n  {'Stock':<15} {'N':<5} {'TueWR%':<10} {'TueAvg':<10}")
    print("  " + "-"*40)
    for sym, rets in sorted(sym_perf.items(), key=lambda x: np.mean(x[1]), reverse=True):
        n = len(rets)
        if n < 2: continue
        wr = sum(1 for r in rets if r > 0) / n * 100
        avg = np.mean(rets)
        if wr >= 70:
            print(f"  {sym:<15} {n:<5} {wr:<10.1f} {avg:<+10.3f}")

# After a good Monday, who keeps going?
good_monday = [w for w in weekend_data if w['mon_ret'] > 1]
if good_monday:
    print(f"\n  Good Mondays (> +1%): {len(good_monday)}")
    sym_perf = defaultdict(list)
    for w in good_monday:
        sym_perf[w['sym']].append(w['tue_ret'])
    
    for sym, rets in sorted(sym_perf.items(), key=lambda x: np.mean(x[1]), reverse=True)[:10]:
        n = len(rets)
        if n < 2: continue
        wr = sum(1 for r in rets if r > 0) / n * 100
        avg = np.mean(rets)
        print(f"  {sym:<15} {n:<5} {wr:<10.1f} {avg:<+10.3f}")

# ============================================================
# PATTERN 7: Specific Date Anomalies — "Expiry Week Effect"
# ============================================================
print("\n" + "="*70)
print("PATTERN 7: Calendar Date × Stock × Day-of-Week")
print("="*70)

# Find: stock + day_of_week + day_of_month range combo
for sym in stocks:
    s = data['stocks'][sym]
    # Group by (day_of_week, day_of_month_range)
    for dow in range(5):
        for d_lo, d_hi, label in [(1, 7, 'Week1'), (8, 14, 'Week2'), (15, 21, 'Week3'), (22, 31, 'Week4')]:
            rets = []
            for i in range(len(s['dates'])):
                dt = datetime.strptime(s['dates'][i], '%Y-%m-%d')
                if dt.weekday() != dow or not (d_lo <= dt.day <= d_hi): continue
                if i + 1 >= len(s['dates']): continue
                nxt_o = s['open'][i+1]
                nxt_c = s['close'][i+1]
                nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
                rets.append(nxt_ret)
            
            if len(rets) >= 4:
                wr = sum(1 for r in rets if r > 0) / len(rets) * 100
                avg = np.mean(rets)
                if wr >= 80:
                    print(f"  {sym} {['Mon','Tue','Wed','Thu','Fri'][dow]} {label}: n={len(rets)}, WR={wr:.0f}%, avg={avg:+.3f}%")

# ============================================================
# PATTERN 8: The ultimate — specific stock+date+condition
# ============================================================
print("\n" + "="*70)
print("PATTERN 8: The Oracle — Most specific profitable setup with good sample")
print("="*70)

all_results = []

for sym in stocks:
    s = data['stocks'][sym]
    rsi_vals = s.get('rsi14', [])
    
    for i in range(10, len(s['dates']) - 1):
        if i >= len(rsi_vals): continue
        rsi = rsi_vals[i] if rsi_vals[i] is not None else 50
        
        o, c, h, l = s['open'][i], s['close'][i], s['high'][i], s['low'][i]
        ret = (c - o) / o * 100 if o else 0
        close_pos = (c - l) / (h - l) if (h - l) > 0 else 0.5
        range_pct = (h - l) / l * 100 if l else 0
        prev_c = s['close'][i-1] if i > 0 else o
        gap = (o - prev_c) / prev_c * 100 if prev_c else 0
        
        # Volume trend
        vols = np.array(s['volume'], dtype=float)
        avg_vol = np.mean(vols[max(0,i-10):i]) if i >= 10 else np.mean(vols[:i])
        vol_ratio = s['volume'][i] / avg_vol if avg_vol > 0 else 1
        
        # Next day
        nxt_o = s['open'][i+1]
        nxt_c = s['close'][i+1]
        nxt_ret = (nxt_c - nxt_o) / nxt_o * 100 if nxt_o else 0
        
        dt = datetime.strptime(s['dates'][i], '%Y-%m-%d')
        
        all_results.append({
            'sym': sym, 'date': s['dates'][i],
            'rsi': rsi, 'ret': round(ret, 2), 'gap': round(gap, 2),
            'close_pos': round(close_pos, 3), 'range': round(range_pct, 2),
            'vol_ratio': round(vol_ratio, 2),
            'dow': dt.weekday(), 'day': dt.day,
            'nxt_ret': round(nxt_ret, 2),
        })

# Find the best single condition across ALL stocks
# Condition: close_pos > 0.7 AND vol < 0.8 AND RSI 30-50 AND Tuesday
condition_results = []
for sym in stocks:
    subset = [r for r in all_results if r['sym'] == sym and r['close_pos'] > 0.7 and r['vol_ratio'] < 0.8 and 30 <= r['rsi'] <= 50 and r['dow'] == 1]
    if len(subset) >= 3:
        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
        wr = ups / len(subset) * 100
        avg = np.mean([r['nxt_ret'] for r in subset])
        condition_results.append({
            'sym': sym, 'n': len(subset), 'wr': round(wr, 1),
            'avg': round(avg, 3), 'sum': round(sum(r['nxt_ret'] for r in subset), 2)
        })

condition_results.sort(key=lambda x: x['avg'] * x['n'], reverse=True)
print("  Best: Tuesday + ClosePos>0.7 + Vol<0.8 + RSI 30-50")
for r in condition_results[:10]:
    print(f"  {r['sym']:<15} n={r['n']:<3} WR={r['wr']:<6} avg={r['avg']:+.3f}% sum={r['sum']:+.2f}%")

# Now: individual stock's best own condition
print("\n  Each stock's best OWN condition:")
for sym in stocks:
    sym_results = [r for r in all_results if r['sym'] == sym]
    if len(sym_results) < 15: continue
    
    best = None
    best_metric = -999
    
    # Try all combos of (close_pos, rsi, vol, dow)
    for cp_lo, cp_hi, cp_l in [(0, 0.3, 'CP<0.3'), (0.3, 0.5, 'CP0.3-0.5'), (0.5, 0.7, 'CP0.5-0.7'), (0.7, 1, 'CP>0.7')]:
        for rsi_lo, rsi_hi, rsi_l in [(0, 30, 'RSI<30'), (30, 50, 'RSI30-50'), (50, 70, 'RSI50-70'), (70, 999, 'RSI>70')]:
            for vol_lo, vol_hi, vol_l in [(0, 0.7, 'Vol<0.7'), (0.7, 1.5, 'Vol0.7-1.5'), (1.5, 999, 'Vol>1.5')]:
                for dow in [-1, 0, 1, 2, 3, 4]:
                    dow_l = '' if dow == -1 else ['Mon','Tue','Wed','Thu','Fri'][dow]
                    subset = [r for r in sym_results 
                             if cp_lo <= r['close_pos'] < cp_hi 
                             and rsi_lo <= r['rsi'] < rsi_hi
                             and vol_lo <= r['vol_ratio'] < vol_hi
                             and (dow == -1 or r['dow'] == dow)]
                    if len(subset) >= 3:
                        ups = sum(1 for r in subset if r['nxt_ret'] > 0)
                        wr = ups / len(subset) * 100
                        avg = np.mean([r['nxt_ret'] for r in subset])
                        score = avg * wr * np.sqrt(len(subset))  # combined metric
                        if score > best_metric:
                            best_metric = score
                            best = {
                                'cond': f"{cp_l}+{rsi_l}+{vol_l}+{dow_l}" if dow_l else f"{cp_l}+{rsi_l}+{vol_l}",
                                'n': len(subset), 'wr': round(wr, 1), 'avg': round(avg, 3)
                            }
    
    if best and best['n'] >= 4 and best['wr'] >= 70:
        print(f"  {sym:<15} {best['cond']:<40} n={best['n']:<3} WR={best['wr']:<6} avg={best['avg']:+.3f}%")

print("\nDone.")
