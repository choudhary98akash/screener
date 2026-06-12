#!/usr/bin/env python3
"""
Nifty 50 Intraday Screener — Backtester
========================================
Fetches real NSE data via yfinance (free), applies the screener
strategy from screener.md, and outputs performance stats.

Usage:
    python backtest.py                        # Backtest last 30 days
    python backtest.py --days 60              # Custom period
    python backtest.py --start 2026-05-01 --end 2026-06-01  # Date range
"""

import argparse, sys, json, warnings, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

# ─── Nifty 50 Constituents (yahoo finance symbols with .NS suffix) ───
NIFTY_50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "HINDUNILVR.NS", "ITC.NS", "INFY.NS", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "SBIN.NS", "WIPRO.NS", "LT.NS", "HCLTECH.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ASIANPAINT.NS", "AXISBANK.NS", "ULTRACEMCO.NS",
    "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "M&M.NS", "TRENT.NS",
    "COALINDIA.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BEL.NS", "BAJAJFINSV.NS",
    "NESTLEIND.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "JSWSTEEL.NS",
    "HINDALCO.NS", "BPCL.NS", "GRASIM.NS", "EICHERMOT.NS", "BRITANNIA.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "SBILIFE.NS", "APOLLOHOSP.NS",
    "HDFCLIFE.NS", "SHRIRAMFIN.NS", "BAJAJHLDNG.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS",
]

def clean_symbol(symbol: str) -> str:
    """Strip .NS suffix for display."""
    return symbol.replace(".NS", "")


# ─── Technical Indicators ───

def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ─── Screener Logic ───

def screen_stock(df: pd.DataFrame, idx: int) -> dict | None:
    """
    Check if stock passes screener criteria on given day index.
    Returns dict with entry details or None if skip.
    """
    today = df.iloc[idx]
    lookback = df.iloc[max(0, idx - 20):idx + 1]

    if len(lookback) < 15:
        return None

    close = lookback["Close"]
    volume = lookback["Volume"]
    ema9 = calc_ema(close, 9)
    ema21 = calc_ema(close, 21)
    atr = calc_atr(lookback, 14)

    # ── Filters ──
    price = today["Close"]
    if price < 500:
        return None

    vol_today = today["Volume"]
    avg_vol = volume.tail(10).mean() if len(volume) >= 10 else volume.mean()
    if vol_today < 1_000_000:
        return None
    if avg_vol == 0:
        return None
    vol_surge_pct = (vol_today / avg_vol) * 100
    if vol_surge_pct < 120:
        return None

    atr_val = atr.iloc[-1]
    if np.isnan(atr_val) or (atr_val / price) < 0.015:
        return None

    # ── Momentum: above both EMAs ──
    if pd.isna(ema9.iloc[-1]) or pd.isna(ema21.iloc[-1]):
        return None
    if price < ema9.iloc[-1] or price < ema21.iloc[-1]:
        return None

    # ── Entry simulation ──
    entry = price
    stop_loss = entry * 0.99
    target = entry * 1.02
    risk_pct = -1.0
    reward_pct = 2.0
    rr = round(reward_pct / abs(risk_pct), 2)

    if rr < 2.0:
        return None

    return {
        "symbol": clean_symbol(df.name) if hasattr(df, "name") else "?",
        "date": today.name.strftime("%Y-%m-%d") if hasattr(today.name, "strftime") else str(today.name),
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "target": round(target, 2),
        "risk_pct": risk_pct,
        "reward_pct": reward_pct,
        "rr": rr,
        "atr_pct": round((atr_val / price) * 100, 2),
        "volume_surge_pct": round(vol_surge_pct, 1),
        "price": round(price, 2),
        "close_ema9": round(ema9.iloc[-1], 2),
        "close_ema21": round(ema21.iloc[-1], 2),
        "above_emas": True,
    }


def simulate_trade(df: pd.DataFrame, idx: int, entry_data: dict) -> dict:
    """
    Simulate the trade: next 5 days max, exit at SL or target.
    Returns result dict.
    """
    entry = entry_data["entry"]
    sl = entry_data["stop_loss"]
    tgt = entry_data["target"]

    future = df.iloc[idx + 1: idx + 6]
    if len(future) == 0:
        return {**entry_data, "result": "NO_DATA", "pnl_pct": 0, "exit_date": None}

    exit_price = None
    exit_reason = "HOLD"
    for _, row in future.iterrows():
        if row["Low"] <= sl:
            exit_price = sl
            exit_reason = "SL_HIT"
            break
        if row["High"] >= tgt:
            exit_price = tgt
            exit_reason = "TARGET_HIT"
            break

    if exit_price is None:
        exit_price = future.iloc[-1]["Close"]
        exit_reason = "TIME_EXIT"

    pnl_pct = round(((exit_price - entry) / entry) * 100, 2)

    return {
        **entry_data,
        "result": exit_reason,
        "exit_price": round(exit_price, 2),
        "exit_date": future.iloc[-1].name.strftime("%Y-%m-%d") if hasattr(future.iloc[-1].name, "strftime") else str(future.iloc[-1].name),
        "pnl_pct": pnl_pct,
    }


# ─── Main Backtest ───

