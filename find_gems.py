#!/usr/bin/env python
"""
PURE DATA: Find ALL stock+day hidden gems.
No bias, no assumptions, no gap strategy.
Just: which stock on which day consistently makes money?
"""
import json, numpy as np
from collections import defaultdict
from datetime import datetime

data = json.load(open('data.json'))
stocks = list(data['stocks'].keys())
alldates = data['stocks'][stocks[0]]['dates']
day_names = ['Monday','Tuesday','Wednesday','Thursday','Friday']

# ============================================================
# PASS 1: Every stock × every day → buy open, sell close
# ============================================================
print("="*100)
print("PASS 1: STOCK × DAY (Buy Open, Sell Close)")
print("="*100)
print(f"{'Stock':<15} {'Day':<12} {'N':<5} {'Wins':<6} {'Losses':<7} {'WR%':<8} {'AvgRet':<10} {'Total':<10} {'Best':<10} {'Worst':<10} {'Risk(Std)':<10}")
print("-"*100)

results = []
for sym in stocks:
    s = data['stocks'][sym]
    for dow in range(5):
        day_rets = []
        for i in range(len(s['dates'])):
            dt = datetime.strptime(s['dates'][i], '%Y-%m-%d')
            if dt.weekday() != dow: continue
            o, c = s['open'][i], s['close'][i]
            if o == 0: continue
            ret = (c - o) / o * 100
            day_rets.append(ret)
        
        if len(day_rets) >= 8:
            n = len(day_rets)
            wins = sum(1 for r in day_rets if r > 0)
            losses = n - wins
            wr = wins / n * 100
            avg = np.mean(day_rets)
            total = sum(day_rets)
            best = max(day_rets)
            worst = min(day_rets)
            std = np.std(day_rets)
            
            results.append({
                'sym': sym, 'day': day_names[dow], 'dow': dow,
                'n': n, 'wins': wins, 'losses': losses,
                'wr': round(wr, 1), 'avg': round(avg, 3),
                'total': round(total, 2), 'best': round(best, 2),
                'worst': round(worst, 2), 'std': round(std, 3)
            })

# Sort by a combined score: avg * wr * sqrt(n) — favors consistency + frequency
for r in results:
    r['score'] = r['avg'] * r['wr'] * (r['n'] ** 0.5)

results.sort(key=lambda r: r['score'], reverse=True)

# Show top 30
for r in results[:30]:
    print(f"{r['sym']:<15} {r['day']:<12} {r['n']:<5} {r['wins']:<6} {r['losses']:<7} {r['wr']:<8.1f} {r['avg']:<+10.3f} {r['total']:<+10.2f} {r['best']:<+10.2f} {r['worst']:<+10.2f} {r['std']:<10.3f}")

# ============================================================
# PASS 2: Every stock × day × close_position filter
# ============================================================
print("\n" + "="*100)
print("PASS 2: STOCK × DAY × CLOSE POSITION (close in top/bottom of range next day)")
print("="*100)
print("Action: If close_pos > 70% -> buy NEXT day open, sell NEXT day close")
print(f"{'Stock':<15} {'Day':<10} {'Dir':<6} {'N':<5} {'WR%':<8} {'AvgRet':<10} {'Total':<10} {'Worst':<10}")
print("-"*70)

cp_results = []
for sym in stocks:
    s = data['stocks'][sym]
    for dow in range(5):
        for direction, cp_lo, cp_hi, label in [
            ('LONG', 0.7, 1.0, 'close_top'),
            ('SHORT', 0.0, 0.3, 'close_bot'),
        ]:
            next_ret_list = []
            for i in range(len(s['dates']) - 1):
                dt = datetime.strptime(s['dates'][i], '%Y-%m-%d')
                if dt.weekday() != dow: continue
                h, l, c = s['high'][i], s['low'][i], s['close'][i]
                if (h - l) == 0: continue
                close_pos = (c - l) / (h - l)
                
                if cp_lo <= close_pos < cp_hi:
                    nxt_o = s['open'][i+1]
                    nxt_c = s['close'][i+1]
                    if nxt_o == 0: continue
                    nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
                    
                    if direction == 'SHORT':
                        nxt_ret = -nxt_ret  # Short: profit when stock goes down
                    
                    next_ret_list.append(nxt_ret)
            
            if len(next_ret_list) >= 4:
                n = len(next_ret_list)
                wins = sum(1 for r in next_ret_list if r > 0)
                wr = wins / n * 100
                avg = np.mean(next_ret_list)
                total = sum(next_ret_list)
                worst = min(next_ret_list)
                
                cp_results.append({
                    'sym': sym, 'day': day_names[dow],
                    'cond': label, 'dir': direction,
                    'n': n, 'wr': round(wr, 1),
                    'avg': round(avg, 3), 'total': round(total, 2),
                    'worst': round(worst, 2)
                })

