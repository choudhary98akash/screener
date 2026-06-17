#!/usr/bin/env python
"""
DEEP DIVE: The single best hidden trade.
Building on findings from hidden_mine2.py, now with exact stock+condition.
"""
import json, itertools, sys
from collections import defaultdict
from datetime import datetime
import numpy as np

data = json.load(open('data.json'))
stocks = list(data['stocks'].keys())
alldates = data['stocks'][stocks[0]]['dates']

def safe(v, default=0):
    return v if v is not None and not (isinstance(v, float) and np.isnan(v)) else default

# Build features (same as before)
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
            'prev_close': s['close'][i-1] if i > 0 else s['open'][i],
        }
        all_recs.append(rec)

# Build feature vectors with next-day returns
features = []
for i in range(10, len(all_recs) - 1):
    r = all_recs[i]
    if i + 1 >= len(all_recs) or all_recs[i+1]['sym'] != r['sym']:
        continue
    
    r_prev = all_recs[i-1]
    
    ret_today = (r['close'] - r['open']) / r['open'] * 100 if r['open'] else 0
    ret_prev = (r_prev['close'] - r_prev['open']) / r_prev['open'] * 100 if r_prev['open'] else 0
    gap = (r['open'] - r['prev_close']) / r['prev_close'] * 100 if r['prev_close'] else 0
    
    # Volume trend
    vol_hist = [all_recs[j]['volume'] for j in range(max(0,i-10), i) if all_recs[j]['volume'] > 0]
    vol_ratio = r['volume'] / np.mean(vol_hist[-10:]) if len(vol_hist) >= 5 and np.mean(vol_hist[-10:]) > 0 else 1
    
    # MA distances
    dist_9 = (r['close'] - r['ema9']) / r['ema9'] * 100 if r['ema9'] and r['ema9'] != 0 else 0
    dist_21 = (r['close'] - r['ema21']) / r['ema21'] * 100 if r['ema21'] and r['ema21'] != 0 else 0
    
    # Range
    range_today = (r['high'] - r['low']) / r['low'] * 100 if r['low'] else 0
    range_prev = (r_prev['high'] - r_prev['low']) / r_prev['low'] * 100 if r_prev['low'] else 0
    
    # Close position in range
    close_pos = (r['close'] - r['low']) / (r['high'] - r['low']) if (r['high'] - r['low']) > 0 else 0.5
    
    # Wicks
    upper_wick = (r['high'] - max(r['open'], r['close'])) / r['high'] * 100 if r['high'] > 0 else 0
    lower_wick = (min(r['open'], r['close']) - r['low']) / r['low'] * 100 if r['low'] > 0 else 0
    body_size = abs(r['close'] - r['open']) / r['open'] * 100 if r['open'] else 0
    
    nxt = all_recs[i+1]
    nxt_ret = (nxt['close'] - nxt['open']) / nxt['open'] * 100 if nxt['open'] else 0
    
    dt = datetime.strptime(r['date'], '%Y-%m-%d')
    
    features.append({
        'sym': r['sym'], 'date': r['date'],
        'rsi': r['rsi14'], 'dist9': dist_9, 'dist21': dist_21,
        'ret_today': round(ret_today, 2), 'ret_prev': round(ret_prev, 2),
        'gap': round(gap, 2),
        'vol_ratio': round(vol_ratio, 2),
        'range': round(range_today, 2), 'range_prev': round(range_prev, 2),
        'close_pos': round(close_pos, 3),
        'upper_wick': round(upper_wick, 2), 'lower_wick': round(lower_wick, 2),
        'body_size': round(body_size, 2),
        'day': dt.day, 'month': dt.month, 'dow': dt.weekday(),
        'nxt_ret': round(nxt_ret, 2), 'nxt_up': nxt_ret > 0,
    })

print(f"Features: {len(features)}")

# ============================================================
# TRADE IDEA 1: "The Tuesday Setup" — Best from earlier
# ============================================================
print("\n" + "="*70)
print("TRADE IDEA 1: Tuesday + RSI 30-50 + Close in Top 30% + Medium Vol")
print("="*70)

tue_setup = [f for f in features if f['dow'] == 1 and 30 <= (f['rsi'] or 50) <= 50 and f['close_pos'] > 0.7]
print(f"  Total: {len(tue_setup)} events")
print(f"  WR: {sum(1 for f in tue_setup if f['nxt_up'])/len(tue_setup)*100:.1f}%")
print(f"  Avg nxt: {np.mean([f['nxt_ret'] for f in tue_setup]):.3f}%")
print(f"  Total sum: {sum(f['nxt_ret'] for f in tue_setup):.2f}%")
print()

# Show best stocks for this
sym_perf = defaultdict(list)
for f in tue_setup:
    sym_perf[f['sym']].append(f['nxt_ret'])
