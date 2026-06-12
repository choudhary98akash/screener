import sys, os, json, math, numpy as np, pandas as pd
sys.path.insert(0, ".")

from daily_screener import svg_chart

def gen_html(symbol, base, seed, lo_date, lo_time):
    np.random.seed(seed)
    periods = 375
    idx = pd.date_range(f"{lo_date} 09:15", periods=periods, freq="min")
    opens = base + np.cumsum(np.random.normal(0, max(base/1500, 0.4), periods))
    df = pd.DataFrame({
        "Open": opens,
        "High": opens+abs(np.random.normal(base/2000, base/3000, periods)),
        "Low": opens-abs(np.random.normal(base/2000, base/3000, periods)),
        "Close": opens+np.random.normal(0, base/2000, periods),
        "Volume": np.random.randint(50000, 500000, periods)
    }, index=idx)
    df.loc[df["High"].idxmax(), "High"] = round(base*1.021, 2)
    df.loc[df["Low"].idxmin(), "Low"] = round(base*0.99, 2)

    entry, sl, target = base, round(base*0.99, 2), round(base*1.02, 2)
    times = [ts.strftime("%H:%M") for ts in df.index]
    closes = [round(c, 2) for c in df["Close"].tolist()]
    chart = svg_chart(closes, times, entry, sl, target, "SL", "TARGET HIT")

    result_color = "#4ade80"
    result_icon = "✓"
    open_price, high, low, close = df["Open"].iloc[0], df["High"].max(), df["Low"].min(), df["Close"].iloc[-1]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Report - {symbol} - {lo_date}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0f1e; color:#e2e8f0; font-family:'Segoe UI','Inter',sans-serif; padding:24px; }}
  .container {{ max-width:960px; margin:0 auto; }}
  .header {{ background:linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #334155; border-radius:16px; padding:24px; margin-bottom:20px; }}
  .header h1 {{ font-size:24px; font-weight:800; }}
  .result-badge {{ display:inline-block; padding:6px 16px; border-radius:8px; font-weight:700; font-size:14px; margin-top:8px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:20px; }}
  .card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:16px; }}
  .card .label {{ color:#64748b; font-size:11px; font-family:monospace; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }}
  .card .value {{ font-size:20px; font-weight:700; font-family:monospace; }}
  .card .sub {{ color:#475569; font-size:12px; margin-top:4px; }}
  .chart-card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; margin-bottom:20px; overflow:hidden; }}
  .stats {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .stat {{ background:#1e293b; padding:8px 14px; border-radius:8px; font-size:12px; }}
  .stat span {{ color:#94a3b8; }}
  .stat strong {{ color:#e2e8f0; font-family:monospace; }}
  .footer {{ text-align:center; color:#334155; font-size:11px; font-family:monospace; margin-top:20px; padding:16px; border-top:1px solid #1e293b; }}
</style>
</head>
<body>
<div class="container">
  <div class="header" style="text-align:center;">
    <div style="color:#64748b;font-size:11px;font-family:monospace;letter-spacing:2px;margin-bottom:8px;">NIFTY 50 INTRADAY SCREENER</div>
    <h1>{lo_date} &middot; {symbol}</h1>
    <div style="margin-top:12px;">
      <span class="result-badge" style="background:{result_color}22;color:{result_color};border:1px solid {result_color}44;">
        {result_icon} TARGET_HIT &mdash; +2.00%
      </span>
    </div>
  </div>
  <div class="grid">
    <div class="card"><div class="label">Stock</div><div class="value" style="font-size:28px;">{symbol}</div><div class="sub">NSE &middot; CASH</div></div>
    <div class="card"><div class="label">Score</div><div class="value" style="color:#a78bfa;">7.5</div><div class="sub">ATR 1.6% &middot; Vol Surge 1.5x</div></div>
    <div class="card"><div class="label">Entry Zone</div><div class="value" style="color:#60a5fa;">\u20b9{entry}</div><div class="sub">Close at signal time</div></div>
    <div class="card"><div class="label">Stop Loss</div><div class="value" style="color:#f87171;">\u20b9{sl}</div><div class="sub">-1% &middot; OK</div></div>
    <div class="card"><div class="label">Target</div><div class="value" style="color:#4ade80;">\u20b9{target}</div><div class="sub">+2% &middot; HIT</div></div>
    <div class="card"><div class="label">Risk:Reward</div><div class="value" style="color:#fbbf24;">1:2.0</div><div class="sub">Min 1:2 required</div></div>
  </div>
  <div class="chart-card">{chart}</div>
  <div class="full-card" style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;margin-bottom:20px;">
    <h2 style="font-size:14px;font-family:monospace;text-transform:uppercase;letter-spacing:1px;color:#64748b;margin-bottom:12px;">Day Summary</h2>
    <div class="stats">
      <div class="stat"><span>Open</span> <strong>\u20b9{open_price:.2f}</strong></div>
      <div class="stat"><span>High</span> <strong style="color:#4ade80;">\u20b9{high:.2f}</strong></div>
      <div class="stat"><span>Low</span> <strong style="color:#f87171;">\u20b9{low:.2f}</strong></div>
      <div class="stat"><span>Close</span> <strong>\u20b9{close:.2f}</strong></div>
      <div class="stat"><span>Range</span> <strong>\u20b9{high - low:.2f}</strong></div>
      <div class="stat"><span>Candles</span> <strong>{len(df)}</strong></div>
    </div>
  </div>
  <div class="footer">
    Generated by Nifty 50 Intraday Screener &middot; {lo_date} {lo_time}<br>
    <span style="color:#1e293b;">This is AI-generated research for educational purposes only. Not SEBI registered advice.</span>
  </div>
</div>
</body>
</html>"""
    return html

for args in [
    ("RELIANCE", 2850.0, 42, "2026-06-11", "15-30-00"),
    ("ICICIBANK", 1317.0, 123, "2026-06-12", "21-01-00"),
]:
    html = gen_html(*args)
    fname = f"report/{args[3]}_{args[4]}.html"
    os.makedirs("report", exist_ok=True)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)
    sys.stderr.write(f"  {args[0]}: {fname} ({html.count('svg')} SVG tags)\n")
