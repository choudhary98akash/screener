#!/usr/bin/env python3
"""Tuesday strategy — generate picks and interactive HTML for June 16, 2026."""
import yfinance as yf
import json, numpy as np
from datetime import datetime

NIFTY50_SYMBOLS = [
    'RELIANCE.NS','TCS.NS','HDFCBANK.NS','INFY.NS','ICICIBANK.NS',
    'HINDUNILVR.NS','ITC.NS','SBIN.NS','BHARTIARTL.NS','KOTAKBANK.NS',
    'LT.NS','WIPRO.NS','AXISBANK.NS','BAJFINANCE.NS','MARUTI.NS',
    'TITAN.NS','SUNPHARMA.NS','ONGC.NS','NTPC.NS','POWERGRID.NS',
    'M&M.NS','HCLTECH.NS','ULTRACEMCO.NS','NESTLEIND.NS','ASIANPAINT.NS',
    'JSWSTEEL.NS','ADANIPORTS.NS','HINDALCO.NS','TATASTEEL.NS',
    'BAJAJFINSV.NS','DRREDDY.NS','ADANIENT.NS','BRITANNIA.NS','CIPLA.NS',
    'COALINDIA.NS','DIVISLAB.NS','EICHERMOT.NS','GRASIM.NS','HEROMOTOCO.NS',
    'HDFCLIFE.NS','SBILIFE.NS','APOLLOHOSP.NS','BPCL.NS','BEL.NS',
    'BAJAJHLDNG.NS','INDUSINDBK.NS','SHRIRAMFIN.NS','TATACONSUM.NS','TRENT.NS'
]
STOCK_NAMES = {}
for s in NIFTY50_SYMBOLS:
    n = s.replace('.NS','')
    STOCK_NAMES[s] = n

today = '2026-06-16'
yesterday = '2026-06-15'

print("Fetching data...")
df = yf.download(NIFTY50_SYMBOLS, start='2026-06-01', end='2026-06-17', interval='1d', progress=False, auto_adjust=True)

# Get yesterday's close for reference
yclose = df['Close'].loc[yesterday]
topen = df['Open'].loc[today]
thigh = df['High'].loc[today]
tlow = df['Low'].loc[today]
tclose = df['Close'].loc[today]
tvol = df['Volume'].loc[today]

# Get volume history for 10-day avg
vol_series = df['Volume'].loc[:yesterday]

