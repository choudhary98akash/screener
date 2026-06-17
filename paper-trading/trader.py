#!/usr/bin/env python3
"""Paper trader — RSI regime-aware gap trading. Runs daily via GitHub Actions."""
import json, os, sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import numpy as np

IST = timezone.utc

def compute_rsi(series, period=14):
    deltas = np.diff(series)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    for i in range(period, len(deltas)):
        delta = deltas[i]
        gain = delta if delta > 0 else 0
        loss = -delta if delta < 0 else 0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
    return rsi

def get_rsi_regime(rsi_val):
    if rsi_val is None:
        return "MID"
    if rsi_val < 30:
        return "LOW"
    if rsi_val > 70:
        return "HIGH"
    return "MID"

def decide_trade(rsi_regime, gap, abs_gap, vol_ratio, trade_dow):
    """Core logic: RSI regime overrides day-wise strategy."""
    if not (0.3 <= abs_gap <= 0.8):
        return "NONE", ""

    if rsi_regime == "LOW":
        if gap > 0:
            return "SHORT", "rsi-low gap-up fade"
        return "NONE", ""

    if rsi_regime == "HIGH":
        if gap < 0:
            return "LONG", "rsi-high gap-down buy"
        return "NONE", ""

    # MID regime — use day-wise strategy
    if trade_dow == 0:
        if gap > 0 and vol_ratio < 0.8:
            return "SHORT", "mon gap-up fade"
    elif trade_dow == 1:
        if gap < 0 and vol_ratio < 0.8:
            return "LONG", "tue gap-down reversal"
        if gap > 0 and vol_ratio < 0.8:
            return "SHORT", "tue gap-up fade"
        if gap < 0 and vol_ratio < 1.5:
            return "LONG", "tue gap-down mod vol"
    elif trade_dow == 2:
        if gap < 0:
            return "LONG", "wed gap-down buy"
    elif trade_dow == 3:
        if gap > 0:
            return "SHORT", "thu gap-up short"
    elif trade_dow == 4:
        if gap < 0 and vol_ratio < 0.8:
            return "LONG", "fri gap-down bargain"
        if gap > 0 and vol_ratio > 1.5:
            return "SHORT", "fri gap-up covering"

    return "NONE", ""

def compute_stats(trades):
    if not trades:
        return {"total": 0, "wins": 0, "losses": 0, "winrate": 0, "pnl": 0, "avg_pnl": 0}
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trades if t.get("pnl", 0) < 0)
    total = len(trades)
    pnl = sum(t.get("pnl", 0) for t in trades)
    return {
        "total": total, "wins": wins, "losses": losses,
        "winrate": round(wins / total * 100, 1) if total > 0 else 0,
        "pnl": round(pnl, 2), "avg_pnl": round(pnl / total, 3) if total > 0 else 0
    }

