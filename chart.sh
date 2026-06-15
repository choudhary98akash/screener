#!/usr/bin/env bash
# Chart — Gap Mean Reversion Scanner + Dashboard
# Usage: bash chart.sh  (or ./chart.sh)
# Note: Run from the Agentic project directory, or this script auto-detects.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

echo "📊 Running Gap Mean Reversion Scan..."
python agent/daily_screener.py gap

echo ""
echo "📈 Generating Dashboard..."
python agent/daily_screener.py dashboard

echo ""
echo "✅ Done"
echo "   index.html → $DIR/index.html"
echo "   Run: start $DIR/index.html"
