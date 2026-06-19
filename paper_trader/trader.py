#!/usr/bin/env python3
"""Paper trader — RSI regime-aware gap trading. 
   Morning mode (3:45 UTC): generates picks.
   Evening mode (10:00 UTC): generates verdict with SVG chart."""
import json, os, sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import numpy as np

IST = timezone(timedelta(hours=5, minutes=30))

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
        if gap > 0:
            return "SHORT", "wed gap-up fade"
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
    avg_pnl = pnl / total if total > 0 else 0
    return {
        "total": total, "wins": wins, "losses": losses,
        "winrate": round(wins / total * 100, 1) if total > 0 else 0,
        "pnl": round(pnl, 2), "avg_pnl": round(avg_pnl, 3)
    }

def generate_trade_svg(t, trade_idx):
    w, h = 1000, 220
    is_long = t.get("trade") == "LONG"
    entry = t.get("entry", 0)
    target = t.get("target", 0)
    sl = t.get("sl", 0)
    close = t.get("close", 0)
    hp = t.get("high", entry)
    lp = t.get("low", entry)
    op = t.get("open", entry)
    pc = t.get("prev_close", entry)
    pnl = t.get("pnl", 0)
    result = t.get("result", "")
    stock = t.get("stock", "")
    date = t.get("date", "")
    day_ended = result in ("FILLED", "STOPPED")

    vals = [v for v in [hp, lp, entry, target, sl, close, op, pc] if v and v > 0]
    if not vals:
        return f'<svg width="{w}" height="100" xmlns="http://www.w3.org/2000/svg"><rect width="{w}" height="100" fill="#0f1117" rx="6"/><text x="{w//2}" y="55" text-anchor="middle" fill="#8b949e" font-size="13">No price data</text></svg>'

    vmin = min(vals)
    vmax = max(vals)
    vrange = vmax - vmin if vmax != vmin else 1
    pad_val = vrange * 0.15
    vmin -= pad_val
    vmax += pad_val
    vrange = vmax - vmin

    margin_l, margin_r, margin_t, margin_b = 72, 16, 40, 28
    chart_l = margin_l
    chart_r = w - margin_r
    chart_w = chart_r - chart_l
    chart_t = margin_t
    chart_b = h - margin_b
    chart_h = chart_b - chart_t

    def scale_y(val):
        return chart_b - ((val - vmin) / vrange) * chart_h

    def scale_x(pct):
        return chart_l + pct * chart_w

    if is_long:
        accent = "#3fb950"
        accent_rgb = "63,185,80"
        body_color = "#3fb950"
        bear_color = "#f85149"
    else:
        accent = "#f85149"
        accent_rgb = "248,81,73"
        body_color = "#f85149"
        bear_color = "#3fb950"

    def price_label(val):
        return f"{val:.2f}"

    lines = []
    lines.append(f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">')
    lines.append(f'<defs><clipPath id="cp{trade_idx}"><rect x="0" y="0" width="{w}" height="{h}"/></clipPath></defs>')
    lines.append(f'<rect width="{w}" height="{h}" fill="#0f1117" rx="8" clip-path="url(#cp{trade_idx})"/>')

    lines.append(f'<rect x="0" y="0" width="{w}" height="32" fill="#15171d" rx="8"/>')
    lines.append(f'<rect x="0" y="20" width="{w}" height="12" fill="#15171d"/>')

    pnl_color = "#3fb950" if pnl >= 0 else "#f85149"
    result_color = {"FILLED": "#3fb950", "STOPPED": "#f85149", "OPEN": "#d29922"}.get(result, "#8b949e")
    lines.append(f'<text x="14" y="21" fill="#e1e4e8" font-family="sans-serif" font-size="14" font-weight="700">{stock}</text>')
    lines.append(f'<text x="14" y="21" fill="#8b949e" font-family="sans-serif" font-size="10"> | {date}</text>')

    info_x = 180
    lines.append(f'<text x="{info_x}" y="14" fill="#8b949e" font-family="sans-serif" font-size="11">{t.get("trade","")} · {t.get("rsi_regime","")}</text>')
    lines.append(f'<text x="{info_x}" y="27" fill="{result_color}" font-family="sans-serif" font-size="11" font-weight="700">{result}</text>')

    gap_val = t.get("gap", 0)
    gap_color = "#3fb950" if gap_val < 0 else "#f85149"
    gap_sym = "▲" if is_long else "▼"
    lines.append(f'<text x="340" y="14" fill="{gap_color}" font-family="sans-serif" font-size="11">Gap {gap_val:+.2f}% {gap_sym}</text>')
    lines.append(f'<text x="340" y="27" fill="#8b949e" font-family="sans-serif" font-size="10">Vol: {t.get("vol_ratio",0):.1f}x</text>')

    lines.append(f'<text x="{w-14}" y="21" fill="{pnl_color}" font-family="sans-serif" font-size="18" font-weight="700" text-anchor="end">{"+" if pnl >= 0 else ""}{pnl:.2f}%</text>')

    if not day_ended:
        lines.append(f'<rect x="{(w-320)//2}" y="{chart_t + (chart_h-50)//2}" width="320" height="50" fill="#1a1d24" rx="6"/>')
        lines.append(f'<text x="{w//2}" y="{chart_t + (chart_h-50)//2 + 22}" text-anchor="middle" fill="#d29922" font-family="sans-serif" font-size="14">⏳ Day in progress</text>')
        lines.append(f'<text x="{w//2}" y="{chart_t + (chart_h-50)//2 + 40}" text-anchor="middle" fill="#8b949e" font-family="sans-serif" font-size="11">Check evening verdict at 3:30 PM for results</text>')
        lines.append('</svg>')
        return "\n".join(lines)

    y_ticks = 6
    for i in range(y_ticks + 1):
        val = vmin + (vrange * i / y_ticks)
        yv = scale_y(val)
        if i == 0 or i == y_ticks:
            lines.append(f'<line x1="{chart_l}" y1="{yv:.1f}" x2="{chart_r}" y2="{yv:.1f}" stroke="#21262d" stroke-width="1"/>')
        else:
            lines.append(f'<line x1="{chart_l}" y1="{yv:.1f}" x2="{chart_r}" y2="{yv:.1f}" stroke="#161b22" stroke-width="1"/>')
        lines.append(f'<text x="{chart_l-6}" y="{yv+4:.1f}" fill="#484f58" font-family="sans-serif" font-size="10" text-anchor="end">{price_label(val)}</text>')

    lines.append(f'<text x="{chart_l}" y="{h-4}" fill="#484f58" font-family="sans-serif" font-size="9">Price</text>')

    rng = hp - lp
    num_curve_points = 40
    curve_x = []
    curve_y = []
    for i in range(num_curve_points + 1):
        x = i / num_curve_points
        xv = scale_x(x)
        trend = op + (close - op) * x
        osc = np.sin(x * np.pi + 0.35 * np.pi) * rng * 0.28
        val = trend + osc
        val = max(lp - rng * 0.05, min(hp + rng * 0.05, val))
        yv = scale_y(val)
        curve_x.append(xv)
        curve_y.append(yv)

    path_d = f"M {curve_x[0]:.1f},{curve_y[0]:.1f}"
    for i in range(1, len(curve_x)):
        path_d += f" L {curve_x[i]:.1f},{curve_y[i]:.1f}"

    lines.append(f'<path d="{path_d} L {curve_x[-1]:.1f},{chart_b} L {curve_x[0]:.1f},{chart_b} Z" fill="rgba({accent_rgb},0.08)"/>')
    lines.append(f'<path d="{path_d}" fill="none" stroke="{accent}" stroke-width="2" stroke-linejoin="round" opacity="0.7"/>')

    line_y = scale_y(op)
    lines.append(f'<circle cx="{scale_x(0):.1f}" cy="{line_y:.1f}" r="4" fill="{accent}" stroke="#0f1117" stroke-width="1.5"/>')
    line_y_c = scale_y(close)
    lines.append(f'<circle cx="{scale_x(1):.1f}" cy="{line_y_c:.1f}" r="4" fill="{accent}" stroke="#0f1117" stroke-width="1.5"/>')

    candle_x = scale_x(0.5)
    lines.append(f'<line x1="{candle_x:.1f}" y1="{scale_y(hp):.1f}" x2="{candle_x:.1f}" y2="{scale_y(lp):.1f}" stroke="#484f58" stroke-width="2" stroke-linecap="round"/>')

    body_top = scale_y(max(op, close))
    body_bot = scale_y(min(op, close))
    body_h = body_top - body_bot
    if body_h < 2:
        body_h = 2
    up = close >= op
    candle_color = "#3fb950" if up else "#f85149"
    lines.append(f'<rect x="{candle_x-5:.1f}" y="{body_bot:.1f}" width="10" height="{body_h:.1f}" fill="{candle_color}" rx="1.5"/>')

    def draw_line(label, val, color, dash, y_offset_text=0):
        yv = scale_y(val)
        dash_attr = ' stroke-dasharray="6,4"' if dash == "dashed" else ' stroke-dasharray="3,3"' if dash == "dotted" else ""
        lines.append(f'<line x1="{chart_l}" y1="{yv:.1f}" x2="{chart_r}" y2="{yv:.1f}" stroke="{color}" stroke-width="1.5"{dash_attr} opacity="0.7"/>')
        lines.append(f'<rect x="{scale_x(0.78):.1f}" y="{yv-9:.1f}" width="{chart_r-scale_x(0.78):.1f}" height="18" fill="rgba(15,17,23,0.7)" rx="3"/>')
        lines.append(f'<text x="{scale_x(0.78)+4:.1f}" y="{yv+4+y_offset_text:.1f}" fill="{color}" font-family="sans-serif" font-size="11" font-weight="600">{label} {price_label(val)}</text>')

    target_color = "#3fb950" if is_long else "#f85149"
    sl_color = "#f85149" if is_long else "#3fb950"

    draw_line("TGT", target, target_color, "dashed")
    draw_line("ENT", entry, "#58a6ff", "solid")
    draw_line("SL", sl, sl_color, "dotted")

    if pc:
        pc_y = scale_y(pc)
        lines.append(f'<line x1="{chart_l}" y1="{pc_y:.1f}" x2="{chart_r}" y2="{pc_y:.1f}" stroke="#8b949e" stroke-width="1" stroke-dasharray="2,4" opacity="0.5"/>')
        lines.append(f'<text x="{chart_r-4}" y="{pc_y-3:.1f}" fill="#8b949e" font-family="sans-serif" font-size="10" text-anchor="end">Prev Close</text>')

    gap_text = f"Gap {gap_val:+.2f}% · Entry {price_label(entry)} → {'Target' if is_long else 'Target'} {price_label(target)} · SL {price_label(sl)}"
    lines.append(f'<text x="{chart_l}" y="{h-4}" fill="#484f58" font-family="sans-serif" font-size="9">{gap_text}</text>')

    lines.append('</svg>')
    return "\n".join(lines)


def generate_svg_chart(trades):
    width, height = 800, 380
    pad = {"t": 50, "b": 55, "l": 70, "r": 30}
    cw = width - pad["l"] - pad["r"]
    ch = height - pad["t"] - pad["b"]

    cum_pnl = []
    running = 0.0
    for t in trades:
        running += t.get("pnl", 0)
        cum_pnl.append(round(running, 2))

    if not cum_pnl:
        return (f'<svg width="{width}" height="200" xmlns="http://www.w3.org/2000/svg">'
                f'<rect width="{width}" height="200" fill="#0f1117" rx="8"/>'
                f'<text x="400" y="105" text-anchor="middle" fill="#8b949e" font-family="sans-serif" font-size="14">No trades yet</text></svg>')

    max_pnl = max(cum_pnl)
    min_pnl = min(cum_pnl)
    pk = max_pnl - min_pnl if max_pnl != min_pnl else 1
    y_margin = pk * 0.12
    y_max = max_pnl + y_margin
    y_min = min_pnl - y_margin
    n = len(cum_pnl)

    def sx(i):
        return pad["l"] + (i / max(n - 1, 1)) * cw

    def sy(v):
        r = (v - y_min) / (y_max - y_min) if y_max != y_min else 0.5
        return pad["t"] + ch - r * ch

    lines = []
    lines.append(f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">')
    lines.append(f'<rect width="{width}" height="{height}" fill="#0f1117" rx="8"/>')
    lines.append(f'<text x="{pad["l"]}" y="28" fill="#e1e4e8" font-family="sans-serif" font-size="15" font-weight="700">PnL Curve — Cumulative Strategy Performance</text>')

    zero_y = sy(0)
    lines.append(f'<line x1="{pad["l"]}" y1="{zero_y:.1f}" x2="{width-pad["r"]}" y2="{zero_y:.1f}" stroke="#30363d" stroke-width="1" stroke-dasharray="3,3"/>')

    num_grid = 5
    for i in range(num_grid + 1):
        v = y_min + (y_max - y_min) * i / num_grid
        y = sy(v)
        lines.append(f'<line x1="{pad["l"]}" y1="{y:.1f}" x2="{width-pad["r"]}" y2="{y:.1f}" stroke="#21262d" stroke-width="1" stroke-dasharray="4,4"/>')
        lines.append(f'<text x="{pad["l"]-8}" y="{y+4}" fill="#8b949e" font-family="sans-serif" font-size="11" text-anchor="end">{v:+.2f}%</text>')

    for i in range(num_grid + 1):
        xi = i / num_grid * (n - 1)
        if 0 < xi < n - 1 or i == 0 or i == num_grid:
            x = sx(xi)
            lines.append(f'<text x="{x:.1f}" y="{height-pad["b"]+16}" fill="#8b949e" font-family="sans-serif" font-size="10" text-anchor="middle">{int(xi+1)}</text>')

    lines.append(f'<text x="{pad["l"]+cw/2}" y="{height-6}" fill="#8b949e" font-family="sans-serif" font-size="11" text-anchor="middle">Trade #</text>')

    pts = " ".join(f"{sx(i):.1f},{sy(p):.1f}" for i, p in enumerate(cum_pnl))
    lines.append(f'<polygon points="{pad["l"]},{sy(y_min):.1f} {pts} {sx(n-1):.1f},{sy(y_min):.1f}" fill="url(#ag)"/>')
    lines.append('<defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">'
                 '<stop offset="0%" stop-color="#3fb950" stop-opacity="0.25"/>'
                 '<stop offset="100%" stop-color="#3fb950" stop-opacity="0.01"/>'
                 '</linearGradient></defs>')
    lines.append(f'<polyline points="{pts}" fill="none" stroke="#3fb950" stroke-width="2.5" stroke-linejoin="round"/>')

    for i, t in enumerate(trades):
        x, y = sx(i), sy(cum_pnl[i])
        pnl_v = t.get("pnl", 0)
        c = "#3fb950" if pnl_v >= 0 else "#f85149"
        r = 5.5 if pnl_v >= 0 else 5.5
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}" stroke="#0f1117" stroke-width="2.5"/>')

    if n >= 2:
        best_idx = cum_pnl.index(max(cum_pnl))
        bx, by = sx(best_idx), sy(cum_pnl[best_idx])
        lines.append(f'<text x="{bx+12:.1f}" y="{by-6:.1f}" fill="#3fb950" font-family="sans-serif" font-size="11">{cum_pnl[best_idx]:+.2f}%</text>')
        worst_idx = cum_pnl.index(min(cum_pnl))
        wx, wy = sx(worst_idx), sy(cum_pnl[worst_idx])
        lines.append(f'<text x="{wx+12:.1f}" y="{wy+15:.1f}" fill="#f85149" font-family="sans-serif" font-size="11">{cum_pnl[worst_idx]:+.2f}%</text>')

    # Final dot
    lx, ly = sx(n-1), sy(cum_pnl[-1])
    lines.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="7" fill="none" stroke="#d29922" stroke-width="2"/>')
    lines.append(f'<text x="{lx+12:.1f}" y="{ly+4:.1f}" fill="#d29922" font-family="sans-serif" font-size="11" font-weight="700">Now: {cum_pnl[-1]:+.2f}%</text>')

    lines.append('</svg>')
    return "\n".join(lines)

def generate_html(ledger, day_picks, today, day_name, mode, regime_summary=None):
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

    svg_chart = generate_svg_chart(all_trades)

    picks_rows = ""
    verdict = ""
    if day_picks:
        wins = sum(1 for p in day_picks if p.get("pnl", 0) > 0)
        losses = sum(1 for p in day_picks if p.get("pnl", 0) < 0)
        day_pnl = sum(p.get("pnl", 0) for p in day_picks)
        verdict_cls = "green" if day_pnl >= 0 else "red"
        if mode == "morning":
            verdict = f'<div class="verdict neutral">Morning Picks — {len(day_picks)} signals generated · Check evening verdict for results</div>'
        else:
            verdict = f'<div class="verdict {verdict_cls}">Verdict: {wins}-{losses} ({wins+losses} trades) · Day PnL: {day_pnl:+.2f}%</div>'

    for i, p in enumerate(day_picks):
        cls = "win" if p.get("pnl", 0) > 0 else ("loss" if p.get("pnl", 0) < 0 else "")
        dir_cls = "long" if p.get("trade") == "LONG" else "short"
        pnl_str = f"{p['pnl']:+.2f}%" if p.get('pnl') != 0 or p.get('result') != 'SKIP' else "-"
        picks_rows += f"<tr class='trade-row {cls}' data-trade-index='{i}'><td>{p['stock']}</td><td>{p.get('rsi',0):.0f}</td><td class='{'red' if p['gap']>0 else 'green'}'>{p['gap']:+.2f}%</td><td>{p['vol_ratio']:.1f}x</td><td><span class='badge {dir_cls}'>{p['trade']}</span></td><td>{p.get('rsi_regime','')}</td><td>{p['entry']}</td><td>{p['target']}</td><td>{p['sl']}</td><td>{p['close']}</td><td>{p['result']}</td><td>{p['pnl']:+.2f}%</td></tr>"
        trade_svg = generate_trade_svg(p, i)
        picks_rows += f"<tr class='trade-detail' data-trade-index='{i}'><td colspan='12' style='padding:10px 15px;background:#0f1117;border-bottom:1px solid #30363d;'>{trade_svg}</td></tr>"

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

    mode_label = "☀️ Morning Picks" if mode == "morning" else "🏆 Evening Verdict"
    mode_badge = f'<span class="mode-badge {mode}">{mode_label}</span>'
    now_ist = datetime.now(IST).strftime('%I:%M %p')
    now_utc = datetime.now(timezone.utc).strftime('%H:%M UTC')

    strategy_rules = (
        "RSI<30 → short gap-ups only. RSI>70 → long gap-downs only. "
        "RSI 30-70 → day-wise: Mon short up, Tue both, Wed long dn, Thu short up, Fri depends."
    )

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Trader — {mode_label}</title>
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
.chart-box {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:15px; margin:15px 0; overflow-x:auto; }}
.chart-box svg {{ display:block; margin:0 auto; max-width:100%; height:auto; }}
.rule {{ background:#1a1d24; padding:10px 15px; border-radius:6px; font-size:13px; color:#8b949e; margin:10px 0; line-height:1.6; }}
.low-rsi {{ color:#f85149; font-weight:600; }}
.high-rsi {{ color:#3fb950; font-weight:600; }}
.verdict {{ font-size:16px; font-weight:700; padding:10px 15px; border-radius:6px; margin:10px 0; }}
.verdict.green {{ background:#0d2810; color:#3fb950; border:1px solid #3fb950; }}
.verdict.red {{ background:#280d0d; color:#f85149; border:1px solid #f85149; }}
.verdict.neutral {{ background:#1a1d24; color:#d29922; border:1px solid #30363d; }}
.mode-badge {{ display:inline-block; padding:4px 14px; border-radius:20px; font-size:14px; font-weight:600; margin-left:10px; }}
.mode-badge.morning {{ background:#1a2d1a; color:#7ee787; border:1px solid #3fb950; }}
.mode-badge.evening {{ background:#2d1a1a; color:#ff7b72; border:1px solid #f85149; }}
.link-bar {{ margin:10px 0; font-size:13px; }}
.link-bar a {{ color:#58a6ff; text-decoration:none; }}
.link-bar a:hover {{ text-decoration:underline; }}
.trade-count {{ font-size:14px; color:#8b949e; margin:5px 0; }}
.trade-row {{ cursor: pointer; transition: background 0.15s; }}
.trade-row:hover {{ background:#1c2128 !important; }}
.trade-detail {{ display: none; }}
.trade-detail.open {{ display: table-row; }}
.trade-detail td {{ padding: 0 !important; }}
</style></head>
<body>
<h1>Paper Trader — RSI Regime Strategy {mode_badge}</h1>
<p class="sub">{today} · {day_name} · {now_ist} IST · Generated {now_utc}</p>

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

<div class="chart-box">
{svg_chart}
</div>

<div class="chart-box"><canvas id="cumChart" height="80"></canvas></div>
<div class="chart-box"><canvas id="dayChart" height="80"></canvas></div>

<h2>{'Today\'s Picks' if mode=='morning' else 'Today\'s Trades'} ({len(day_picks)} trades)</h2>
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

document.querySelectorAll('.trade-row').forEach(row => {{
    row.addEventListener('click', () => {{
        const idx = row.dataset.tradeIndex;
        const detail = document.querySelector(`.trade-detail[data-trade-index="${{idx}}"]`);
        if (detail) {{
            detail.classList.toggle('open');
        }}
    }});
}});
</script>
<p style="color:#484f58;font-size:12px;margin-top:20px">Auto-generated · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
</body></html>'''

    return html

def run_paper_trade(override_date=None):
    import yfinance as yf

    today = datetime.strptime(override_date, '%Y-%m-%d') if override_date else datetime.now()
    utc_hour = datetime.now(timezone.utc).hour
    mode = "evening" if override_date else ("morning" if utc_hour < 7 else "evening")

    dow = today.weekday()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = day_names[dow]

    if dow >= 5:
        print(f"Weekend ({day_name}) — no trading")
        return

    print(f"Running {mode} paper trade for {day_name} ({today.strftime('%Y-%m-%d')})")

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

    idx = available_dates.index(trade_date)
    prev_date = available_dates[idx - 1] if idx > 0 else available_dates[0]

    ledger_path = "paper_trader/ledger.json"
    if os.path.exists(ledger_path):
        ledger = json.load(open(ledger_path))
    else:
        ledger = {"trades": [], "runs": []}

    for t in ledger["trades"]:
        if "high" not in t or "low" not in t or "open" not in t or "prev_close" not in t:
            gap_pct = t.get("gap", 0)
            entry = t.get("entry", 0)
            close = t.get("close", 0)
            target = t.get("target", 0)
            sl = t.get("sl", 0)
            t["open"] = t.get("open", entry)
            t["prev_close"] = t.get("prev_close", round(entry / (1 + gap_pct / 100), 2)) if gap_pct else t.get("prev_close", entry)
            vals = [v for v in [entry, close, target, sl] if v and v > 0]
            t["high"] = t.get("high", max(vals) if vals else entry)
            t["low"] = t.get("low", min(vals) if vals else entry)
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)

    actual_day_name = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][trade_dow]

    existing_dates = {t.get("date") for t in ledger["trades"]}

    if mode == "evening" and trade_date not in existing_dates:
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
                    "high": round(hp, 2), "low": round(lp, 2),
                    "prev_close": round(pc, 2), "open": round(op, 2),
                    "result": result, "pnl": pnl, "direction": direction,
                    "date": trade_date, "day": actual_day_name,
                    "market_tide": f"{pct_up:.0f}% up"
                })

        for p in day_picks:
            ledger["trades"].append(p)
        ledger["runs"].append({"date": trade_date, "day": day_name, "trades": len(day_picks), "mode": mode})

        with open(ledger_path, "w") as f:
            json.dump(ledger, f, indent=2)

        print(f"Recorded {len(day_picks)} trades for {trade_date}")
    else:
        # Morning or already-processed: re-generate HTML with existing data
        if mode == "morning":
            print(f"Morning mode — generating picks from latest available data")
        else:
            print(f"Already processed {trade_date} — regenerating HTML")

    todays_picks = [t for t in ledger["trades"] if t.get("date") == trade_date]

    regime_summary = {"LOW": 0, "MID": 0, "HIGH": 0}
    for p in todays_picks:
        r = p.get("rsi_regime", "")
        if r in regime_summary:
            regime_summary[r] += 1

    html = generate_html(ledger, todays_picks, trade_date, actual_day_name, mode, regime_summary)
    html_path = "paper_trader/index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard: {html_path}")
    print(f"Mode: {mode}")

    all_trades = ledger["trades"]
    wins = sum(1 for t in all_trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in all_trades if t.get("pnl", 0) < 0)
    total_pnl = sum(t.get("pnl", 0) for t in all_trades)
    print(f"\n{'='*50}")
    print(f"  PAPER TRADING SUMMARY ({mode.upper()})")
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
    import sys
    override = sys.argv[1] if len(sys.argv) > 1 else None
    run_paper_trade(override_date=override)