print("  Per-stock breakdown:")
for sym, rets in sorted(sym_perf.items(), key=lambda x: np.mean(x[1]), reverse=True):
    wr = sum(1 for r in rets if r > 0) / len(rets) * 100
    print(f"    {sym}: n={len(rets)}, WR={wr:.0f}%, avg={np.mean(rets):+.3f}%")

# ============================================================
# TRADE IDEA 2: The "Fakeout Follow-Through"
# ============================================================
print("\n" + "="*70)
print("TRADE IDEA 2: Fakeout — what happens the NEXT day after a fakeout?")
print("="*70)

# A fakeout is: gaps up >0.5% but closes negative (or vice versa)
fakeout_events = []
for i in range(1, len(features)):
    f = features[i]
    gap = f['gap']
    ret = f['ret_today']
    is_up_fake = gap > 0.5 and ret < -0.5
    is_dn_fake = gap < -0.5 and ret > 0.5
    
    if is_up_fake or is_dn_fake:
        ft = 'UP_FAKE' if is_up_fake else 'DN_FAKE'
        # Next day
        nxt = f['nxt_ret']
        fakeout_events.append({
            'sym': f['sym'], 'date': f['date'],
            'type': ft, 'gap': gap, 'today_ret': ret,
            'nxt_ret': nxt, 'rsi': f['rsi'],
            'close_pos': f['close_pos'],
        })

for ft in ['UP_FAKE', 'DN_FAKE']:
    subset = [e for e in fakeout_events if e['type'] == ft]
    print(f"\n  {ft} ({len(subset)} events):")
    print(f"    Next day WR: {sum(1 for e in subset if e['nxt_ret']>0)/len(subset)*100:.1f}%")
    print(f"    Next day avg: {np.mean([e['nxt_ret'] for e in subset]):.3f}%")
    
    # Split by RSI
    for lo, hi, label in [(0, 40, 'RSI<40'), (40, 60, 'RSI 40-60'), (60, 100, 'RSI>60')]:
        ss = [e for e in subset if lo <= (e['rsi'] or 50) < hi]
        if ss:
            wr = sum(1 for e in ss if e['nxt_ret']>0)/len(ss)*100
            avg = np.mean([e['nxt_ret'] for e in ss])
            print(f"    {label}: n={len(ss)}, WR={wr:.0f}%, avg={avg:.3f}%")
    
    # Show best individual events
    best = sorted(subset, key=lambda e: e['nxt_ret'], reverse=True)[:5]
    print(f"    Best events:")
    for e in best:
        print(f"      {e['sym']} {e['date']}: gap={e['gap']:+.2f}%, today={e['today_ret']:+.2f}%, nxt={e['nxt_ret']:+.2f}%")

# ============================================================
# TRADE IDEA 3: The "Quiet Breakout" — Narrow range, low vol, then pops
# ============================================================
print("\n" + "="*70)
print("TRADE IDEA 3: Quiet Breakout — 3+ days of tightening range + low vol")
print("="*70)

quiet_breakouts = []
for i in range(5, len(features)):
    f = features[i]
    rsi = f['rsi'] or 50
    
    # Check if range has been narrowing for 3 days
    ranges = []
    for j in range(i-3, i):
        if j >= 0:
            ranges.append(features[j]['range'])
    
    if len(ranges) < 3: continue
    narrowing = all(ranges[k] >= ranges[k+1] for k in range(len(ranges)-1))
    
    if narrowing and f['vol_ratio'] < 0.8 and 30 <= rsi <= 70:
        nxt_ret = f['nxt_ret']
        quiet_breakouts.append({
            'sym': f['sym'], 'date': f['date'],
            'ranges': ranges, 'vol': f['vol_ratio'],
            'rsi': f['rsi'], 'close_pos': f['close_pos'],
            'nxt_ret': nxt_ret,
            'type': 'bull' if nxt_ret > 0 else 'bear'
        })

print(f"  Events: {len(quiet_breakouts)}")
wr = sum(1 for q in quiet_breakouts if q['nxt_ret'] > 0) / len(quiet_breakouts) * 100 if quiet_breakouts else 0
avg = np.mean([q['nxt_ret'] for q in quiet_breakouts]) if quiet_breakouts else 0
print(f"  WR: {wr:.1f}%, avg: {avg:.3f}%")
best = sorted(quiet_breakouts, key=lambda q: q['nxt_ret'], reverse=True)[:5]
for q in best:
    print(f"    {q['sym']} {q['date']}: ranges={[round(r,2) for r in q['ranges']]}, vol={q['vol']}x, nxt={q['nxt_ret']:+.2f}%")

