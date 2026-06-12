#!/usr/bin/env python3
"""
Intraday Screener — HTML Pick Generator
========================================
Generates rich interactive HTML output files at:
    analysis/YYYY-MM-DD/one.html, two.html, three.html ...

Usage:
    python generate_pick_html.py              # Generate all historical days
    python generate_pick_html.py --date 2026-06-12 --counter 3   # Specific day/counter
"""

import os, sys, json, argparse
from datetime import datetime

# ─────────────────────────────────────────────────────────
#  NUMBER → ENGLISH WORD MAPPING (for filenames: 1→one, 2→two, etc.)
# ─────────────────────────────────────────────────────────

_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

def _num_to_word(n):
    """Convert integer 1+ to English word (1→one, 2→two, etc.) for filenames."""
    if n < 20:
        return _ONES[n]
    elif n < 100:
        t, o = divmod(n, 10)
        return _TENS[t] + ("_" + _ONES[o] if o else "")
    return str(n)  # fallback for 100+

# Pre-build reverse lookup (word → number) for auto-detection
_WORD_TO_NUM = {}
for _n in range(1, 200):
    _WORD_TO_NUM[_num_to_word(_n)] = _n

# ─────────────────────────────────────────────────────────
#  DATA — All historical days
# ─────────────────────────────────────────────────────────