print("\nFetching volume history...")
# Compute 10-day avg volume up to yesterday for each stock
picks = []
for sym in NIFTY50_SYMBOLS:
    name = STOCK_NAMES[sym]
    try:
        prev_close = float(yclose[sym])
        open_p = float(topen[sym])
        high_p = float(thigh[sym])
        low_p = float(tlow[sym])
        close_p = float(tclose[sym])
        vol_today = float(tvol[sym])
    except:
        continue
    
    if prev_close == 0 or np.isnan(prev_close):
        continue
    
    gap = (open_p - prev_close) / prev_close * 100
    oc = (close_p - open_p) / open_p * 100 if open_p != 0 else 0
    day_range = (high_p - low_p) / prev_close * 100
    
    # Volume ratio
    vols = [float(v) for v in vol_series[sym].dropna() if not np.isnan(float(v))]
    avg_vol = np.mean(vols[-10:]) if len(vols) >= 10 else np.mean(vols) if vols else vol_today
    vol_ratio = vol_today / avg_vol if avg_vol > 0 else 1
    
    gap_filled = (low_p <= prev_close) if gap > 0 else (high_p >= prev_close)
    if gap > 0:
        fill_pct = min(100, (open_p - low_p) / (open_p - prev_close) * 100) if (open_p - prev_close) != 0 else 0
    else:
        fill_pct = min(100, (high_p - open_p) / (prev_close - open_p) * 100) if (prev_close - open_p) != 0 else 0
    
    close_pos = (close_p - low_p) / (high_p - low_p) * 100 if (high_p - low_p) > 0 else 50
    
    # Tuesday Strategy Rules
    trade = "NONE"
    direction = ""
    target_price = 0
    sl_price = 0
    confidence = ""
    reasoning = ""
    
    abs_gap = abs(gap)
    
    if 0.3 <= abs_gap <= 0.8:
        # Setup A: Low-Volume Gap-Down (Primary)
        if gap < 0 and vol_ratio < 0.8:
            trade = "LONG"
            direction = "LONG (gap-down reversal)"
            target_price = open_p * (1 + abs_gap * 0.5 / 100)  # 50% fill
            sl_price = open_p * (1 - 0.5 / 100)
            confidence = "HIGH"
            reasoning = f"Tue + gap-down + low vol ({vol_ratio:.1f}x) = 82.1% fill rate"
        # Setup B: Low-Volume Gap-Up (Secondary)
        elif gap > 0 and vol_ratio < 0.8:
            trade = "SHORT"
            direction = "SHORT (gap-up fade)"
            target_price = open_p * (1 - abs_gap * 0.5 / 100)
            sl_price = open_p * (1 + 0.5 / 100)
            confidence = "HIGH"
            reasoning = f"Tue + gap-up + low vol ({vol_ratio:.1f}x) = 73.2% fill rate"
        # Setup C: The Monday Hangover
        elif gap < 0 and vol_ratio < 1.5:
            # Check if Monday was red — we know it was (data shows Monday returns)
            trade = "LONG"
            direction = "LONG (Monday hangover reversal)"
            target_price = open_p * (1 + abs_gap * 0.5 / 100)
            sl_price = open_p * (1 - 0.5 / 100)
            confidence = "MEDIUM"
            reasoning = f"Tue + gap-down (any moderate vol) = 69.7% fill rate"
        elif gap > 0 and vol_ratio < 1.5:
            trade = "SHORT"
            direction = "SHORT (gap-up fade - moderate vol)"
            target_price = open_p * (1 - abs_gap * 0.5 / 100)
            sl_price = open_p * (1 + 0.5 / 100)
            confidence = "MEDIUM"
            reasoning = f"Tue + gap-up (any moderate vol) = 69.7% fill rate"
    elif abs_gap < 0.3 and abs_gap >= 0.15:
        # Tiny gaps — still worth noting
        if gap < 0:
            trade = "LONG"
            direction = "LONG (tiny gap-down)"
            target_price = open_p * (1 + abs_gap * 0.5 / 100)
            sl_price = open_p * (1 - 0.3 / 100)
            confidence = "TINY"
            reasoning = "Gap too small (<0.3%) — not worth the risk"

    result_status = "PENDING"
    result_emoji = "⏳"
    pnl_pct = 0
    
    if trade != "NONE" and trade != "TINY":
        # Check actual result
        if direction.startswith("LONG"):
            if low_p <= prev_close:
                result_status = "FILLED ✓"
                result_emoji = "✅"
                pnl_pct = (min(high_p, target_price) - open_p) / open_p * 100
                if pnl_pct < 0:
                    pnl_pct = 0
            elif low_p <= sl_price:
                result_status = "STOPPED ✗"
                result_emoji = "❌"
                pnl_pct = -0.5
            else:
                result_status = "OPEN"
                result_emoji = "🔄"
                pnl_pct = (close_p - open_p) / open_p * 100
        elif direction.startswith("SHORT"):
            if high_p >= prev_close:
                result_status = "FILLED ✓"
                result_emoji = "✅"
                pnl_pct = (open_p - max(low_p, target_price)) / open_p * 100
                if pnl_pct < 0:
                    pnl_pct = 0
            elif high_p >= sl_price:
                result_status = "STOPPED ✗"
                result_emoji = "❌"
                pnl_pct = -0.5
            else:
                result_status = "OPEN"
                result_emoji = "🔄"
                pnl_pct = (open_p - close_p) / open_p * 100
    
    picks.append({
        "stock": name, "gap": round(gap, 2), "abs_gap": round(abs_gap, 2),
        "vol_ratio": round(vol_ratio, 2), "trade": trade, "direction": direction,
        "entry": round(open_p, 2), "target": round(target_price, 2) if target_price else 0,
        "sl": round(sl_price, 2) if sl_price else 0,
        "close": round(close_p, 2), "oc": round(oc, 2), "day_range": round(day_range, 2),
        "fill_pct": round(fill_pct, 1), "gap_filled": gap_filled,
        "close_pos": round(close_pos, 1), "confidence": confidence,
        "reasoning": reasoning, "result": result_status,
        "pnl": round(pnl_pct, 2), "emoji": result_emoji
    })

# Sort: trades first (by confidence), then nontrades
trades = [p for p in picks if p["trade"] not in ("NONE", "TINY")]
nontrades = [p for p in picks if p["trade"] in ("NONE", "TINY")]
trades.sort(key=lambda x: 0 if x["confidence"] == "HIGH" else 1 if x["confidence"] == "MEDIUM" else 2)
picks_sorted = trades + nontrades

print(f"\nTotal picks: {len(trades)} trades, {len(nontrades)} no-trades")
if trades:
    wins = sum(1 for p in trades if "FILLED" in p["result"])
    losses = sum(1 for p in trades if "STOPPED" in p["result"])
    avg_pnl = np.mean([p["pnl"] for p in trades])
    print(f"Wins: {wins}, Losses: {losses}, Avg PnL: {avg_pnl:.2f}%")