# ============================================================
# TRADE IDEA 4: The "Volume Climax Reversal"
# ============================================================
print("\n" + "="*70)
print("TRADE IDEA 4: Volume Climax — Huge vol after downtrend = capitulation")
print("="*70)

climax = []
for i in range(10, len(features)):
    f = features[i]
    # Stock has been falling (3 red days out of last 5)
    prev_rets = [features[j]['ret_today'] for j in range(i-5, i) if j >= 0]
    red_count = sum(1 for r in prev_rets if r < 0)
    
    # Today shows huge volume and a bounce
    if red_count >= 3 and f['vol_ratio'] > 1.5 and f['ret_today'] > 0 and f['close_pos'] > 0.6:
        climax.append({
            'sym': f['sym'], 'date': f['date'],
            'vol': f['vol_ratio'], 'ret_today': f['ret_today'],
            'red_count': red_count, 'rsi': f['rsi'],
            'nxt_ret': f['nxt_ret'],
            'range': f['range'],
        })

print(f"  Events: {len(climax)}")
if climax:
    wr = sum(1 for c in climax if c['nxt_ret'] > 0) / len(climax) * 100
    avg = np.mean([c['nxt_ret'] for c in climax])
    print(f"  WR: {wr:.1f}%, avg: {avg:.3f}%")
    best = sorted(climax, key=lambda c: c['nxt_ret'], reverse=True)[:5]
    for c in best:
        print(f"    {c['sym']} {c['date']}: vol={c['vol']}x, ret={c['ret_today']:+.2f}%, nxt={c['nxt_ret']:+.2f}%")

# ============================================================
# TRADE IDEA 5: The "Inside Day Break" — specific stock finder
# ============================================================
print("\n" + "="*70)
print("TRADE IDEA 5: After Inside Day Break — the next day follow-through")
print("="*70)

inside_follow = []
for i in range(2, len(features)):
    f = features[i]
    f_prev = features[i-1]
    f_prev2 = features[i-2]
    
    # Was yesterday an inside day?
    prev_range = f_prev['range']
    prev2_range = f_prev2['range']
    
    # Inside day: prev day range < range before it, and today we break out
    if prev_range < prev2_range * 0.7:  # significant contraction
        # Today's direction
        nxt_ret = f['nxt_ret']
        
        # If today broke up (close > prev high of the inside day)
        # We check if today close > previous day's close
        broke_up = f['ret_today'] > 0 and f['close_pos'] > 0.6
        broke_dn = f['ret_today'] < 0 and f['close_pos'] < 0.4
        
        if broke_up or broke_dn:
            inside_follow.append({
                'sym': f['sym'], 'date': f['date'],
                'type': 'UP' if broke_up else 'DN',
                'prev_range': round(prev_range, 2),
                'prev2_range': round(prev2_range, 2),
                'ret_today': f['ret_today'],
                'close_pos': f['close_pos'],
                'vol': f['vol_ratio'],
                'nxt_ret': nxt_ret,
            })

for dtype in ['UP', 'DN']:
    subset = [e for e in inside_follow if e['type'] == dtype]
    if subset:
        wr = sum(1 for e in subset if e['nxt_ret'] > 0) / len(subset) * 100
        avg = np.mean([e['nxt_ret'] for e in subset])
        print(f"  {dtype} break ({len(subset)} events): WR={wr:.1f}%, avg={avg:.3f}%")
        best = sorted(subset, key=lambda e: e['nxt_ret'], reverse=True)[:3]
        for e in best:
            print(f"    {e['sym']} {e['date']}: today={e['ret_today']:+.2f}%, nxt={e['nxt_ret']:+.2f}%")

# ============================================================
# THE WINNER: Most profitable single trade setup
# ============================================================
print("\n" + "="*70)
print("THE SINGLE BEST TRADE: Comprehensive Grid Search")
print("="*70)

# Stock-specific search: for each stock, what's the best next-day predictor?
all_ideas = []

for sym in stocks:
    sf = [f for f in features if f['sym'] == sym]
    if len(sf) < 15: continue
    
    # Try simple conditions per stock
    conditions = [
        ("close_pos>0.7", lambda f: f['close_pos'] > 0.7),
        ("close_pos<0.3", lambda f: f['close_pos'] < 0.3),
        ("range<avg_range", lambda f: f['range'] < np.mean([x['range'] for x in sf])),
        ("range>avg_range*1.5", lambda f: f['range'] > np.mean([x['range'] for x in sf]) * 1.5),
        ("vol<0.7", lambda f: f['vol_ratio'] < 0.7),
        ("vol>1.5", lambda f: f['vol_ratio'] > 1.5),
        ("rsi<40", lambda f: (f['rsi'] or 50) < 40),
        ("rsi>60", lambda f: (f['rsi'] or 50) > 60),
        ("ret_today>1", lambda f: f['ret_today'] > 1),
        ("ret_today<-1", lambda f: f['ret_today'] < -1),
        ("dow=1(Tue)", lambda f: f['dow'] == 1),
        ("dow=2(Wed)", lambda f: f['dow'] == 2),
    ]
    
    for cond_name, cond_func in conditions:
        subset = [f for f in sf if cond_func(f)]
        if len(subset) >= 4:
            ups = sum(1 for f in subset if f['nxt_up'])
            avg_nxt = np.mean([f['nxt_ret'] for f in subset])
            wr = ups / len(subset) * 100
            if wr >= 70 and avg_nxt >= 0.3:
                all_ideas.append({
                    'sym': sym, 'cond': cond_name,
                    'n': len(subset), 'wr': round(wr, 1),
                    'avg': round(avg_nxt, 3),
                    'sum': round(sum(f['nxt_ret'] for f in subset), 2)
                })