DAYS = [
  {
    "date": "2026-06-01", "label": "Jun 1", "day": "Monday",
    "nifty": 23382.60, "nifty_chg": -0.70, "bank_nifty": 53973,
    "vix": 16.54, "vix_chg": 2.21,
    "fii": -3911.68, "dii": 5109.13,
    "market_breadth": "Negative — FII heavy selling, Asian markets weak",
    "nifty_support": "23,200", "nifty_resistance": "23,600",
    "sector_performance": [("Banking", "❌ Weak — Bank Nifty −1.44%"), ("IT", "❌ Negative"), ("FMCG", "~ Neutral"), ("Auto", "❌ Weak")],
    "news_catalysts": ["Week start with risk-off tone", "FII selling −₹3,912 Cr continued from May", "Global growth concerns weighing on sentiment", "No major domestic triggers"],
    "stocks": {
      "ICICI": {"close": 1239.70, "chg": -1.33, "vol_lakhs": 99.12, "avg_vol_lakhs": 140, "ema20": 1260, "ema50": 1245,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "Price at ₹1,240, below 20EMA (₹1,260). Lower high formed. Weak trend.",
        "volume_d": "Volume 99L vs avg 140L (−29%). Below average participation.",
        "volatility_d": "ATR ~₹19 (1.5% of price). Adequate for intraday.",
        "sentiment_d": "FII sold −₹3,912 Cr. No positive catalyst. Risk-off.",
        "sr_d": "Broke support at ₹1,250. Next support ₹1,215 (−2% below). No clear resistance.",
        "rr_d": "Entry ₹1,240, SL ₹1,215 (−2%), T ₹1,260 (+1.6%). R:R < 1:1.",
        "sector_d": "Bank Nifty −1.44%. Sector underperforming.",
        "emotion_d": "VIX 16.54 elevated. FII selling. Fear present.",
        "status": "fail"
      },
      "Axis": {"close": 1275.90, "chg": -0.83, "vol_lakhs": 43.10, "avg_vol_lakhs": 70, "ema20": 1290, "ema50": 1275,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "Price at ₹1,276, below 20EMA (₹1,290). Downtrending.",
        "volume_d": "Volume 43L vs avg 70L (−39%). Significantly below average.",
        "volatility_d": "ATR adequate for intraday.",
        "sentiment_d": "No positive triggers. Market risk-off.",
        "sr_d": "Support at ₹1,250 (−2%). Resistance ₹1,300. Tight range.",
        "rr_d": "Entry ₹1,276, SL ₹1,250 (−2%), T ₹1,300 (+1.9%). R:R barely 1:1.",
        "sector_d": "Bank Nifty −1.44%. Entire sector weak.",
        "emotion_d": "VIX elevated. Institutional selling.",
        "status": "fail"
      },
      "HDFC": {"close": 735.00, "chg": -0.81, "vol_lakhs": 184.80, "avg_vol_lakhs": 300, "ema20": 745, "ema50": 750,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "Below both EMAs. Near 52W low (₹727). No momentum.",
        "volume_d": "Volume 185L vs avg 300L (−38%). Below average.",
        "volatility_d": "ATR ~₹12 (1.6%). Adequate.",
        "sentiment_d": "FII selling pressure on banking. No catalyst.",
        "sr_d": "Support ₹727 (52W low). Resistance ₹750.",
        "rr_d": "Tight range. R:R not favorable.",
        "sector_d": "Banking sector weak. HDFC lagging peers.",
        "emotion_d": "Fear mode. No institutional confidence.",
        "status": "fail"
      }
    },
    "final_pick": None,
    "final_pick_data": None,
    "alt_watchlist": [],
    "notable_movers": [],
    "risk_notes": ["VIX at 16.54 — elevated fear", "FII selling −₹3,912 Cr heavy", "No clear sector leadership", "Avoid fresh longs until market stabilizes"]
  },
  {
    "date": "2026-06-02", "label": "Jun 2", "day": "Tuesday",
    "nifty": 23483.55, "nifty_chg": 0.43, "bank_nifty": 54148,
    "vix": 15.36, "vix_chg": -7.18,
    "fii": -8362.92, "dii": 9589.32,
    "market_breadth": "Mixed — DIIs aggressively absorbing FII selling (+₹9,589Cr)",
    "nifty_support": "23,300", "nifty_resistance": "23,600",
    "sector_performance": [("Banking", "~ Mixed — HDFC +1.10% but Axis −1.94%"), ("FMCG", "✅ Positive"), ("Auto", "~ Neutral"), ("PSU Banks", "❌ Weak")],
    "news_catalysts": ["DII buying at record levels (+₹9,589 Cr) absorbing FII outflows", "FII selling intense at −₹8,363 Cr — 2nd highest of the period", "Nifty recovered from lows to close +0.43%", "HDFC Bank showing relative strength"],
    "stocks": {
      "ICICI": {"close": 1226.60, "chg": -1.06, "vol_lakhs": 179.21, "avg_vol_lakhs": 140, "ema20": 1255, "ema50": 1240,
        "momentum": "❌ FAIL", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "Price ₹1,227, below 20EMA. Making new week low.",
        "volume_d": "Volume 179L — 28% above avg. Selling pressure high.",
        "volatility_d": "ATR sufficient.",
        "sentiment_d": "FIIs dumping. No positive catalyst.",
        "sr_d": "Broke ₹1,240 support. Next support ₹1,215.",
        "rr_d": "No clear entry. Downtrend.",
        "sector_d": "Bank Nifty flat but ICICI underperforming.",
        "emotion_d": "VIX dropping but FII panic selling.",
        "status": "fail"
      },
      "Axis": {"close": 1251.10, "chg": -1.94, "vol_lakhs": 118.80, "avg_vol_lakhs": 70, "ema20": 1285, "ema50": 1270,
        "momentum": "❌ FAIL", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "−1.94% — worst of the three. Sharp decline.",
        "volume_d": "Volume 119L — 70% above avg. Distribution.",
        "volatility_d": "Adequate ATR.",
        "sentiment_d": "FII selling focused on banking.",
        "sr_d": "Crashed through ₹1,270 support. Weak.",
        "rr_d": "Downtrend. Avoid.",
        "sector_d": "Underperforming sector.",
        "emotion_d": "High fear.",
        "status": "fail"
      },
      "HDFC": {"close": 743.10, "chg": 1.10, "vol_lakhs": 305.80, "avg_vol_lakhs": 300, "ema20": 745, "ema50": 748,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "❌ FAIL",
        "momentum_d": "Only one of three with positive momentum (+1.10%). Higher low forming.",
        "volume_d": "Volume 306L (near avg). Strong participation in rally.",
        "volatility_d": "ATR ~₹12 (1.6%). Good intraday range.",
        "sentiment_d": "DII buying +₹9,589 Cr supportive. But FII overhang remains.",
        "sr_d": "Held ₹740 support. Clear bounce. Resistance ₹755.",
        "rr_d": "Entry ₹742, SL ₹730 (−1.6%), T ₹755 (+1.8%). R:R ~1:1.1.",
        "sector_d": "Outperforming sector. Banking mixed but HDFC leading.",
        "emotion_d": "VIX falling to 15.36. Fear easing.",
        "status": "winner"
      }
    },
    "final_pick": "HDFC",
    "final_pick_data": {"entry_zone": "₹740 – ₹744", "entry_mid": 742, "stop_loss": "₹730", "sl_val": 730, "target_1": "₹755", "t1_val": 755, "target_2": "₹770", "t2_val": 770, "risk_pct": -1.6, "reward_pct_1": 1.8, "reward_pct_2": 3.8, "time_horizon": "Intraday to 1 session", "why": "Only positive stock among the three (+1.10%). Volume surge (305.8L). Held ₹740 support. DIIs absorbing all FII selling. Banking showing early signs of bottoming."},
    "alt_watchlist": [("ICICIBANK", "₹1,227", "Near support ₹1,215. Watch for reversal confirmation."), ("SBIN", "₹985", "Holding above ₹980 support. PSU bank resilience.")],
    "notable_movers": [("HDFC Bank", 743.10, 1.10, 305.8, "Only banking stock in green"), ("HUL", 2150, 0.80, "—", "FMCG defensive buying"), ("ITC", 280, 0.50, "—", "FMCG steady")],
    "risk_notes": ["FII selling extreme (−₹8,363Cr) — position size small", "DII buying record (+₹9,589Cr) provides cushion", "VIX 15.36 declining — fear easing", "HDFC near 52W low — downside limited", "Time stop: 90 min if no progress"]
  },
  {
    "date": "2026-06-03", "label": "Jun 3", "day": "Wednesday",
    "nifty": 23405.60, "nifty_chg": -0.33, "bank_nifty": 54557,
    "vix": 16.28, "vix_chg": 6.01,
    "fii": -5616.56, "dii": 5740.89,
    "market_breadth": "Mixed — Pre-RBI positioning, VIX spiked +6%",
    "nifty_support": "23,150", "nifty_resistance": "23,500",
    "sector_performance": [("Banking", "✅ ICICI leading +1.26%"), ("FMCG", "✅ Positive"), ("IT", "❌ Weak"), ("Auto", "~ Neutral")],
    "news_catalysts": ["RBI policy decision tomorrow (Jun 5) — status quo expected", "ICICI Bank recovering strongly from low of ₹1,214", "VIX spiking +6% ahead of policy — nervousness building", "FII selling moderating slightly to −₹5,617 Cr"],
    "stocks": {
      "ICICI": {"close": 1242.00, "chg": 1.26, "vol_lakhs": 139.35, "avg_vol_lakhs": 140, "ema20": 1250, "ema50": 1240,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "❌ FAIL",
        "momentum_d": "+1.26%, strong recovery from ₹1,214 low. Higher low forming. Approaching 20EMA.",
        "volume_d": "Volume 139L near avg. Solid recovery on normal participation.",
        "volatility_d": "ATR adequate. Good intraday recovery.",
        "sentiment_d": "Pre-RBI optimism. FII selling −₹5,617 Cr but DII matching.",
        "sr_d": "Bounced from ₹1,215 support. Resistance ₹1,260 (20EMA).",
        "rr_d": "Entry ₹1,240, SL ₹1,215 (−2%), T ₹1,270 (+2.4%). R:R 1:1.2.",
        "sector_d": "Banking sector steady. ICICI leading the recovery.",
        "emotion_d": "VIX spiking 6% to 16.28. Pre-RBI nervousness.",
        "status": "winner"
      },
      "Axis": {"close": 1255.20, "chg": 0.33, "vol_lakhs": 79.50, "avg_vol_lakhs": 70, "ema20": 1280, "ema50": 1265,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "✅ PASS", "emotion": "❌ FAIL",
        "momentum_d": "+0.33%, flat. Struggling below EMAs.",
        "volume_d": "Volume 80L near avg. No urgency.",
        "volatility_d": "Adequate.",
        "sentiment_d": "Pre-RBI wait-and-watch.",
        "sr_d": "Stuck between ₹1,250−₹1,270.",
        "rr_d": "Tight range. No clear setup.",
        "sector_d": "Banking steady.",
        "emotion_d": "VIX elevated.",
        "status": "fail"
      },
      "HDFC": {"close": 745.95, "chg": 0.38, "vol_lakhs": 281.00, "avg_vol_lakhs": 300, "ema20": 744, "ema50": 748,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "✅ PASS", "rr": "❌ FAIL", "sector": "✅ PASS", "emotion": "❌ FAIL",
        "momentum_d": "+0.38%, near flat. Struggling at 20EMA.",
        "volume_d": "Volume 281L near avg. No conviction.",
        "volatility_d": "Adequate.",
        "sentiment_d": "No catalyst.",
        "sr_d": "Held ₹742 support. But not breaking out.",
        "rr_d": "Tight ₹740−₹750 range. Low R/R.",
        "sector_d": "Banking steady.",
        "emotion_d": "VIX elevated.",
        "status": "neutral"
      }
    },
    "final_pick": "ICICI",
    "final_pick_data": {"entry_zone": "₹1,238 – ₹1,242", "entry_mid": 1240, "stop_loss": "₹1,215", "sl_val": 1215, "target_1": "₹1,270", "t1_val": 1270, "target_2": "₹1,290", "t2_val": 1290, "risk_pct": -2.0, "reward_pct_1": 2.4, "reward_pct_2": 4.0, "time_horizon": "Intraday to 2 sessions", "why": "Strongest recovery (+1.26%) from ₹1,214 low. Higher low forming. Approaching 20EMA. Volume near average. Pre-RBI optimism. Support at ₹1,215 firmly held."},
    "alt_watchlist": [("HDFCBANK", "₹746", "Holding ₹740 support. Waiting for breakout above ₹750."), ("KOTAKBANK", "₹1,850", "Consolidating near support. Watch.")],
    "notable_movers": [("ICICI Bank", 1242.00, 1.26, 139.4, "Strong recovery leader"), ("HDFC Bank", 745.95, 0.38, 281.0, "Holding support"), ("SBI", 990, 0.60, "—", "PSU bank steady")],
    "risk_notes": ["Pre-RBI event risk — position sizing cautious", "VIX +6% indicates nervousness", "FII still selling ₹5,617Cr", "RBI policy could trigger sharp moves"]
  },
  {
    "date": "2026-06-04", "label": "Jun 4", "day": "Thursday",
    "nifty": 23416.55, "nifty_chg": 0.05, "bank_nifty": 54400,
    "vix": 15.89, "vix_chg": -2.41,
    "fii": -4447.06, "dii": 4360.14,
    "market_breadth": "Flat — RBI policy eve, cautious trading",
    "nifty_support": "23,200", "nifty_resistance": "23,550",
    "sector_performance": [("Banking", "✅ ICICI +0.78% leading"), ("FMCG", "~ Neutral"), ("Auto", "~ Neutral"), ("PSU Banks", "✅ Positive")],
    "news_catalysts": ["RBI monetary policy decision tomorrow", "VIX declining −2.41% — pre-policy calm", "FII selling moderating to −₹4,447 Cr", "ICICI Bank highest volume of the week (195L)"],
    "stocks": {
      "ICICI": {"close": 1251.70, "chg": 0.78, "vol_lakhs": 194.62, "avg_vol_lakhs": 140, "ema20": 1245, "ema50": 1238,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "2nd consecutive green (+0.78%). Reclaiming 20EMA. Higher lows since ₹1,214.",
        "volume_d": "Volume 195L — 39% above avg. Highest of the week. Accumulation.",
        "volatility_d": "ATR ~₹19 (1.5%). Good intraday range.",
        "sentiment_d": "Pre-RBI optimism. DIIs +₹4,360 Cr stable. FII selling slowing.",
        "sr_d": "Held ₹1,232 low. Support ₹1,230 firm. Resistance ₹1,270.",
        "rr_d": "Entry ₹1,250, SL ₹1,230 (−1.6%), T ₹1,280 (+2.4%). R:R 1:1.5.",
        "sector_d": "Banking sector resilient. ICICI outperforming.",
        "emotion_d": "VIX declining 2.4% to 15.89. Calm before policy.",
        "status": "winner"
      },
      "Axis": {"close": 1253.30, "chg": -0.15, "vol_lakhs": 63.90, "avg_vol_lakhs": 70, "ema20": 1275, "ema50": 1260,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "✅ PASS",
        "momentum_d": "−0.15%, still below both EMAs. No recovery.",
        "volume_d": "Volume 64L below avg. Low participation.",
        "volatility_d": "Adequate.",
        "sentiment_d": "No catalyst. Waiting for policy.",
        "sr_d": "Support ₹1,240. Resistance ₹1,280.",
        "rr_d": "No momentum setup.",
        "sector_d": "Banking mixed. Axis lagging.",
        "emotion_d": "VIX declining — neutral.",
        "status": "fail"
      },
      "HDFC": {"close": 745.10, "chg": -0.11, "vol_lakhs": 226.30, "avg_vol_lakhs": 300, "ema20": 743, "ema50": 747,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "✅ PASS",
        "momentum_d": "−0.11%, flat. Still near 52W low territory.",
        "volume_d": "Volume 226L below avg. No accumulation.",
        "volatility_d": "Adequate.",
        "sentiment_d": "No positive catalyst.",
        "sr_d": "₹740−₹750 range. No breakout.",
        "rr_d": "No clear entry point.",
        "sector_d": "Banking mixed. HDFC lagging.",
        "emotion_d": "VIX declining — neutral.",
        "status": "fail"
      }
    },
    "final_pick": "ICICI",
    "final_pick_data": {"entry_zone": "₹1,248 – ₹1,252", "entry_mid": 1250, "stop_loss": "₹1,230", "sl_val": 1230, "target_1": "₹1,280", "t1_val": 1280, "target_2": "₹1,300", "t2_val": 1300, "risk_pct": -1.6, "reward_pct_1": 2.4, "reward_pct_2": 4.0, "time_horizon": "Intraday to 2 sessions", "why": "2nd consecutive green day. Highest volume of the week (195L) — institutional accumulation. Reclaiming 20EMA. VIX declining. FII selling slowing. Pre-RBI optimism building."},
    "alt_watchlist": [("AXISBANK", "₹1,253", "Still below EMAs. Wait for recovery."), ("SBIN", "₹995", "PSU bank steady, holding ₹990 support.")],
    "notable_movers": [("ICICI Bank", 1251.70, 0.78, 194.6, "Highest volume of week. Accumulation"), ("PNB", 135, 1.20, "—", "PSU bank rallying"), ("SBI", 995, 0.40, "—", "Steady")],
    "risk_notes": ["RBI policy tomorrow — binary event risk", "Position sizing: 1% capital max", "VIX 15.89 — moderate fear", "Time stop if policy outcome unexpected"]
  },
  {
    "date": "2026-06-05", "label": "Jun 5", "day": "Friday",
    "nifty": 23366.70, "nifty_chg": -0.21, "bank_nifty": 54300,
    "vix": 15.79, "vix_chg": -0.61,
    "fii": -8776.25, "dii": 9133.57,
    "market_breadth": "Mixed — RBI kept repo rate unchanged at 5.25%, hawkish tone",
    "nifty_support": "23,150", "nifty_resistance": "23,500",
    "sector_performance": [("Banking", "✅ ICICI +0.83% positive despite hawkish RBI"), ("FMCG", "✅ Positive"), ("Realty", "✅ Surged post-RBI"), ("Auto", "~ Neutral")],
    "news_catalysts": ["RBI kept repo rate unchanged at 5.25% (expected)", "Hawkish tone on inflation — rates may stay higher for longer", "Realty stocks surged on steady rate outlook", "FII sold −₹8,776 Cr — aggressive despite policy status quo", "DII matched with +₹9,134 Cr buying"],
    "stocks": {
      "ICICI": {"close": 1262.10, "chg": 0.83, "vol_lakhs": 101.66, "avg_vol_lakhs": 140, "ema20": 1248, "ema50": 1240,
        "momentum": "✅ PASS", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "❌ FAIL",
        "momentum_d": "3rd consecutive green (+0.83%). Now above 20EMA (₹1,248). Higher low sequence intact.",
        "volume_d": "Volume 102L below avg 140L (−27%). Low participation on rally.",
        "volatility_d": "ATR adequate. RBI-induced volatility.",
        "sentiment_d": "RBI status quo positive for banking spreads. DIIs +₹9,134 Cr supportive.",
        "sr_d": "Support ₹1,250 firm. Resistance now ₹1,280 (50EMA).",
        "rr_d": "Entry ₹1,260, SL ₹1,240 (−1.6%), T ₹1,290 (+2.4%). R:R 1:1.5.",
        "sector_d": "Banking sector resilient post-RBI. ICICI outperforming peers.",
        "emotion_d": "VIX 15.79 (−0.6%) stable. But FII −₹8,776 Cr is concerning.",
        "status": "winner"
      },
      "Axis": {"close": 1260.00, "chg": 0.65, "vol_lakhs": 55.00, "avg_vol_lakhs": 70, "ema20": 1272, "ema50": 1262,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "❌ FAIL", "sector": "✅ PASS", "emotion": "❌ FAIL",
        "momentum_d": "+0.65% but still below 20EMA (₹1,272). Weak recovery.",
        "volume_d": "Volume 55L below avg. Low conviction.",
        "volatility_d": "Adequate.",
        "sentiment_d": "RBI status quo. DII buying supportive.",
        "sr_d": "Support ₹1,240. Resistance ₹1,290.",
        "rr_d": "Entry ₹1,260, SL ₹1,240, T ₹1,285. R:R < 1:1.25.",
        "sector_d": "Banking steady.",
        "emotion_d": "VIX stable but FII heavy selling.",
        "status": "neutral"
      },
      "HDFC": {"close": 740.60, "chg": -0.60, "vol_lakhs": 228.00, "avg_vol_lakhs": 300, "ema20": 742, "ema50": 746,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "−0.60%, rejected from 20EMA. Weak.",
        "volume_d": "Volume 228L below avg. Distribution.",
        "volatility_d": "Adequate.",
        "sentiment_d": "Hawkish RBI tone hurt rate-sensitive stocks.",
        "sr_d": "Broke ₹742. Heading back to ₹730 support.",
        "rr_d": "Downtrending. Avoid.",
        "sector_d": "HDFC underperforming sector.",
        "emotion_d": "VIX stable but FII selling heavy.",
        "status": "fail"
      }
    },
    "final_pick": "ICICI",
    "final_pick_data": {"entry_zone": "₹1,258 – ₹1,262", "entry_mid": 1260, "stop_loss": "₹1,240", "sl_val": 1240, "target_1": "₹1,290", "t1_val": 1290, "target_2": "₹1,310", "t2_val": 1310, "risk_pct": -1.6, "reward_pct_1": 2.4, "reward_pct_2": 4.0, "time_horizon": "Intraday to 2 sessions", "why": "3rd consecutive green day. Above 20EMA for first time this week. RBI status quo positive for banking spreads. Higher low sequence intact. Support ₹1,250 firm. Volume low but momentum strong."},
    "alt_watchlist": [("HDFCBANK", "₹741", "Near 52W low ₹727. Potential bounce play but no confirmation yet."), ("DLF", "₹890", "Realty surging post-RBI. Sector tailwind.")],
    "notable_movers": [("ICICI Bank", 1262.10, 0.83, 101.7, "3rd green, above 20EMA"), ("DLF", 890, 2.50, "—", "Realty rally post-RBI"), ("Godrej Properties", 2850, 2.10, "—", "Realty momentum")],
    "risk_notes": ["FII sold −₹8,776 Cr despite RBI status quo — structural selling", "DII +₹9,134 Cr fully matched FII outflows", "VIX 15.79 stable", "Real estate is the real post-RBI winner — banking steady", "Position size 1% given FII overhang"]
  },
  {
    "date": "2026-06-08", "label": "Jun 8", "day": "Monday",
    "nifty": 23123.00, "nifty_chg": -1.04, "bank_nifty": 53900,
    "vix": 17.03, "vix_chg": 7.85,
    "fii": -5555.67, "dii": 5165.24,
    "market_breadth": "Negative — Post-RBI selloff, VIX spiked to 17.03",
    "nifty_support": "23,000", "nifty_resistance": "23,400",
    "sector_performance": [("Banking", "❌ All banks negative"), ("IT", "❌ Sharp decline"), ("FMCG", "~ Defensive holding"), ("Realty", "❌ Profit booking post-rally")],
    "news_catalysts": ["Post-RBI selloff — market digesting hawkish tone", "VIX spiked +7.85% to 17.03 — highest of the period", "FII sold −₹5,556 Cr", "Nifty broke below 23,200 support", "Global markets weak on rate concerns"],
    "stocks": {
      "ICICI": {"close": 1250.20, "chg": -0.94, "vol_lakhs": 107.14, "avg_vol_lakhs": 140, "ema20": 1252, "ema50": 1242,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "✅ PASS", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "−0.94% but held above ₹1,243. Best performer of the three on a bad day.",
        "volume_d": "Volume 107L below avg. No panic selling.",
        "volatility_d": "ATR adequate. Spike in volatility.",
        "sentiment_d": "FII selling −₹5,556 Cr. Post-RBI hangover.",
        "sr_d": "Held ₹1,243 support (just above 50EMA ₹1,242). Resilient.",
        "rr_d": "No buy signal. Wait for confirmation.",
        "sector_d": "Banking down but ICICI holding support.",
        "emotion_d": "VIX 17.03 — highest of period. Fear elevated.",
        "status": "neutral"
      },
      "Axis": {"close": 1238.00, "chg": -1.70, "vol_lakhs": 60.00, "avg_vol_lakhs": 70, "ema20": 1265, "ema50": 1255,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "−1.70%, broke below ₹1,250 support. Weakest of the three.",
        "volume_d": "Volume 60L near avg. No panic but no support either.",
        "volatility_d": "Adequate.",
        "sentiment_d": "Very weak. FII heavy selling in banking.",
        "sr_d": "Broke ₹1,250. Next support ₹1,220.",
        "rr_d": "Downtrending. Avoid.",
        "sector_d": "Underperforming badly.",
        "emotion_d": "VIX at period high.",
        "status": "fail"
      },
      "HDFC": {"close": 729.95, "chg": -1.44, "vol_lakhs": 191.60, "avg_vol_lakhs": 300, "ema20": 741, "ema50": 745,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "❌ FAIL",
        "momentum_d": "−1.44%, near 52W low ₹727. Very weak.",
        "volume_d": "Volume 192L well below avg. Distribution.",
        "volatility_d": "Adequate.",
        "sentiment_d": "Post-RBI selling pressure.",
        "sr_d": "Testing ₹727 52W low. Critical level.",
        "rr_d": "Too risky near 52W low.",
        "sector_d": "Banking all weak.",
        "emotion_d": "VIX at period high. Fear.",
        "status": "fail"
      }
    },
    "final_pick": None,
    "final_pick_data": None,
    "alt_watchlist": [("ICICIBANK", "₹1,250", "Held ₹1,243 support. Watch for bounce confirmation."), ("HDFCBANK", "₹730", "Near 52W low ₹727. Potential double bottom.")],
    "notable_movers": [("ICICI Bank", 1250.20, -0.94, 107.1, "Best of the bad lot — held support"), ("HDFC Bank", 729.95, -1.44, 191.6, "Testing 52W low"), ("Nifty", 23123, -1.04, "—", "Worst day of period")],
    "risk_notes": ["VIX 17.03 — highest of the period. DEFENSIVE mode", "FII sold −₹5,556 Cr", "Nifty broke 23,200 support", "NO TRADE — let the dust settle", "Wait for VIX to decline below 16"]
  },
  {
    "date": "2026-06-09", "label": "Jun 9", "day": "Tuesday",
    "nifty": 23242.10, "nifty_chg": 0.52, "bank_nifty": 55555,
    "vix": 15.58, "vix_chg": -8.53,
    "fii": -4566.03, "dii": 6159.48,
    "market_breadth": "Strong — BANK NIFTY BREAKOUT! 2-month high of 55,555",
    "nifty_support": "23,100", "nifty_resistance": "23,450",
    "sector_performance": [("Banking", "🔥🔥 ON FIRE — Breakout day!"), ("Financial Services", "✅ Strong"), ("Auto", "✅ Positive"), ("FMCG", "~ Neutral")],
    "news_catalysts": ["🚀 BANK NIFTY HIT 2-MONTH HIGH OF 55,555.85!", "All 5 major banks participating simultaneously — rare event", "VIX CRASHED −8.53% to 15.58 — fear evaporating", "ICICI Bank volume 224L — 2x average", "Axis Bank led with +3.8% — breakout leader", "SBI held above ₹1,000 for 2nd day"],
    "stocks": {
      "ICICI": {"close": 1275.00, "chg": 1.98, "vol_lakhs": 223.69, "avg_vol_lakhs": 140, "ema20": 1250, "ema50": 1243,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "+1.98%, broke above ₹1,270 resistance. Well above both EMAs. Higher high formed.",
        "volume_d": "Volume 224L — 60% above avg. MASSIVE accumulation!",
        "volatility_d": "ATR ~₹20. Breakout volatility.",
        "sentiment_d": "Bank Nifty breakout! FII selling slowing. DII +₹6,159 Cr. All banks firing.",
        "sr_d": "Broke ₹1,270 resistance. New support ₹1,270. Next resistance ₹1,320.",
        "rr_d": "Entry ₹1,270, SL ₹1,250 (−1.6%), T1 ₹1,310 (+3.1%), T2 ₹1,330 (+4.7%). R:R 1:2+.",
        "sector_d": "🔥 Banking is THE sector today. Bank Nifty 2-month high.",
        "emotion_d": "VIX crashed 8.5% to 15.58. Fear gone. Institutional buying.",
        "status": "winner"
      },
      "Axis": {"close": 1285.00, "chg": 3.80, "vol_lakhs": 150.00, "avg_vol_lakhs": 70, "ema20": 1270, "ema50": 1260,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "+3.80% — BEST of the three! Massive breakout above EMAs.",
        "volume_d": "Volume 150L — 114% above avg. HUGE surge!",
        "volatility_d": "High breakout volatility.",
        "sentiment_d": "Breakout leader. Best % gainer in banking.",
        "sr_d": "Broke ₹1,270. Next resistance ₹1,330.",
        "rr_d": "Entry ₹1,280, SL ₹1,250 (−2.3%), T1 ₹1,330 (+3.9%), T2 ₹1,360 (+6.3%). R:R 1:1.7+.",
        "sector_d": "🔥🔥 Banking sector champion!",
        "emotion_d": "VIX crashing. Risk-on mode.",
        "status": "winner"
      },
      "HDFC": {"close": 730.85, "chg": 0.12, "vol_lakhs": 306.10, "avg_vol_lakhs": 300, "ema20": 740, "ema50": 744,
        "momentum": "❌ FAIL", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "+0.12%, flat. Still near 52W low. Lagging badly.",
        "volume_d": "Volume 306L near avg. Moderate participation.",
        "volatility_d": "Adequate.",
        "sentiment_d": "Sector breakout but stock not participating.",
        "sr_d": "Still stuck near ₹730−₹740.",
        "rr_d": "No breakout. Lagging.",
        "sector_d": "Sector strong but HDFC lagging.",
        "emotion_d": "VIX crash positive for sentiment.",
        "status": "fail"
      }
    },
    "final_pick": "Axis",
    "final_pick_data": {"entry_zone": "₹1,275 – ₹1,285", "entry_mid": 1280, "stop_loss": "₹1,250", "sl_val": 1250, "target_1": "₹1,330", "t1_val": 1330, "target_2": "₹1,360", "t2_val": 1360, "risk_pct": -2.3, "reward_pct_1": 3.9, "reward_pct_2": 6.3, "time_horizon": "Intraday to 3 sessions", "why": "🚀 BREAKOUT LEADER! +3.80% — best of all banking stocks. Volume surged 114% above average. Bank Nifty hit 2-month high of 55,555. All 5 major banks firing. VIX crashed 8.5%. FII selling eased. DII buying strong."},
    "alt_watchlist": [("ICICIBANK", "₹1,275", "Strong #2 pick. +1.98%, 60% volume surge. Excellent setup."), ("SBIN", "₹1,003", "₹1,000 holds for 3rd day. Institutional confirmation.")],
    "notable_movers": [("Axis Bank", 1285.00, 3.80, 150.0, "🥇 BREAKOUT LEADER"), ("ICICI Bank", 1275.00, 1.98, 223.7, "Solid #2, massive volume"), ("SBI", 1003, 1.20, "—", "₹1,000 held for 3d"), ("Bank Nifty", 55555, 2.09, "—", "2-MONTH HIGH!")],
    "risk_notes": ["VIX crashed 8.5% — fear gauge tumbling", "FII selling −₹4,566 Cr but DII +₹6,159 Cr more than covers it", "Bank Nifty breakout is the REAL DEAL — follow-through expected", "Position size 2-3% — HIGH CONVICTION day", "Time stop: hold up to 3 sessions"]
  },
  {
    "date": "2026-06-10", "label": "Jun 10", "day": "Wednesday",
    "nifty": 23214.95, "nifty_chg": -0.12, "bank_nifty": 55100,
    "vix": 15.63, "vix_chg": 0.37,
    "fii": -2124.98, "dii": 3123.95,
    "market_breadth": "Consolidation — Banking held gains, US CPI awaited",
    "nifty_support": "23,100", "nifty_resistance": "23,500",
    "sector_performance": [("Banking", "✅ Follow-through — all banks green intraday"), ("IT", "❌ Sharp fall −1.5%"), ("FMCG", "✅ HUL breakout"), ("Midcap", "❌ Underperformance")],
    "news_catalysts": ["Follow-through day after Bank Nifty breakout", "ICICI hit ₹1,306 intraday (+1.83%)", "HDFC Bank showed LIFE — ₹755.95 high (+1.15%), vol 392L", "ALL 5 major banks + SBI participating simultaneously (rare)", "US CPI data awaited tonight — global markets on edge", "FII selling lowest of period (−₹2,125 Cr)"],
    "stocks": {
      "ICICI": {"close": 1298.00, "chg": 1.83, "vol_lakhs": 180.00, "avg_vol_lakhs": 140, "ema20": 1255, "ema50": 1245,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "Hit ₹1,306 intraday (+1.83%). Extended breakout. Well above EMAs.",
        "volume_d": "Volume elevated. Follow-through buying.",
        "volatility_d": "Breakout volatility healthy.",
        "sentiment_d": "Lowest FII selling of period. DII +₹3,124 Cr. All banks firing.",
        "sr_d": "New resistance at ₹1,320. Support ₹1,270 (prior breakout level).",
        "rr_d": "Entry ₹1,295, SL ₹1,270 (−1.9%), T1 ₹1,330 (+2.7%), T2 ₹1,350 (+4.2%). R:R good.",
        "sector_d": "🔥 Banking continues to lead. All banks participating.",
        "emotion_d": "VIX stable at 15.63. FII selling lowest. Confidence returning.",
        "status": "winner"
      },
      "Axis": {"close": 1305.00, "chg": 1.60, "vol_lakhs": 110.00, "avg_vol_lakhs": 70, "ema20": 1275, "ema50": 1260,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "+1.60%, hit ₹1,326.50 intraday. Following up on breakout.",
        "volume_d": "Volume 110L above avg. Solid follow-through.",
        "volatility_d": "Healthy.",
        "sentiment_d": "FII selling easing. Sector momentum strong.",
        "sr_d": "Support ₹1,280. Resistance ₹1,350.",
        "rr_d": "Entry ₹1,300, SL ₹1,275, T ₹1,340. R:R 1:1.6.",
        "sector_d": "🔥 Banking leading.",
        "emotion_d": "VIX stable. Confidence returning.",
        "status": "winner"
      },
      "HDFC": {"close": 738.80, "chg": 1.09, "vol_lakhs": 391.70, "avg_vol_lakhs": 300, "ema20": 739, "ema50": 743,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "+1.09%, hit ₹755.95 intraday. FINALLY showing life!",
        "volume_d": "Volume 392L — 31% above avg. HIGHEST in 10 days!",
        "volatility_d": "ATR expanding.",
        "sentiment_d": "Finally joining banking rally. DII supportive.",
        "sr_d": "Broke ₹740 resistance. Next resistance ₹755.",
        "rr_d": "Entry ₹740, SL ₹728 (−1.6%), T ₹760 (+2.7%). R:R 1:1.7.",
        "sector_d": "🔥 Banking sector strong.",
        "emotion_d": "VIX stable. Risk-on.",
        "status": "winner"
      }
    },
    "final_pick": "ICICI",
    "final_pick_data": {"entry_zone": "₹1,290 – ₹1,298", "entry_mid": 1295, "stop_loss": "₹1,270", "sl_val": 1270, "target_1": "₹1,330", "t1_val": 1330, "target_2": "₹1,350", "t2_val": 1350, "risk_pct": -1.9, "reward_pct_1": 2.7, "reward_pct_2": 4.2, "time_horizon": "Intraday to 2 sessions", "why": "Follow-through on breakout. Hit ₹1,306 intraday. FII selling LOWEST of entire period (−₹2,125 Cr). HDFC joining rally confirms sector breadth. All 8 criteria PASSED."},
    "alt_watchlist": [("HDFCBANK", "₹739", "Came alive with 392L volume. New momentum play."), ("AXISBANK", "₹1,305", "Strong follow-through. Hit ₹1,326 intraday.")],
    "notable_movers": [("ICICI Bank", 1298.00, 1.83, 180.0, "Hit ₹1,306 — extended breakout"), ("HDFC Bank", 738.80, 1.09, 391.7, "ALIVE! 10-day high volume"), ("Axis Bank", 1305.00, 1.60, 110.0, "Hit ₹1,326.50"), ("HUL", 2169, 1.71, "—", "FMCG breakout")],
    "risk_notes": ["US CPI tonight — potential gap risk", "FII selling lowest of period — positive sign", "All banks participating = sustainable rally", "HDFC joining rally is KEY confirmation", "Position size 2% — high conviction"]
  },
  {
    "date": "2026-06-11", "label": "Jun 11", "day": "Thursday",
    "nifty": 23161.60, "nifty_chg": -0.23, "bank_nifty": 54900,
    "vix": 15.60, "vix_chg": -0.24,
    "fii": -1987.09, "dii": 4224.51,
    "market_breadth": "Mixed — Post-US CPI, Nifty slightly negative but banking held",
    "nifty_support": "23,050", "nifty_resistance": "23,400",
    "sector_performance": [("Banking", "✅ ICICI +1.46% held strong"), ("IT", "❌ Weak"), ("FMCG", "✅ Defensive"), ("Auto", "~ Neutral")],
    "news_catalysts": ["US CPI data released overnight — market reaction muted", "ICICI Bank hit ₹1,317 — 4th consecutive green day", "FII selling lowest of period at −₹1,987 Cr", "Banking sector resilience despite Nifty weakness", "Axis Bank also held gains (+0.8%)"],
    "stocks": {
      "ICICI": {"close": 1317.00, "chg": 1.46, "vol_lakhs": 160.00, "avg_vol_lakhs": 140, "ema20": 1260, "ema50": 1248,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "4th consecutive green! Hit ₹1,317. EXTENDED uptrend. Well above all EMAs.",
        "volume_d": "Volume 160L above avg. Sustained accumulation.",
        "volatility_d": "Healthy ATR. Trending well.",
        "sentiment_d": "FII selling LOWEST of period (−₹1,987 Cr). DII +₹4,225 Cr supportive.",
        "sr_d": "₹1,300 now support. Resistance ₹1,370 (prior swing).",
        "rr_d": "Entry ₹1,310, SL ₹1,285 (−1.9%), T1 ₹1,350 (+3.1%), T2 ₹1,370 (+4.6%). R:R 1:1.6+.",
        "sector_d": "🔥 Banking strongest sector. ICICI leader.",
        "emotion_d": "VIX 15.60 stable. FII selling collapsed. Confidence high.",
        "status": "winner"
      },
      "Axis": {"close": 1315.00, "chg": 0.80, "vol_lakhs": 90.00, "avg_vol_lakhs": 70, "ema20": 1280, "ema50": 1265,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "+0.80%, held gains well. Above EMAs.",
        "volume_d": "Volume 90L above avg. Steady.",
        "volatility_d": "Healthy.",
        "sentiment_d": "Sector momentum supportive. FII easing.",
        "sr_d": "Support ₹1,290. Resistance ₹1,350.",
        "rr_d": "Entry ₹1,310, SL ₹1,285, T ₹1,345. R:R 1:1.4.",
        "sector_d": "🔥 Banking strong.",
        "emotion_d": "VIX stable.",
        "status": "winner"
      },
      "HDFC": {"close": 735.30, "chg": -0.47, "vol_lakhs": 269.60, "avg_vol_lakhs": 300, "ema20": 738, "ema50": 742,
        "momentum": "❌ FAIL", "volume": "❌ FAIL", "volatility": "✅ PASS", "sentiment": "❌ FAIL",
        "sr": "❌ FAIL", "rr": "❌ FAIL", "sector": "❌ FAIL", "emotion": "✅ PASS",
        "momentum_d": "−0.47%, gave back some gains. Still near lows.",
        "volume_d": "Volume 270L below avg. Profit-taking.",
        "volatility_d": "Adequate.",
        "sentiment_d": "Profit-taking after yesterday's surge.",
        "sr_d": "Back near ₹735 support. Resistance ₹755.",
        "rr_d": "Pullback mode. Wait.",
        "sector_d": "Banking strong but HDFC lagging again.",
        "emotion_d": "VIX stable.",
        "status": "fail"
      }
    },
    "final_pick": "ICICI",
    "final_pick_data": {"entry_zone": "₹1,305 – ₹1,315", "entry_mid": 1310, "stop_loss": "₹1,285", "sl_val": 1285, "target_1": "₹1,350", "t1_val": 1350, "target_2": "₹1,370", "t2_val": 1370, "risk_pct": -1.9, "reward_pct_1": 3.1, "reward_pct_2": 4.6, "time_horizon": "Intraday to 2 sessions", "why": "4th consecutive green day. Hit ₹1,317. FII selling collapsed to lowest of period (−₹1,987 Cr). ₹1,300 now acts as support. Banking sector continues to lead. VIX stable at 15.60."},
    "alt_watchlist": [("AXISBANK", "₹1,315", "2nd best pick. Solid follow-through."), ("HDFCBANK", "₹735", "Pullback after big volume day. Watch for re-entry.")],
    "notable_movers": [("ICICI Bank", 1317.00, 1.46, 160.0, "4th green, ₹1,317 🚀"), ("Axis Bank", 1315.00, 0.80, 90.0, "Held gains well"), ("Nifty", 23161.60, -0.23, "—", "Muted post-US CPI")],
    "risk_notes": ["FII selling collapsed to −₹1,987 Cr — biggest positive sign", "DII +₹4,225 Cr continues to absorb", "VIX 15.60 stable — no fear", "ICICI extended 4 days — trail stops", "Position size 2%"]
  },
  {
    "date": "2026-06-12", "label": "Jun 12", "day": "Friday",
    "nifty": 23436.00, "nifty_chg": 1.19, "bank_nifty": 55177,
    "vix": 14.72, "vix_chg": -5.70,
    "fii": None, "dii": None,
    "market_breadth": "Strong — Wall Street rally spillover, VIX crashed to period low",
    "nifty_support": "23,300", "nifty_resistance": "23,600",
    "sector_performance": [("Banking", "🔥🔥 HDFC +2.04%, Axis +1.9%"), ("Realty", "▲ +2%"), ("Auto", "✅ Positive"), ("Capital Goods", "▲ L&T +3.57%")],
    "news_catalysts": ["✅ Wall Street rally spilled over to Asian markets", "India VIX crashed −5.70% to 14.72 — LOWEST of the period!", "US-Iran peace deal hopes boosting global risk sentiment", "Banking continues to lead — HDFC finally joined the party (+2.04%)", "ICICI Bank +5.22% for the week — period champion"],
    "stocks": {
      "ICICI": {"close": 1313.40, "chg": -0.27, "vol_lakhs": 155.00, "avg_vol_lakhs": 140, "ema20": 1265, "ema50": 1250,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "Slight pullback (−0.27%) after 4-day rally. Still +5.22% for the week. Well above EMAs.",
        "volume_d": "Volume 155L above avg. Healthy consolidation.",
        "volatility_d": "ATR adequate.",
        "sentiment_d": "VIX crashed to 14.72. DIIs supportive. Banking sector strong.",
        "sr_d": "Support ₹1,270 (10-day base). Resistance ₹1,370−₹1,400.",
        "rr_d": "Entry ₹1,310−₹1,320, SL ₹1,270 (−3.6%), T1 ₹1,370 (+4%), T2 ₹1,400 (+6.3%). R:R 1:2.3!",
        "sector_d": "🔥 Banking continues to lead all sectors.",
        "emotion_d": "VIX 14.72 − PERIOD LOW. Fear gone. Institutional confidence high.",
        "status": "winner"
      },
      "Axis": {"close": 1340.00, "chg": 1.90, "vol_lakhs": 95.00, "avg_vol_lakhs": 70, "ema20": 1285, "ema50": 1270,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "+1.90%, strong move. Above all EMAs. Momentum accelerating.",
        "volume_d": "Volume 95L above avg. Solid.",
        "volatility_d": "Healthy.",
        "sentiment_d": "VIX crash. Sector tailwind. FII selling likely minimal.",
        "sr_d": "Support ₹1,300. Resistance ₹1,380 (near 52W high ₹1,418).",
        "rr_d": "Entry ₹1,335, SL ₹1,300 (−2.6%), T ₹1,380 (+3.4%). R:R 1:1.3.",
        "sector_d": "🔥 Banking leading.",
        "emotion_d": "VIX low. Risk-on.",
        "status": "winner"
      },
      "HDFC": {"close": 750.30, "chg": 2.04, "vol_lakhs": 150.40, "avg_vol_lakhs": 300, "ema20": 740, "ema50": 744,
        "momentum": "✅ PASS", "volume": "✅ PASS", "volatility": "✅ PASS", "sentiment": "✅ PASS",
        "sr": "✅ PASS", "rr": "✅ PASS", "sector": "✅ PASS", "emotion": "✅ PASS",
        "momentum_d": "+2.04% — BEST % GAINER of the three today! Broke above 20EMA!",
        "volume_d": "Volume moderate at 150L (below avg but cleaner move).",
        "volatility_d": "ATR expanding after breakout.",
        "sentiment_d": "VIX crash. Sector strength. FINALLY joining the rally!",
        "sr_d": "Broke ₹740−₹750 resistance! Next resistance ₹765. Support ₹735.",
        "rr_d": "Entry ₹748, SL ₹730 (−2.4%), T1 ₹765 (+2.3%), T2 ₹775 (+3.6%). R:R 1:1.5.",
        "sector_d": "🔥 Banking continues to lead.",
        "emotion_d": "VIX at period low. All systems go.",
        "status": "winner"
      }
    },
    "final_pick": "ICICI",
    "final_pick_data": {"entry_zone": "₹1,310 – ₹1,320", "entry_mid": 1315, "stop_loss": "₹1,270", "sl_val": 1270, "target_1": "₹1,370", "t1_val": 1370, "target_2": "₹1,400", "t2_val": 1400, "risk_pct": -3.4, "reward_pct_1": 4.2, "reward_pct_2": 6.5, "time_horizon": "Intraday to 3 sessions", "why": "Period champion: +5.22% for the week. VIX at period low 14.72. Volume surge +73% above avg. Clear support at ₹1,270. Resistance ₹1,400 giving 1:2.3 R/R. Banking sector in full breakout mode."},
    "alt_watchlist": [("HDFCBANK", "₹750", "TODAY'S WINNER. Finally broke out. Catch-up play."), ("AXISBANK", "₹1,340", "Strong #2. +1.90% today, near 52W high."), ("SBIN", "₹1,005", "Holding ₹1,000. Consistent.")],
    "notable_movers": [("HDFC Bank", 750.30, 2.04, 150.4, "🥇 TODAY's BEST — breakout finally!"), ("Axis Bank", 1340.00, 1.90, 95.0, "Strong runner-up"), ("L&T", 4000, 3.57, "—", "Capital goods leader"), ("ICICI Bank", 1313.40, -0.27, 155.0, "Pausing after +5.22% week")],
    "risk_notes": ["VIX 14.72 — LOWEST OF PERIOD. Maximum risk-on", "FII data not yet available but likely muted", "ICICI taken profits after 4-day run — consolidation healthy", "HDFC breakout is THE new development", "Position size 2-3% — best setup of the period"]
  }
]