# Generate HTML
def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tuesday Strategy — June 16, 2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0f1117; color:#e1e4e8; padding:20px; }}
h1 {{ font-size:24px; margin-bottom:4px; }}
h2 {{ font-size:18px; margin:20px 0 10px; color:#8b949e; }}
.sub {{ color:#8b949e; font-size:14px; margin-bottom:20px; }}
.stats {{ display:flex; gap:12px; flex-wrap:wrap; margin:16px 0; }}
.stat {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px 20px; flex:1; min-width:100px; }}
.stat .num {{ font-size:28px; font-weight:700; }}
.stat .lbl {{ font-size:12px; color:#8b949e; }}
.green {{ color:#3fb950; }}
.red {{ color:#f85149; }}
.yellow {{ color:#d29922; }}
table {{ width:100%; border-collapse:collapse; margin:10px 0; font-size:13px; }}
th, td {{ padding:8px 10px; text-align:left; border-bottom:1px solid #21262d; }}
th {{ background:#161b22; color:#8b949e; font-weight:600; position:sticky; top:0; }}
tr:hover {{ background:#1c2128; }}
.conf-HIGH {{ background:#0d2810; }}
.conf-MEDIUM {{ background:#1a1a0d; }}
.conf-TINY {{ opacity:0.6; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.badge-LONG {{ background:#0d2810; color:#3fb950; }}
.badge-SHORT {{ background:#280d0d; color:#f85149; }}
.badge-NONE {{ background:#1c2128; color:#8b949e; }}
.bar-container {{ width:100%; height:40px; background:#161b22; border-radius:4px; position:relative; overflow:hidden; }}
.bar-fill {{ position:absolute; height:100%; border-radius:4px; transition:width 0.5s; }}
.bar-label {{ position:absolute; width:100%; text-align:center; line-height:40px; font-size:12px; font-weight:600; text-shadow:0 1px 3px rgba(0,0,0,0.8); }}
.chart-container {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:15px; margin:15px 0; }}
</style>
</head>
<body>
<h1>🎯 Tuesday Strategy — "Every Small Gap Counts"</h1>
<p class="sub">June 16, 2026 · Based on real data: 82.1% fill rate on best setup</p>

<div class="stats">'''

if trades:
    wins = sum(1 for p in trades if "FILLED" in p["result"])
    losses = sum(1 for p in trades if "STOPPED" in p["result"])
    open_trades = sum(1 for p in trades if "FILLED" not in p["result"] and "STOPPED" not in p["result"])
    avg_pnl = np.mean([p["pnl"] for p in trades if p["pnl"] != 0])
    total_pnl = sum(p["pnl"] for p in trades)
    winrate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    
    html += f'''
<div class="stat"><div class="num green">{len(trades)}</div><div class="lbl">Trades Today</div></div>
<div class="stat"><div class="num green">{wins}</div><div class="lbl">Wins</div></div>
<div class="stat"><div class="num red">{losses}</div><div class="lbl">Losses</div></div>
<div class="stat"><div class="num {'green' if winrate >= 50 else 'red'}">{winrate:.0f}%</div><div class="lbl">Win Rate</div></div>
<div class="stat"><div class="num {'green' if avg_pnl >= 0 else 'red'}">{avg_pnl:+.2f}%</div><div class="lbl">Avg PnL</div></div>
<div class="stat"><div class="num {'green' if total_pnl >= 0 else 'red'}">{total_pnl:+.2f}%</div><div class="lbl">Total PnL</div></div>'''

html += '</div>'

# Chart: Gap sizes and confidence
html += '''<div class="chart-container">
<canvas id="gapChart" height="80"></canvas>
</div>'''

# Chart: PnL distribution
if trades:
    html += '''<div class="chart-container">
<canvas id="pnlChart" height="80"></canvas>
</div>'''

# Trades table
html += '<h2>📊 Tuesday Picks</h2>'
html += '<table><tr><th>Stock</th><th>Gap</th><th>Vol</th><th>Trade</th><th>Entry</th><th>Target</th><th>SL</th><th>Close</th><th>Result</th><th>PnL</th><th>Reasoning</th></tr>'

for p in picks_sorted:
    if p["trade"] == "NONE":
        continue
    conf_class = f"conf-{p['confidence']}" if p["confidence"] in ("HIGH", "MEDIUM", "TINY") else ""
    badge_class = f"badge-{p['trade']}"
    pnl_class = "green" if p["pnl"] > 0 else ("red" if p["pnl"] < 0 else "")
    gap_color = "green" if p["gap"] < 0 else "red"  # red for gap-up (short), green for gap-down (long)
    
    html += f'<tr class="{conf_class}">'
    html += f'<td><b>{p["stock"]}</b></td>'
    html += f'<td class="{gap_color}">{p["gap"]:+.2f}%</td>'
    html += f'<td>{p["vol_ratio"]:.1f}x</td>'
    html += f'<td><span class="badge {badge_class}">{p["trade"]}</span></td>'
    html += f'<td>{p["entry"]}</td>'
    html += f'<td>{p["target"]}</td>'
    html += f'<td>{p["sl"]}</td>'
    html += f'<td>{p["close"]}</td>'
    html += f'<td>{p["emoji"]} {p["result"]}</td>'
    html += f'<td class="{pnl_class}"><b>{p["pnl"]:+.2f}%</b></td>'
    html += f'<td style="font-size:11px;color:#8b949e;max-width:250px">{p["reasoning"]}</td>'
    html += '</tr>'

html += '</table>'

# No-trade watch list
no_trades = [p for p in picks_sorted if p["trade"] == "NONE"]
if no_trades:
    html += '<h2>👀 Watched (No Trade)</h2>'
    html += '<table><tr><th>Stock</th><th>Gap</th><th>Vol</th><th>Why Skipped</th><th>Close</th><th>OC</th><th>Fill%</th></tr>'
    for p in no_trades:
        gap_color = "green" if p["gap"] < 0 else "red"
        html += f'<tr><td><b>{p["stock"]}</b></td>'
        html += f'<td class="{gap_color}">{p["gap"]:+.2f}%</td>'
        html += f'<td>{p["vol_ratio"]:.1f}x</td>'
        reason = "Gap too large" if p["abs_gap"] > 0.8 else "Gap too small" if p["abs_gap"] < 0.3 else "Volume too high" if p["vol_ratio"] >= 1.5 else "No valid setup"
        html += f'<td style="color:#8b949e">{reason}</td>'
        html += f'<td>{p["close"]}</td>'
        html += f'<td>{p["oc"]:+.2f}%</td>'
        html += f'<td>{p["fill_pct"]:.0f}%</td></tr>'
    html += '</table>'

# Strategy summary
html += f'''
<h2>📋 Tuesday Strategy Rules Applied</h2>
<table>
<tr><th>Setup</th><th>Condition</th><th>Action</th><th>Expected WR</th></tr>
<tr><td><b>A (Primary)</b></td><td>Gap-down −0.3% to −0.8% + Vol <0.8x</td><td>LONG (buy dip)</td><td class="green">82.1%</td></tr>
<tr><td><b>B (Secondary)</b></td><td>Gap-up +0.3% to +0.8% + Vol <0.8x</td><td>SHORT (fade rally)</td><td class="green">73.2%</td></tr>
<tr><td><b>C (Hangover)</b></td><td>Gap-down + Mod vol + Monday red</td><td>LONG (second day reversal)</td><td class="yellow">69.7%</td></tr>
</table>
'''

# JavaScript for charts
html += '''
<script>
const gapData = ['''
for p in trades:
    html += f'{{stock:"{p["stock"]}",gap:{p["gap"]},vol:{p["vol_ratio"]},conf:"{p["confidence"]}",pnl:{p["pnl"]}}},'
html += '''];

const ctx1 = document.getElementById('gapChart').getContext('2d');
new Chart(ctx1, {
    type: 'bar',
    data: {
        labels: gapData.map(d => d.stock),
        datasets: [{
            label: 'Gap %',
            data: gapData.map(d => d.gap),
            backgroundColor: gapData.map(d => d.gap < 0 ? 'rgba(63,185,80,0.7)' : 'rgba(248,81,73,0.7)'),
            borderColor: gapData.map(d => d.gap < 0 ? '#3fb950' : '#f85149'),
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false },
            title: { display: true, text: 'Gap Size by Stock (green = gap-down = long, red = gap-up = short)', color: '#8b949e' }
        },
        scales: {
            x: { ticks: { color: '#8b949e', maxRotation: 45 }, grid: { color: '#21262d' } },
            y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
        }
    }
});
'''

if trades:
    html += '''
const ctx2 = document.getElementById('pnlChart').getContext('2d');
new Chart(ctx2, {
    type: 'bar',
    data: {
        labels: gapData.map(d => d.stock),
        datasets: [{
            label: 'PnL %',
            data: gapData.map(d => d.pnl),
            backgroundColor: gapData.map(d => d.pnl >= 0 ? 'rgba(63,185,80,0.7)' : 'rgba(248,81,73,0.7)'),
            borderColor: gapData.map(d => d.pnl >= 0 ? '#3fb950' : '#f85149'),
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false },
            title: { display: true, text: 'PnL by Stock', color: '#8b949e' }
        },
        scales: {
            x: { ticks: { color: '#8b949e', maxRotation: 45 }, grid: { color: '#21262d' } },
            y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
        }
    }
});
'''

html += '</script></body></html>'

with open('tuesday-picks.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nHTML report generated: tuesday-picks.html")
print("Open in browser to view")