def generate_html(ledger, day_picks, today, day_name, regime_summary=None):
    all_trades = ledger.get("trades", [])
    stats = compute_stats(all_trades)

    day_breakdown = defaultdict(list)
    for t in all_trades:
        day_breakdown[t.get("date", "unknown")].append(t)

    day_stats = []
    for date, trades in sorted(day_breakdown.items()):
        ds = compute_stats(trades)
        day_stats.append({"date": date, **ds})

    cum_pnl = []
    running = 0
    for t in all_trades:
        running += t.get("pnl", 0)
        cum_pnl.append(round(running, 2))

    picks_rows = ""
    verdict = ""
    if day_picks:
        wins = sum(1 for p in day_picks if p.get("pnl", 0) > 0)
        losses = sum(1 for p in day_picks if p.get("pnl", 0) < 0)
        day_pnl = sum(p.get("pnl", 0) for p in day_picks)
        verdict_cls = "green" if day_pnl >= 0 else "red"
        verdict = f'<div class="verdict {verdict_cls}">Verdict: {wins}-{losses} ({wins+losses} trades) · Day PnL: {day_pnl:+.2f}%</div>'

    for p in day_picks:
        cls = "win" if p.get("pnl", 0) > 0 else ("loss" if p.get("pnl", 0) < 0 else "")
        dir_cls = "long" if p.get("trade") == "LONG" else "short"
        picks_rows += f"<tr class='{cls}'><td>{p['stock']}</td><td>{p.get('rsi',0):.0f}</td><td class='{'red' if p['gap']>0 else 'green'}'>{p['gap']:+.2f}%</td><td>{p['vol_ratio']:.1f}x</td><td><span class='badge {dir_cls}'>{p['trade']}</span></td><td>{p.get('rsi_regime','')}</td><td>{p['entry']}</td><td>{p['target']}</td><td>{p['sl']}</td><td>{p['close']}</td><td>{p['result']}</td><td>{p['pnl']:+.2f}%</td></tr>"

    history_rows = ""
    for ds in sorted(day_stats, key=lambda x: x["date"]):
        cls = "win" if ds["pnl"] > 0 else "loss"
        history_rows += f"<tr class='{cls}'><td>{ds['date']}</td><td>{ds['total']}</td><td>{ds['wins']}</td><td>{ds['losses']}</td><td>{ds['winrate']}%</td><td>{ds['pnl']:+.2f}%</td></tr>"

    regime_block = ""
    if regime_summary:
        parts = []
        for k, v in regime_summary.items():
            if v > 0:
                cls = "low-rsi" if k == "LOW" else ("high-rsi" if k == "HIGH" else "")
                label = {"LOW": "RSI<30 (SHORT gap-ups)", "HIGH": "RSI>70 (LONG gap-downs)", "MID": "RSI 30-70 (day-wise)"}.get(k, k)
                parts.append(f"<span class='{cls}'>{label}: {v} stocks</span>")
        if parts:
            regime_block = '<div class="rule">' + " · ".join(parts) + "</div>"

    strategy_rules = (
        "RSI<30 → short gap-ups only. RSI>70 → long gap-downs only. "
        "RSI 30-70 → day-wise: Mon short up, Tue both, Wed long dn, Thu short up, Fri depends."
    )

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Trader — RSI Regime</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0f1117; color:#e1e4e8; padding:20px; }}
h1 {{ font-size:24px; margin-bottom:4px; }}
h2 {{ font-size:18px; margin:20px 0 10px; color:#8b949e; }}
.sub {{ color:#8b949e; font-size:14px; }}
.stats {{ display:flex; gap:12px; flex-wrap:wrap; margin:16px 0; }}
.stat {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px 20px; flex:1; min-width:100px; }}
.stat .num {{ font-size:28px; font-weight:700; }}
.stat .lbl {{ font-size:12px; color:#8b949e; }}
.green {{ color:#3fb950; }} .red {{ color:#f85149; }} .yellow {{ color:#d29922; }} .purple {{ color:#a855f7; }}
table {{ width:100%; border-collapse:collapse; margin:10px 0; font-size:13px; }}
th, td {{ padding:6px 8px; text-align:left; border-bottom:1px solid #21262d; }}
th {{ background:#161b22; color:#8b949e; font-weight:600; position:sticky; top:0; }}
tr:hover {{ background:#1c2128; }}
tr.win {{ border-left:3px solid #3fb950; }}
tr.loss {{ border-left:3px solid #f85149; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.long {{ background:#0d2810; color:#3fb950; }}
.short {{ background:#280d0d; color:#f85149; }}
.chart-box {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:15px; margin:15px 0; }}
.rule {{ background:#1a1d24; padding:10px 15px; border-radius:6px; font-size:13px; color:#8b949e; margin:10px 0; line-height:1.6; }}
.low-rsi {{ color:#f85149; font-weight:600; }}
.high-rsi {{ color:#3fb950; font-weight:600; }}
.verdict {{ font-size:16px; font-weight:700; padding:10px 15px; border-radius:6px; margin:10px 0; }}
.verdict.green {{ background:#0d2810; color:#3fb950; border:1px solid #3fb950; }}
.verdict.red {{ background:#280d0d; color:#f85149; border:1px solid #f85149; }}
.verdict.neutral {{ background:#1a1d24; color:#8b949e; border:1px solid #30363d; }}
.link-bar {{ margin:10px 0; font-size:13px; }}
.link-bar a {{ color:#58a6ff; text-decoration:none; }}
.link-bar a:hover {{ text-decoration:underline; }}
</style></head>
<body>
<h1>Paper Trader — RSI Regime Strategy</h1>
<p class="sub">Running daily via GitHub Actions · {today} · {day_name}</p>

<div class="rule"><b>Rules:</b> {strategy_rules}</div>
{regime_block}
{verdict}

<div class="stats">
<div class="stat"><div class="num">{stats['total']}</div><div class="lbl">Total Trades</div></div>
<div class="stat"><div class="num green">{stats['wins']}</div><div class="lbl">Wins</div></div>
<div class="stat"><div class="num red">{stats['losses']}</div><div class="lbl">Losses</div></div>
<div class="stat"><div class="num {'green' if stats['winrate']>=70 else 'yellow'}">{stats['winrate']}%</div><div class="lbl">Win Rate</div></div>
<div class="stat"><div class="num {'green' if stats['pnl']>=0 else 'red'}">{stats['pnl']:+.2f}%</div><div class="lbl">Total PnL</div></div>
<div class="stat"><div class="num {('green' if stats['avg_pnl']>=0 else 'red')}">{stats['avg_pnl']:+.3f}%</div><div class="lbl">Avg PnL/Trade</div></div>
</div>

<div class="chart-box"><canvas id="cumChart" height="80"></canvas></div>
<div class="chart-box"><canvas id="dayChart" height="80"></canvas></div>

<h2>Today's Picks ({len(day_picks)} trades)</h2>
<table><tr><th>Stock</th><th>RSI</th><th>Gap</th><th>Vol</th><th>Trade</th><th>Regime</th><th>Entry</th><th>Target</th><th>SL</th><th>Close</th><th>Result</th><th>PnL</th></tr>{picks_rows}</table>

<h2>Daily History</h2>
<table><tr><th>Date</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>PnL</th></tr>{history_rows}</table>

<div class="link-bar">
<a href="https://github.com/choudhary98akash/screener/blob/main/paper_trader/trader.py">Strategy Source</a> ·
<a href="https://github.com/choudhary98akash/screener/blob/main/strategy-day-wise.md">Playbook</a> ·
<a href="https://github.com/choudhary98akash/screener/blob/main/findings.md">Findings</a> ·
<a href="https://github.com/choudhary98akash/screener/actions">Workflow Runs</a>
</div>

<script>
const cumData = {json.dumps(cum_pnl)};
const dayLabels = {json.dumps([ds['date'] for ds in sorted(day_stats, key=lambda x: x['date'])])};
const dayPnls = {json.dumps([ds['pnl'] for ds in sorted(day_stats, key=lambda x: x['date'])])};
const dayWrs = {json.dumps([ds['winrate'] for ds in sorted(day_stats, key=lambda x: x['date'])])};

new Chart(document.getElementById('cumChart'), {{
    type: 'line',
    data: {{ labels: cumData.map((_,i)=>i+1), datasets: [{{ label:'Cumulative PnL %', data:cumData, borderColor:'#3fb950', backgroundColor:'rgba(63,185,80,0.1)', fill:true, tension:0.3 }}] }},
    options: {{ responsive:true, plugins:{{ legend:{{ display:false }}, title:{{ display:true, text:'Cumulative PnL', color:'#8b949e' }} }}, scales:{{ x:{{ ticks:{{ color:'#8b949e' }} }}, y:{{ ticks:{{ color:'#8b949e' }} }} }} }}
}});

new Chart(document.getElementById('dayChart'), {{
    type: 'bar',
    data: {{ labels: dayLabels, datasets: [
        {{ label:'Daily PnL %', data:dayPnls, backgroundColor:dayPnls.map(v=>v>=0?'rgba(63,185,80,0.7)':'rgba(248,81,73,0.7)'), borderColor:dayPnls.map(v=>v>=0?'#3fb950':'#f85149'), borderWidth:1 }},
        {{ label:'Win Rate %', data:dayWrs, type:'line', borderColor:'#d29922', backgroundColor:'rgba(210,153,34,0.1)', fill:false, tension:0.3, yAxisID:'y1' }}
    ] }},
    options: {{ responsive:true, plugins:{{ title:{{ display:true, text:'Daily Performance', color:'#8b949e' }} }}, scales:{{ x:{{ ticks:{{ color:'#8b949e' }} }}, y:{{ ticks:{{ color:'#8b949e' }}, position:'left' }}, y1:{{ ticks:{{ color:'#d29922' }}, position:'right', max:100, grid:{{ drawOnChartArea:false }} }} }} }}
}});
</script>
<p style="color:#484f58;font-size:12px;margin-top:20px">Auto-generated · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
</body></html>'''

    return html

def run_paper_trade():
    import yfinance as yf

    today = datetime.now()
    dow = today.weekday()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = day_names[dow]

    if dow >= 5:
        print(f"Weekend ({day_name}) — no trading")
        return

    print(f"Running paper trade for {day_name} ({today.strftime('%Y-%m-%d')})")

    symbols = [
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
    stock_names = {s: s.replace('.NS','') for s in symbols}

    today_str = today.strftime('%Y-%m-%d')
    end_str = (today + timedelta(days=2)).strftime('%Y-%m-%d')
    start_str = (today - timedelta(days=35)).strftime('%Y-%m-%d')

    print("Fetching data...")
    try:
        df = yf.download(symbols, start=start_str, end=end_str, interval='1d', progress=False, auto_adjust=True)
    except Exception as e:
        print(f"Fetch error: {e}")
        return

    available_dates = [d.strftime('%Y-%m-%d') for d in df.index]
    print(f"Available dates: {available_dates}")

    if today_str in available_dates and dow < 5:
        trade_date = today_str
    else:
        completed_dates = [d for d in available_dates if d < today_str]
        if not completed_dates:
            completed_dates = available_dates
        trade_date = completed_dates[-1]
    trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
    trade_dow = trade_dt.weekday()

    print(f"Trade date: {trade_date} ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][trade_dow]})")
    print(f"System says today is {today_str} ({day_name}) — trading on {trade_date}")

    idx = available_dates.index(trade_date)
    prev_date = available_dates[idx - 1] if idx > 0 else available_dates[0]

    ledger_path = "paper_trader/ledger.json"
    if os.path.exists(ledger_path):
        ledger = json.load(open(ledger_path))
    else:
        ledger = {"trades": [], "runs": []}

    actual_day_name = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][trade_dow]

    existing_dates = {t.get("date") for t in ledger["trades"]}
    if trade_date in existing_dates:
        print(f"Already processed {trade_date} — skipping")
    else:
        try:
            yclose = df['Close'].loc[prev_date]
            topen = df['Open'].loc[trade_date]
            thigh = df['High'].loc[trade_date]
            tlow = df['Low'].loc[trade_date]
            tclose = df['Close'].loc[trade_date]
            tvol = df['Volume'].loc[trade_date]
            close_hist = df['Close'].loc[:trade_date]
        except Exception as e:
            print(f"Data error: {e}")
            return

        gap_directions = []
        for sym in symbols:
            try:
                pc2 = float(yclose[sym])
                op2 = float(topen[sym])
                if pc2 != 0 and not np.isnan(pc2) and not np.isnan(op2):
                    g2 = (op2 - pc2) / pc2 * 100
                    if abs(g2) >= 0.15:
                        gap_directions.append(g2)
            except:
                continue
        pct_up = sum(1 for g in gap_directions if g > 0) / len(gap_directions) * 100 if gap_directions else 50
        print(f"Market context: {len(gap_directions)} stocks with gaps, {pct_up:.0f}% gap-up")

        vol_hist = df['Volume'].loc[:prev_date]

        day_picks = []
        for sym in symbols:
            name = stock_names[sym]
            try:
                pc = float(yclose[sym])
                op = float(topen[sym])
                hp = float(thigh[sym])
                lp = float(tlow[sym])
                cp = float(tclose[sym])
                vt = float(tvol[sym])
            except:
                continue
            if pc == 0 or np.isnan(pc):
                continue

            gap = (op - pc) / pc * 100
            abs_gap = abs(gap)

            vols = [float(v) for v in vol_hist[sym].dropna() if not np.isnan(float(v))]
            avg_vol = np.mean(vols[-10:]) if len(vols) >= 10 else np.mean(vols) if len(vols) > 0 else vt
            vol_ratio = vt / avg_vol if avg_vol > 0 else 1

            close_prices = [float(c) for c in close_hist[sym].dropna() if not np.isnan(float(c))]
            rsi_val = compute_rsi(np.array(close_prices)) if len(close_prices) >= 15 else None
            rsi_regime = get_rsi_regime(rsi_val)

            trade, direction = decide_trade(rsi_regime, gap, abs_gap, vol_ratio, trade_dow)

            pnl = 0
            result = "SKIP"
            target_price = 0
            sl_price = 0

            if trade != "NONE":
                target_price = op * (1 + abs_gap * 0.5 / 100) if trade == "LONG" else op * (1 - abs_gap * 0.5 / 100)
                sl_price = op * (1 - 0.5 / 100) if trade == "LONG" else op * (1 + 0.5 / 100)

                if trade == "LONG":
                    gap_filled_check = hp >= pc
                    sl_hit = lp <= sl_price
                else:
                    gap_filled_check = lp <= pc
                    sl_hit = hp >= sl_price

                if gap_filled_check:
                    result = "FILLED"
                    if trade == "LONG":
                        achieved = min(hp, target_price)
                        pnl = round(max(0, (achieved - op) / op * 100), 2)
                    else:
                        achieved = max(lp, target_price)
                        pnl = round(max(0, (op - achieved) / op * 100), 2)
                elif sl_hit:
                    pnl = -0.5
                    result = "STOPPED"
                else:
                    pnl = round(((cp - op) / op * 100) if trade == "LONG" else ((op - cp) / op * 100), 2)
                    result = "OPEN"

                day_picks.append({
                    "stock": name, "rsi": round(rsi_val, 1) if rsi_val else 0,
                    "gap": round(gap, 2), "abs_gap": round(abs_gap, 2),
                    "vol_ratio": round(vol_ratio, 2), "trade": trade,
                    "rsi_regime": rsi_regime,
                    "entry": round(op, 2), "target": round(target_price, 2),
                    "sl": round(sl_price, 2), "close": round(cp, 2),
                    "result": result, "pnl": pnl, "direction": direction,
                    "date": trade_date, "day": actual_day_name,
                    "market_tide": f"{pct_up:.0f}% up"
                })

        for p in day_picks:
            ledger["trades"].append(p)
        ledger["runs"].append({"date": trade_date, "day": day_name, "trades": len(day_picks)})

        with open(ledger_path, "w") as f:
            json.dump(ledger, f, indent=2)

        print(f"Recorded {len(day_picks)} trades for {trade_date}")

    todays_picks = [t for t in ledger["trades"] if t.get("date") == trade_date]

    regime_summary = {"LOW": 0, "MID": 0, "HIGH": 0}
    for p in todays_picks:
        r = p.get("rsi_regime", "")
        if r in regime_summary:
            regime_summary[r] += 1

    html = generate_html(ledger, todays_picks, trade_date, actual_day_name, regime_summary)
    html_path = "paper_trader/index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard: {html_path}")
    print(f"Root copy: paper-trading.html")

    all_trades = ledger["trades"]
    wins = sum(1 for t in all_trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in all_trades if t.get("pnl", 0) < 0)
    total_pnl = sum(t.get("pnl", 0) for t in all_trades)
    print(f"\n{'='*50}")
    print(f"  PAPER TRADING SUMMARY")
    print(f"{'='*50}")
    print(f"  Total runs: {len(ledger['runs'])}")
    print(f"  Total trades: {len(all_trades)}")
    print(f"  Wins: {wins}, Losses: {losses}")
    wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    print(f"  Win rate: {wr:.1f}%")
    print(f"  Total PnL: {total_pnl:+.2f}%")
    print(f"  Today: {len(todays_picks)} trades")
    print(f"{'='*50}")

if __name__ == "__main__":
    run_paper_trade()