cp_results.sort(key=lambda r: r['avg'] * r['wr'] * (r['n'] ** 0.5), reverse=True)

for r in cp_results[:30]:
    prefix = '+' if r['dir'] == 'LONG' else '-'
    print(f"{r['sym']:<15} {r['day']:<10} {r['cond']:<6} {r['n']:<5} {r['wr']:<8.1f} {r['avg']:<+10.3f} {r['total']:<+10.2f} {r['worst']:<+10.2f}")

# ============================================================
# PASS 3: Every stock × day × volume filter
# ============================================================
print("\n" + "="*100)
print("PASS 3: STOCK × DAY × VOLUME (low vol = high conviction)")
print("="*100)
print(f"{'Stock':<15} {'Day':<10} {'VolFilter':<10} {'N':<5} {'WR%':<8} {'AvgRet':<10} {'Total':<10} {'Worst':<10}")
print("-"*70)

vol_results = []
for sym in stocks:
    s = data['stocks'][sym]
    for dow in range(5):
        for v_lo, v_hi, v_label in [
            (0, 0.7, 'vol<0.7x'),
            (0, 1.0, 'vol<1.0x'),
            (0, 999, 'any_vol'),
        ]:
            next_ret_list = []
            for i in range(len(s['dates']) - 1):
                dt = datetime.strptime(s['dates'][i], '%Y-%m-%d')
                if dt.weekday() != dow: continue
                
                vol = s['volume'][i]
                vols = np.array(s['volume'], dtype=float)
                avg_vol = np.mean(vols[max(0,i-10):i]) if i >= 10 and np.mean(vols[max(0,i-10):i]) > 0 else 1
                vol_ratio = vol / avg_vol
                
                if not (v_lo <= vol_ratio < v_hi): continue
                
                nxt_o = s['open'][i+1]
                nxt_c = s['close'][i+1]
                if nxt_o == 0: continue
                nxt_ret = (nxt_c - nxt_o) / nxt_o * 100
                next_ret_list.append(nxt_ret)
            
            if len(next_ret_list) >= 4:
                n = len(next_ret_list)
                wins = sum(1 for r in next_ret_list if r > 0)
                wr = wins / n * 100
                avg = np.mean(next_ret_list)
                total = sum(next_ret_list)
                worst = min(next_ret_list)
                
                vol_results.append({
                    'sym': sym, 'day': day_names[dow],
                    'vol_filter': v_label,
                    'n': n, 'wr': round(wr, 1),
                    'avg': round(avg, 3), 'total': round(total, 2),
                    'worst': round(worst, 2)
                })

vol_results.sort(key=lambda r: r['avg'] * r['wr'] * (r['n'] ** 0.5), reverse=True)

for r in vol_results[:30]:
    print(f"{r['sym']:<15} {r['day']:<10} {r['vol_filter']:<10} {r['n']:<5} {r['wr']:<8.1f} {r['avg']:<+10.3f} {r['total']:<+10.2f} {r['worst']:<+10.2f}")

# ============================================================
# PASS 4: STOCK × STOCK pair (A today → B tomorrow)
# ============================================================
print("\n" + "="*100)
print("PASS 4: STOCK A TODAY → STOCK B TOMORROW (cross-prediction)")
print("="*100)

# Build daily returns
daily_rets = {}
for sym in stocks:
    s = data['stocks'][sym]
    rets = []
    for i in range(len(s['dates'])):
        o, c = s['open'][i], s['close'][i]
        if o == 0:
            rets.append(0)
        else:
            rets.append((c - o) / o * 100)
    daily_rets[sym] = rets