def run_backtest(start_date: str, end_date: str):
    print(f"\n{'='*60}")
    print(f"  NIFTY 50 INTRADAY SCREENER - BACKTEST")
    print(f"  Period: {start_date}  ->  {end_date}")
    print(f"{'='*60}\n")

    all_trades = []
    total_checks = 0
    total_passed = 0
    errors = []

    for i, symbol in enumerate(NIFTY_50):
        name = clean_symbol(symbol)
        print(f"  [{i+1:2d}/50] {name:16s} ... ", end="", flush=True)

        try:
            df = yf.download(
                symbol, start=start_date, end=end_date,
                progress=False, auto_adjust=True
            )
        except Exception as e:
            print(f"❌ FETCH ERROR: {e}")
            errors.append((name, str(e)))
            continue

        if df.empty or len(df) < 20:
            print("⚠ SKIP (insufficient data)")
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.name = symbol

        # Check each day
        trades_found = 0
        for idx in range(20, len(df) - 2):
            total_checks += 1
            entry_data = screen_stock(df, idx)
            if entry_data is None:
                continue

            total_passed += 1
            result = simulate_trade(df, idx, entry_data)
            all_trades.append(result)
            trades_found += 1

        print(f"{trades_found} trades")
        if trades_found > 0:
            for t in all_trades[-trades_found:]:
                icon = "✅" if t["pnl_pct"] > 0 else "❌"
                print(f"         {icon} {t['date']} entry={t['entry']} "
                      f"→ {t['result']} PnL={t['pnl_pct']:+.2f}%")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Total checks       : {total_checks}")
    print(f"  Signals generated  : {total_passed}")
    print(f"  Stocks with errors : {len(errors)}")

    if not all_trades:
        print("\n  ⚠ No trades generated. Try a longer/more volatile period.")
        return

    df_trades = pd.DataFrame(all_trades)
    wins = df_trades[df_trades["pnl_pct"] > 0]
    losses = df_trades[df_trades["pnl_pct"] <= 0]

    win_rate = round(len(wins) / len(df_trades) * 100, 1)
    avg_win = round(wins["pnl_pct"].mean(), 2) if len(wins) else 0
    avg_loss = round(losses["pnl_pct"].mean(), 2) if len(losses) else 0
    expectancy = round(df_trades["pnl_pct"].mean(), 2)
    total_pnl = round(df_trades["pnl_pct"].sum(), 2)
    max_drawdown = round(df_trades["pnl_pct"].min(), 2)
    best_trade = round(df_trades["pnl_pct"].max(), 2)

    print(f"\n  ┌─────────────────────┬──────────┐")
    print(f"  │ Metric              │ Value    │")
    print(f"  ├─────────────────────┼──────────┤")
    print(f"  │ Total Trades        │ {len(df_trades):>8d} │")
    print(f"  │ Win Rate            │ {win_rate:>7.1f}%  │")
    print(f"  │ Avg Win             │ {avg_win:>+.2f}%  │")
    print(f"  │ Avg Loss            │ {avg_loss:>+.2f}%  │")
    print(f"  │ Expectancy (avg)    │ {expectancy:>+.2f}%  │")
    print(f"  │ Total PnL (sum)     │ {total_pnl:>+.2f}%  │")
    print(f"  │ Best Trade          │ {best_trade:>+.2f}%  │")
    print(f"  │ Max Drawdown        │ {max_drawdown:>+.2f}%  │")
    print(f"  │ Profit Factor       │ {calc_profit_factor(df_trades):>7.2f}  │")
    print(f"  └─────────────────────┴──────────┘")

    # Top stocks by trades
    top = df_trades["symbol"].value_counts().head(10)
    print(f"\n  Top stocks by signals:")
    for sym, cnt in top.items():
        sym_trades = df_trades[df_trades["symbol"] == sym]
        sym_win = len(sym_trades[sym_trades["pnl_pct"] > 0])
        print(f"    {sym:16s} {cnt:2d} trades  ({sym_win} wins)")

    # Exit reasons breakdown
    print(f"\n  Exit breakdown:")
    for reason, group in df_trades.groupby("result"):
        print(f"    {reason:15s} {len(group):3d} trades")

    # Save detailed results
    out_path = f"backtest_results_{start_date}_to_{end_date}.csv"
    df_trades.to_csv(out_path, index=False)
    print(f"\n  📄 Detailed results saved to: {out_path}")

    # Save JSON summary
    summary = {
        "period": {"start": start_date, "end": end_date},
        "total_checks": total_checks,
        "signals": total_passed,
        "trades": len(df_trades),
        "win_rate_pct": win_rate,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "expectancy_pct": expectancy,
        "total_pnl_pct": total_pnl,
        "best_trade_pct": best_trade,
        "max_drawdown_pct": max_drawdown,
        "profit_factor": calc_profit_factor(df_trades),
        "exit_breakdown": df_trades["result"].value_counts().to_dict(),
    }
    summary_path = f"backtest_summary_{start_date}_to_{end_date}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  📄 Summary saved to: {summary_path}\n")


def calc_profit_factor(df_trades: pd.DataFrame) -> float:
    gross_profit = df_trades[df_trades["pnl_pct"] > 0]["pnl_pct"].sum()
    gross_loss = abs(df_trades[df_trades["pnl_pct"] < 0]["pnl_pct"].sum())
    return round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nifty 50 Intraday Screener Backtest")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backtest (default: 30)")
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD")
    args = parser.parse_args()

    if args.start and args.end:
        start, end = args.start, args.end
    else:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    run_backtest(start, end)