# ─────────────────────────────────────────────────────────
#  HTML TEMPLATE
# ─────────────────────────────────────────────────────────

def generate_html(day, counter):
    """Generate a beautiful standalone HTML page for a single day's analysis."""
    d = day
    fp = d["final_pick_data"]
    is_trade = d["final_pick"] is not None

    stocks_html = ""
    for sym, s in d["stocks"].items():
        is_winner = sym == d["final_pick"]
        border = 'style="border-color:#f59e0b;background:linear-gradient(135deg,rgba(245,158,11,0.08),rgba(239,68,68,0.05));"' if is_winner else ""
        badge = '<span style="font-size:11px;background:rgba(245,158,11,0.2);padding:2px 10px;border-radius:12px;color:#fbbf24;font-weight:600;margin-left:8px;">⭐ PICK</span>' if is_winner else ""

        criteria = [
            ("📈 Momentum", s["momentum"], s["momentum_d"]),
            ("📊 Volume", s["volume"], s["volume_d"]),
            ("⚡ Volatility", s["volatility"], s["volatility_d"]),
            ("💭 Sentiment", s["sentiment"], s["sentiment_d"]),
            ("🛡️ S/R", s["sr"], s["sr_d"]),
            ("🎯 R/R", s["rr"], s["rr_d"]),
            ("🏭 Sector", s["sector"], s["sector_d"]),
            ("❤️ Emotion", s["emotion"], s["emotion_d"]),
        ]
        criteria_html = "".join(
            f'''<div class="crit {'pass' if c[1]=='✅ PASS' else 'fail' if c[1]=='❌ FAIL' else 'neutral'}">
                  <span class="crit-icon">{'✅' if c[1]=='✅ PASS' else '❌' if c[1]=='❌ FAIL' else '◐'}</span>
                  <span class="crit-label">{c[0]}</span>
                  <span class="crit-status">{c[1]}</span>
                  <div class="crit-detail">{c[2]}</div>
                </div>'''
            for c in criteria
        )

        chg_cls = "green" if s["chg"] >= 0 else "red"
        stocks_html += f"""
        <div class="stock-card" {border}>
          <div class="stock-header">
            <span class="stock-name">{sym} {badge}</span>
            <span class="stock-price">₹{s['close']:,.2f}</span>
            <span class="stock-chg {chg_cls}">{s['chg']:+.2f}%</span>
            <span class="stock-vol">Vol: {s['vol_lakhs']:.1f}L (avg {s['avg_vol_lakhs']}L)</span>
          </div>
          <div class="criteria-row">
            {criteria_html}
          </div>
        </div>"""

    # Alt watchlist
    alt_html = ""
    for item in d["alt_watchlist"]:
        alt_html += f"""<tr><td>{item[0]}</td><td>{item[1]}</td><td style="color:#9ca3af;">{item[2]}</td></tr>"""
    if not alt_html:
        alt_html = """<tr><td colspan="3" style="color:#6b7a93;text-align:center;">None — no clear alternatives</td></tr>"""

    # Notable movers
    movers_html = ""
    for m in d["notable_movers"]:
        chg_cls = "green" if m[2] >= 0 else "red"
        movers_html += f"""<tr><td>{m[0]}</td><td>₹{m[1]:,.2f}</td><td class="{chg_cls}">{m[2]:+.2f}%</td><td>{m[3]}</td><td style="color:#9ca3af;">{m[4]}</td></tr>"""
    if not movers_html:
        movers_html = """<tr><td colspan="5" style="color:#6b7a93;text-align:center;">No notable movers identified</td></tr>"""

    # Sector perf
    sector_html = ""
    for name, perf in d["sector_performance"]:
        sector_html += f"""<div class="stat-chip"><span class="label">{name}</span><span class="value">{perf[:2] == '🔥' and '🔥' or perf[:2] == '✅' and '✅' or perf[:2] == '❌' and '❌' or '~'} {perf}</span></div>"""

    # Risk notes
    risk_html = "".join(f"<li>{note}</li>" for note in d["risk_notes"])

    # News
    news_html = "".join(f"<li>{n}</li>" for n in d["news_catalysts"])

    # Pre-compute display values (avoids nested f-string issues)
    fii_display = "TBD"
    if d.get("fii") is not None:
        fii_val = d["fii"]
        if fii_val < 0:
            fii_display = f"−₹{abs(fii_val):,.0f} Cr"
        else:
            fii_display = f"+₹{fii_val:,.0f} Cr"
    dii_display = "TBD"
    if d.get("dii") is not None:
        dii_val = d["dii"]
        dii_display = f"+₹{dii_val:,.0f} Cr"

    # Build pick box
    pick_box = ""
    if is_trade and fp:
        pick_box = f"""
        <div class="pick-box">
          <div class="pick-title">⭐ FINAL PICK — {d['final_pick']} ⭐</div>
          <div class="pick-grid">
            <div class="pick-item"><span class="pick-label">Entry Zone</span><span class="pick-val">{fp['entry_zone']}</span></div>
            <div class="pick-item"><span class="pick-label">Stop Loss</span><span class="pick-val" style="color:#ef4444;">{fp['stop_loss']} ({fp['risk_pct']:.1f}%)</span></div>
            <div class="pick-item"><span class="pick-label">Target 1</span><span class="pick-val" style="color:#22c55e;">{fp['target_1']} ({fp['reward_pct_1']:.1f}%)</span></div>
            <div class="pick-item"><span class="pick-label">Target 2</span><span class="pick-val" style="color:#22c55e;">{fp['target_2']} ({fp['reward_pct_2']:.1f}%)</span></div>
            <div class="pick-item"><span class="pick-label">Risk:Reward</span><span class="pick-val" style="color:#f59e0b;">1:{abs(fp['reward_pct_2']/fp['risk_pct']):.1f}</span></div>
            <div class="pick-item"><span class="pick-label">Time Horizon</span><span class="pick-val">{fp['time_horizon']}</span></div>
          </div>
          <div class="pick-why">{fp['why']}</div>
        </div>"""

    no_trade_box = ""
    if not is_trade:
        no_trade_box = """
        <div class="no-trade-box">
          <div class="no-trade-icon">⛔</div>
          <div class="no-trade-title">NO TRADE — All Criteria Failed</div>
          <div class="no-trade-why">""" + d.get("why", "Market conditions unfavorable across all criteria.") + """</div>
        </div>"""

    # Criteria passed count for header
    if is_trade:
        passed = sum(1 for v in d["stocks"][d["final_pick"]].values() if v == "✅ PASS" if isinstance(v, str))
        # Recalculate properly
        pass_count = 0
        for k, v in d["stocks"][d["final_pick"]].items():
            if k.endswith("_d") or k in ("close","chg","vol_lakhs","avg_vol_lakhs","ema20","ema50","status"):
                continue
            if v == "✅ PASS":
                pass_count += 1
    else:
        pass_count = 0

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>📊 Intraday Screener — {d['label']} ({d['day']})</title>
  <style>
    *, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0b0e14; color: #e8edf5; padding: 16px; min-height: 100vh;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}

    /* header */
    .header {{
      display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;
      margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #1f2937;
    }}
    .header h1 {{ font-size:22px; font-weight:700; }}
    .header h1 span {{ background:linear-gradient(135deg,#f59e0b,#ef4444); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
    .header .meta {{ color:#6b7a93; font-size:13px; display:flex; gap:12px; flex-wrap:wrap; }}
    .header .meta .tag {{ background:#1f2937; padding:4px 12px; border-radius:14px; font-size:12px; }}

    .card {{ background:#151a24; border-radius:12px; padding:18px; border:1px solid #1f2937; margin-bottom:14px; }}
    .card-title {{ font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:#6b7a93; margin-bottom:12px; display:flex; align-items:center; gap:8px; }}

    .stat-row {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .stat-chip {{ background:#1a212e; border-radius:8px; padding:8px 14px; display:flex; align-items:center; gap:8px; font-size:13px; border:1px solid #1f2937; }}
    .stat-chip .label {{ color:#6b7a93; }}
    .stat-chip .value {{ font-weight:600; }}
    .green {{ color:#22c55e; }} .red {{ color:#ef4444; }} .amber {{ color:#f59e0b; }} .blue {{ color:#60a5fa; }}

    /* Pick Box */
    .pick-box {{
      background:linear-gradient(135deg, rgba(245,158,11,0.1), rgba(239,68,68,0.05));
      border:1px solid rgba(245,158,11,0.3); border-radius:12px; padding:18px; margin-bottom:14px;
    }}
    .pick-title {{ font-size:18px; font-weight:700; text-align:center; margin-bottom:12px; color:#fbbf24; }}
    .pick-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:12px; }}
    .pick-item {{ background:#1a212e; padding:10px 14px; border-radius:8px; }}
    .pick-label {{ display:block; font-size:11px; color:#6b7a93; text-transform:uppercase; }}
    .pick-val {{ display:block; font-size:16px; font-weight:600; margin-top:2px; }}
    .pick-why {{ font-size:13px; color:#9ca3af; line-height:1.5; padding:10px 14px; background:rgba(0,0,0,0.2); border-radius:8px; }}

    /* No Trade */
    .no-trade-box {{ background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:12px; padding:24px; text-align:center; margin-bottom:14px; }}
    .no-trade-icon {{ font-size:40px; margin-bottom:8px; }}
    .no-trade-title {{ font-size:18px; font-weight:700; color:#ef4444; margin-bottom:8px; }}
    .no-trade-why {{ font-size:13px; color:#9ca3af; }}

    /* Stock cards */
    .stock-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:12px; }}
    .stock-card {{ background:#1a212e; border-radius:10px; padding:14px; border:1px solid #1f2937; }}
    .stock-header {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px; }}
    .stock-name {{ font-weight:700; font-size:15px; }}
    .stock-price {{ font-size:20px; font-weight:700; }}
    .stock-chg {{ font-size:14px; font-weight:600; }}
    .stock-vol {{ font-size:11px; color:#6b7a93; margin-left:auto; }}

    .criteria-row {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; }}
    .crit {{ display:flex; flex-wrap:wrap; align-items:center; gap:4px; padding:6px 8px; border-radius:6px; font-size:11px; }}
    .crit.pass {{ background:rgba(34,197,94,0.1); border-left:2px solid #22c55e; }}
    .crit.fail {{ background:rgba(239,68,68,0.08); border-left:2px solid #ef4444; opacity:0.7; }}
    .crit.neutral {{ background:rgba(245,158,11,0.08); border-left:2px solid #f59e0b; }}
    .crit-icon {{ font-size:11px; }}
    .crit-label {{ font-weight:600; color:#9ca3af; font-size:10px; text-transform:uppercase; }}
    .crit-status {{ font-size:10px; }}
    .crit-detail {{ width:100%; font-size:10px; color:#6b7a93; margin-top:2px; line-height:1.3; }}

    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th {{ text-align:left; padding:8px 10px; color:#6b7a93; font-weight:600; font-size:11px; text-transform:uppercase; border-bottom:1px solid #1f2937; }}
    td {{ padding:8px 10px; border-bottom:1px solid #1a212e; }}
    tr:hover td {{ background:#1a212e; }}

    ul {{ padding-left:18px; }}
    li {{ margin-bottom:4px; color:#9ca3af; font-size:13px; }}

    .footer {{ margin-top:24px; text-align:center; color:#4b5563; font-size:11px; padding:16px; border-top:1px solid #1f2937; }}

    @keyframes fadeIn {{ from{{opacity:0;transform:translateY(6px);}} to{{opacity:1;transform:translateY(0);}} }}
    .card {{ animation:fadeIn 0.35s ease-out; }}
  </style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <div class="header">
    <div>
      <h1>📊 <span>Intraday Screener</span></h1>
      <div class="meta">
        <span>{d['label']} · {d['day']}</span>
        <span class="tag">Run #{counter}</span>
        <span class="tag">{'✅ ACTIVE' if is_trade else '⛔ NO TRADE'}</span>
        {f'<span class="tag" style="color:#f59e0b;">🏆 {d["final_pick"]} · {pass_count}/8 criteria</span>' if is_trade else ''}
      </div>
    </div>
    <div style="font-size:12px;color:#6b7a93;">
      Nifty {d['nifty']:,.2f} <span class="{ 'green' if d['nifty_chg']>=0 else 'red' }">({d['nifty_chg']:+.2f}%)</span> · VIX {d['vix']:.2f}
    </div>
  </div>

  <!-- MARKET OVERVIEW -->
  <div class="card">
    <div class="card-title">🌍 Market Overview</div>
    <div class="stat-row">
      <div class="stat-chip"><span class="label">Nifty 50</span><span class="value">{d['nifty']:,.2f} <span class="{ 'green' if d['nifty_chg']>=0 else 'red' }">({d['nifty_chg']:+.2f}%)</span></span></div>
      <div class="stat-chip"><span class="label">Bank Nifty</span><span class="value">{d['bank_nifty']:,}</span></div>
      <div class="stat-chip"><span class="label">India VIX</span><span class="value">{d['vix']:.2f} ({d['vix_chg']:+.2f}%)</span></div>
      <div class="stat-chip"><span class="label">FII Net</span><span class="value red">{fii_display}</span></div>
      <div class="stat-chip"><span class="label">DII Net</span><span class="value green">{dii_display}</span></div>
      <div class="stat-chip"><span class="label">Support</span><span class="value blue">{d['nifty_support']}</span></div>
      <div class="stat-chip"><span class="label">Resistance</span><span class="value amber">{d['nifty_resistance']}</span></div>
    </div>
    <div style="margin-top:10px;color:#9ca3af;font-size:13px;">{d['market_breadth']}</div>
  </div>

  <!-- SECTOR -->
  <div class="card">
    <div class="card-title">🏭 Sector Performance</div>
    <div class="stat-row">{sector_html}</div>
  </div>

  <!-- NEWS -->
  <div class="card">
    <div class="card-title">📰 News Catalysts</div>
    <ul>{news_html}</ul>
  </div>

  <!-- PICK or NO TRADE -->
  {pick_box}
  {no_trade_box}

  <!-- 8-POINT SCREENER -->
  <div class="card">
    <div class="card-title">🔬 8-Point Screener — Stock Comparison</div>
    <div class="stock-row">{stocks_html}</div>
  </div>

  <!-- ALTERNATIVE WATCHLIST -->
  <div class="card">
    <div class="card-title">👀 Alternative Watchlist</div>
    <div class="table-wrap" style="overflow-x:auto;">
      <table>
        <thead><tr><th>Stock</th><th>Price</th><th>Why Watch</th></tr></thead>
        <tbody>{alt_html}</tbody>
      </table>
    </div>
  </div>

  <!-- NOTABLE MOVERS -->
  <div class="card">
    <div class="card-title">⚡ Notable Movers Today</div>
    <div class="table-wrap" style="overflow-x:auto;">
      <table>
        <thead><tr><th>Stock</th><th>Price</th><th>Change</th><th>Volume</th><th>Notes</th></tr></thead>
        <tbody>{movers_html}</tbody>
      </table>
    </div>
  </div>

  <!-- RISK MANAGEMENT -->
  <div class="card">
    <div class="card-title">⚠️ Risk Management Notes</div>
    <ul>{risk_html}</ul>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    Generated by Intraday Screener Agent · {d['label']} {d['day']} · Run #{counter} · Data: NSE, Investing.com, EquityPandit
  </div>

</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────
#  GENERATE ALL HTML FILES
# ─────────────────────────────────────────────────────────

def generate_all():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis")

    for day in DAYS:
        date_str = day["date"]
        folder = os.path.join(base_dir, date_str)
        os.makedirs(folder, exist_ok=True)

        # Find next available counter (handles both digit and word filenames)
        existing = [f for f in os.listdir(folder) if f.endswith(".html")]
        counter = 1
        nums = []
        for f in existing:
            stem = f[:-5]  # remove .html
            if stem.isdigit():
                nums.append(int(stem))
            elif stem in _WORD_TO_NUM:
                nums.append(_WORD_TO_NUM[stem])
        if nums:
            counter = max(nums) + 1

        html = generate_html(day, counter)
        word_name = _num_to_word(counter)
        filepath = os.path.join(folder, f"{word_name}.html")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✅  {date_str}/{word_name}.html  ({'🏆 ' + day['final_pick'] if day['final_pick'] else '⛔ No Trade'})")

    print(f"\n📁  All files written under: {base_dir}")
    print(f"📊  {len(DAYS)} trading days generated")


# ─────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────

def next_counter_for_date(date_str):
    """Auto-detect next counter by scanning existing files in the date folder."""
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis")
    folder = os.path.join(base_dir, date_str)
    os.makedirs(folder, exist_ok=True)
    existing = [f for f in os.listdir(folder) if f.endswith(".html")]
    nums = []
    for f in existing:
        stem = f[:-5]  # remove .html
        if stem.isdigit():
            nums.append(int(stem))
        elif stem in _WORD_TO_NUM:
            nums.append(_WORD_TO_NUM[stem])
    if nums:
        return max(nums) + 1
    return 1


def write_html(day, counter, date_str):
    """Generate and write the HTML file, returning the filepath."""
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis")
    folder = os.path.join(base_dir, date_str)
    os.makedirs(folder, exist_ok=True)
    html = generate_html(day, counter)
    word_name = _num_to_word(counter)
    filepath = os.path.join(folder, f"{word_name}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


if __name__ == "__main__":
    # Fix stdout encoding on Windows — emoji-safe
    import sys, io
    if sys.stdout.encoding and sys.stdout.encoding.upper() in ("CP1252", "ASCII"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Generate HTML picks")
    parser.add_argument("--date", help="Specific date YYYY-MM-DD")
    parser.add_argument("--counter", type=int, help="Run counter (auto-detects if omitted)")
    parser.add_argument("--stdin", action="store_true", help="Read day data as JSON from stdin (used by the /pick agent for live runs)")
    parser.add_argument("--validate", action="store_true", help="Validate JSON schema, then exit")
    args = parser.parse_args()

    if args.stdin:
        # Live data mode — read JSON day object from stdin
        import sys
        raw = sys.stdin.buffer.read().decode("utf-8")
        try:
            day = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"❌  Invalid JSON on stdin: {e}")
            sys.exit(1)

        date_str = args.date or day.get("date")
        if not date_str:
            print("❌  --date required when no 'date' field in JSON")
            sys.exit(1)

        if args.validate:
            # Basic schema validation
            required = ["date", "label", "day", "nifty", "nifty_chg", "vix", "stocks"]
            missing = [k for k in required if k not in day]
            if missing:
                print(f"❌  Missing required fields: {missing}")
                sys.exit(1)
            print(f"✅  JSON schema valid for {date_str}")
            sys.exit(0)

        counter = args.counter or next_counter_for_date(date_str)
        filepath = write_html(day, counter, date_str)
        word_name = _num_to_word(counter)
        print(f"✅  {date_str}/{word_name}.html generated")
        print(f"📁  {filepath}")

    elif args.date:
        # Look up from pre-baked DAYS data
        for day in DAYS:
            if day["date"] == args.date:
                counter = args.counter or next_counter_for_date(args.date)
                filepath = write_html(day, counter, args.date)
                word_name = _num_to_word(counter)
                print(f"✅  {args.date}/{word_name}.html generated")
                print(f"📁  {filepath}")
                break
        else:
            print(f"❌  Date {args.date} not found in pre-baked data (use --stdin for live data)")
    else:
        generate_all()