cross_results = []
for a in stocks:
    for b in stocks:
        if a == b: continue
        ra = daily_rets[a]
        rb = daily_rets[b]
        pairs = []
        for i in range(min(len(ra), len(rb)) - 1):
            if abs(ra[i]) > 0.3:  # A moved meaningfully today
                pairs.append(rb[i+1])  # B's return tomorrow
        
        if len(pairs) >= 8:
            n = len(pairs)
            wins = sum(1 for r in pairs if r > 0)
            wr = wins / n * 100
            avg = np.mean(pairs)
            total = sum(pairs)
            
            # For reference: A's return today direction -> B's return tomorrow
            a_up = [rb[i+1] for i in range(min(len(ra), len(rb)) - 1) if ra[i] > 0.3]
            a_dn = [rb[i+1] for i in range(min(len(ra), len(rb)) - 1) if ra[i] < -0.3]
            
            cross_results.append({
                'a': a, 'b': b,
                'n': n, 'wr': round(wr, 1),
                'avg': round(avg, 3), 'total': round(total, 2),
                'avg_when_a_up': round(np.mean(a_up), 3) if a_up else 0,
                'avg_when_a_dn': round(np.mean(a_dn), 3) if a_dn else 0,
            })

cross_results.sort(key=lambda r: r['wr'], reverse=True)

print(f"{'A_today':<15} {'B_tomorrow':<15} {'N':<5} {'WR%':<8} {'AvgB':<10} {'Total':<10} {'B_when_A_up':<13} {'B_when_A_dn':<13}")
print("-"*90)
for r in cross_results[:30]:
    print(f"{r['a']:<15} {r['b']:<15} {r['n']:<5} {r['wr']:<8.1f} {r['avg']:<+10.3f} {r['total']:<+10.2f} {r['avg_when_a_up']:<+13.3f} {r['avg_when_a_dn']:<+13.3f}")

# ============================================================
# SUMMARY: Best of each category
# ============================================================
print("\n" + "="*100)
print("SUMMARY: THE BEST HIDDEN GEMS (n >= 8, WR >= 75%)")
print("="*100)
print()

# Stock × Day
print("CATEGORY 1: Stock × Day (Buy Open, Sell Close)")
print("-"*50)
for r in results:
    if r['n'] >= 8 and r['wr'] >= 75:
        print(f"  {r['sym']:<15} {r['day']:<10} WR={r['wr']:<6.1f}% avg={r['avg']:<+7.3f}% total={r['total']:<+7.2f}% n={r['n']}")

# Stock × Day × ClosePos → Next Day
print("\nCATEGORY 2: Stock × Day × ClosePos → Next Day")
print("-"*50)
for r in cp_results:
    if r['n'] >= 4 and r['wr'] >= 80:
        dir_sym = '+' if r['dir'] == 'LONG' else '-'
        print(f"  {r['sym']:<15} {r['day']:<10} {r['cond']:<10} WR={r['wr']:<6.1f}% avg={r['avg']:<+7.3f}% total={r['total']:<+7.2f}% n={r['n']}")

# Stock × Day × LowVol → Next Day
print("\nCATEGORY 3: Stock × Day × Low Volume → Next Day")
print("-"*50)
for r in vol_results:
    if r['n'] >= 4 and r['wr'] >= 80 and 'low' in r.get('vol_filter', '').lower() or ('any' in r.get('vol_filter', '').lower() and r['wr'] >= 80 and r['n'] >= 6):
        if r['wr'] >= 80:
            print(f"  {r['sym']:<15} {r['day']:<10} {r['vol_filter']:<10} WR={r['wr']:<6.1f}% avg={r['avg']:<+7.3f}% total={r['total']:<+7.2f}% n={r['n']}")

# Cross-prediction
print("\nCATEGORY 4: A Today → B Tomorrow")
print("-"*50)
for r in cross_results:
    if r['n'] >= 15 and r['wr'] >= 65:
        print(f"  {r['a']:<15} -> {r['b']:<15} WR={r['wr']:<6.1f}% avg={r['avg']:<+7.3f}% n={r['n']}")

print("\nDone.")