# Also try stock + dow + close_pos combos
for sym in stocks:
    sf = [f for f in features if f['sym'] == sym]
    if len(sf) < 15: continue
    for dow in range(5):
        for cp_lo, cp_hi, cp_lbl in [(0, 0.3, 'close_bot'), (0.3, 0.5, 'close_low'), (0.5, 0.7, 'close_mid'), (0.7, 1, 'close_top')]:
            subset = [f for f in sf if f['dow'] == dow and cp_lo <= f['close_pos'] < cp_hi]
            if len(subset) >= 4:
                ups = sum(1 for f in subset if f['nxt_up'])
                avg_nxt = np.mean([f['nxt_ret'] for f in subset])
                wr = ups / len(subset) * 100
                day_name = ['Mon','Tue','Wed','Thu','Fri'][dow]
                if wr >= 75 and avg_nxt >= 0.3:
                    all_ideas.append({
                        'sym': sym, 'cond': f"{day_name}+{cp_lbl}",
                        'n': len(subset), 'wr': round(wr, 1),
                        'avg': round(avg_nxt, 3),
                        'sum': round(sum(f['nxt_ret'] for f in subset), 2)
                    })

# Filter and rank
all_ideas.sort(key=lambda x: x['avg'] * x['n'] / (x['n'] + 5), reverse=True)  # weighted by confidence

print("Top 30 stock-specific setups (WR>=70%, n>=4):")
print(f"{'Stock':<15} {'Condition':<20} {'n':<5} {'WR':<7} {'Avg':<8} {'Sum':<8}")
print("-"*60)
for idea in all_ideas[:30]:
    print(f"{idea['sym']:<15} {idea['cond']:<20} {idea['n']:<5} {idea['wr']:<7} {idea['avg']:+.3f}  {idea['sum']:+.2f}")

# ============================================================
# FINAL ANSWER: The absolute best single trade
# ============================================================
print("\n" + "="*70)
print("FINAL RECOMMENDATION: The Single Trade")
print("="*70)

if all_ideas:
    best = all_ideas[0]
    print(f"\n  Stock: {best['sym']}")
    print(f"  Condition: {best['cond']}")
    print(f"  Events: {best['n']}")
    print(f"  Win Rate: {best['wr']}%")
    print(f"  Avg Return: {best['avg']:+.3f}%")
    print(f"  Total Sum: {best['sum']:+.2f}%")
    
    # Show actual events
    sf = [f for f in features if f['sym'] == best['sym']]
    print(f"\n  Actual events for this setup:")
    # Extract the condition details
    cond_name = best['cond']
    if '+' in cond_name:
        parts = cond_name.split('+')
        dow_map = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4}
        matching = []
        for f in sf:
            match = True
            for p in parts:
                if p in dow_map and f['dow'] != dow_map[p]:
                    match = False
                elif p == 'close_bot' and not (0 <= f['close_pos'] < 0.3):
                    match = False
                elif p == 'close_low' and not (0.3 <= f['close_pos'] < 0.5):
                    match = False
                elif p == 'close_mid' and not (0.5 <= f['close_pos'] < 0.7):
                    match = False
                elif p == 'close_top' and not (0.7 <= f['close_pos'] <= 1):
                    match = False
            if match:
                matching.append(f)
        
        for f in matching:
            day_name = ['Monday','Tuesday','Wednesday','Thursday','Friday'][f['dow']]
            print(f"    {f['date']} ({day_name}): close_pos={f['close_pos']:.2f}, nxt={f['nxt_ret']:+.2f}%")
    
    print(f"\n  THE TRADE: When {best['sym']} satisfies '{best['cond']}', BUY at next day open.")
    print(f"  Expected return: {best['avg']:+.3f}% per trade, {best['wr']:.0f}% win rate.")
    print(f"  Over {best['n']} occurrences: total {best['sum']:+.2f}%.")
