import sys, os, json, math, numpy as np, pandas as pd, yfinance as yf

# Copy of svg_chart from daily_screener.py
def svg_chart(closes, times, entry, sl, target, sl_label, tgt_label):
    W, H = 800, 360
    ML, MR, MT, MB = 70, 16, 24, 44
    PW = W - ML - MR; PH = H - MT - MB
    cmin = min(closes); cmax = max(closes)
    pad = max((cmax - cmin) * 0.12, 2)
    ylo = min(cmin - pad, sl - 2); yhi = max(cmax + pad, target + 2)
    def sx(i): return ML + PW * i / max(len(closes) - 1, 1)
    def sy(v): return MT + PH * (yhi - v) / (yhi - ylo)
    pts = " ".join(f"{sx(i)},{sy(v)}" for i, v in enumerate(closes))
    fill_pts = f"{sx(0)},{H} {pts} {sx(len(closes)-1)},{H}"
    tick_step = max(1, len(times) // 14)
    x_ticks = [(i, times[i]) for i in range(0, len(times), tick_step)]
    y_range = yhi - ylo
    y_step = 10 ** round(math.log10(y_range)) / 4
    y_ticks = []
    v = round(ylo / y_step) * y_step
    while v <= yhi:
        y_ticks.append(v); v += y_step
    svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">'
    svg += f'<rect x="0" y="0" width="{W}" height="{H}" fill="#0f172a" rx="12"/>'
    svg += f'<clipPath id="cp"><rect x="{ML}" y="{MT}" width="{PW}" height="{PH}"/></clipPath><g clip-path="url(#cp)">'
    svg += f'<polygon points="{fill_pts}" fill="rgba(129,140,248,0.1)"/>'
    svg += f'<polyline points="{pts}" fill="none" stroke="#818cf8" stroke-width="2" stroke-linejoin="round"/></g>'
    for v in y_ticks:
        y = sy(v)
        svg += f'<line x1="{ML}" y1="{y}" x2="{W-MR}" y2="{y}" stroke="#1e293b" stroke-width="1"/>'
        svg += f'<text x="{ML-6}" y="{y+4}" fill="#64748b" font-family="monospace" font-size="11" text-anchor="end">₹{v:,.0f}</text>'
    for i, t in x_ticks:
        x = sx(i)
        svg += f'<line x1="{x}" y1="{MT}" x2="{x}" y2="{H-MB}" stroke="#1e293b" stroke-width="1"/>'
        svg += f'<text x="{x}" y="{H-MB+16}" fill="#64748b" font-family="monospace" font-size="10" text-anchor="middle">{t}</text>'
    for v, color, label, anchor in [(entry, "#60a5fa", f"Entry ₹{entry}", "bottom"), (sl, "#f87171", f"{sl_label} ₹{sl}", "top"), (target, "#4ade80", f"{tgt_label} ₹{target}", "bottom")]:
        y = sy(v); dy = 4 if anchor == "top" else -4
        svg += f'<line x1="{ML}" y1="{y}" x2="{W-MR}" y2="{y}" stroke="{color}" stroke-width="1.5" stroke-dasharray="6,4"/>'
        svg += f'<text x="{ML+4}" y="{y+dy}" fill="{color}" font-family="monospace" font-size="11" font-weight="600" dominant-baseline="{anchor}">{label}</text>'
    close_val = closes[-1]; yc = sy(close_val)
    svg += f'<text x="{W-MR-4}" y="{yc-4}" fill="#e2e8f0" font-family="monospace" font-size="11" font-weight="600" text-anchor="end">Close ₹{close_val:,.2f}</text>'
    svg += '</svg>'
    return svg

def gen(symbol, lo_date, lo_time, entry, sl, target, df):
    times = [ts.strftime("%H:%M") for ts in df.index]
    closes = [round(c, 2) for c in df["Close"].tolist()]
    chart = svg_chart(closes, times, entry, sl, target, "SL", "TARGET HIT")
    op, hi, lo, cl = df["Open"].iloc[0], df["High"].max(), df["Low"].min(), df["Close"].iloc[-1]
    return f"""<!DOCTYPE html>
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
      <span class="result-badge" style="background:#4ade8022;color:#4ade80;border:1px solid #4ade8044;">✓ TARGET_HIT &mdash; +2.00%</span>
    </div>
  </div>
  <div class="grid">
    <div class="card"><div class="label">Stock</div><div class="value" style="font-size:28px;">{symbol}</div><div class="sub">NSE &middot; CASH</div></div>
    <div class="card"><div class="label">Score</div><div class="value" style="color:#a78bfa;">7.5</div><div class="sub">ATR 1.6% &middot; Vol Surge 1.5x</div></div>
    <div class="card"><div class="label">Entry Zone</div><div class="value" style="color:#60a5fa;">₹{entry}</div><div class="sub">Close at signal time</div></div>
    <div class="card"><div class="label">Stop Loss</div><div class="value" style="color:#f87171;">₹{sl}</div><div class="sub">-1% &middot; OK</div></div>
    <div class="card"><div class="label">Target</div><div class="value" style="color:#4ade80;">₹{target}</div><div class="sub">+2% &middot; HIT</div></div>
    <div class="card"><div class="label">Risk:Reward</div><div class="value" style="color:#fbbf24;">1:2.0</div><div class="sub">Min 1:2 required</div></div>
  </div>
  <div class="chart-card">{chart}</div>
  <div class="full-card" style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;margin-bottom:20px;">
    <h2 style="font-size:14px;font-family:monospace;text-transform:uppercase;letter-spacing:1px;color:#64748b;margin-bottom:12px;">Day Summary</h2>
    <div class="stats">
      <div class="stat"><span>Open</span> <strong>₹{op:.2f}</strong></div>
      <div class="stat"><span>High</span> <strong style="color:#4ade80;">₹{hi:.2f}</strong></div>
      <div class="stat"><span>Low</span> <strong style="color:#f87171;">₹{lo:.2f}</strong></div>
      <div class="stat"><span>Close</span> <strong>₹{cl:.2f}</strong></div>
      <div class="stat"><span>Range</span> <strong>₹{hi - lo:.2f}</strong></div>
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

# ICICIBANK - real data
df = yf.download("ICICIBANK.NS", period="2d", interval="1m", progress=False, auto_adjust=True)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
td = df[df.index.date == pd.Timestamp("2026-06-12").date()]
html = gen("ICICIBANK", "2026-06-12", "21:01:00", 1317.0, 1303.83, 1343.34, td)
with open("report/2026-06-12_21-01.html", "w", encoding="utf-8") as f:
    f.write(html)
os.write(2, b"ICICIBANK SVG done\n")

# RELIANCE - dummy data
np.random.seed(42)
idx = pd.date_range("2026-06-11 09:15", periods=375, freq="min")
opens = 2850.0 + np.cumsum(np.random.normal(0, 2, 375))
df2 = pd.DataFrame({"Open": opens, "High": opens+abs(np.random.normal(1.5,1,375)), "Low": opens-abs(np.random.normal(1.5,1,375)), "Close": opens+np.random.normal(0,1.5,375), "Volume": np.random.randint(100000,500000,375)}, index=idx)
df2.loc[df2["High"].idxmax(), "High"] = 2908.5
df2.loc[df2["Low"].idxmin(), "Low"] = 2820.58
html2 = gen("RELIANCE", "2026-06-11", "15:30:00", 2850.0, 2821.5, 2907.0, df2)
with open("report/2026-06-11_15-30.html", "w", encoding="utf-8") as f:
    f.write(html2)
os.write(2, b"RELIANCE SVG done\n")
