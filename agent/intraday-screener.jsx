import { useState, useEffect } from "react";

const SCREENER_CRITERIA = `
You are an expert Indian stock market intraday trader and analyst. 

SCREENER CRITERIA (apply all of these):
1. MOMENTUM: Stock showing strong pre-market or early momentum (price above 20 EMA and 50 EMA)
2. VOLUME: Volume surge >150% of 10-day average volume (unusual activity = smart money)
3. VOLATILITY: ATR (Average True Range) should be >1.5% of price (enough movement for intraday profit)
4. SENTIMENT: Check news sentiment - positive catalyst preferred (earnings beat, sector tailwind, FII buying)
5. SUPPORT/RESISTANCE: Clear support level nearby (max 1-2% below entry) and resistance at least 3% above
6. RISK/REWARD: Minimum 1:3 risk-reward ratio
7. SECTOR STRENGTH: Stock should be in a sector showing strength that day
8. EMOTION TRACKER: Assess current market emotion (fear/greed/neutral) and how it affects this pick

OUTPUT FORMAT (strict JSON):
{
  "stock": "SYMBOL",
  "company": "Full Company Name",
  "exchange": "NSE",
  "sector": "Sector Name",
  "ltp": "approximate current price in ₹",
  "entry": "suggested entry price range",
  "target1": "first target price",
  "target2": "second target price",  
  "stopLoss": "stop loss price",
  "riskReward": "ratio like 1:3",
  "volumeSignal": "High/Very High/Extreme",
  "momentumScore": 0-100,
  "sentimentScore": 0-100,
  "marketEmotion": "Fear/Greed/Neutral/Euphoria/Panic",
  "emotionOpportunity": "how to use current emotion to your advantage",
  "catalyst": "what is driving this stock today",
  "technicalSetup": "describe the chart pattern",
  "keyRisk": "main risk to watch",
  "confidence": 0-100,
  "strategy": "Momentum/Breakout/Reversal/Gap-Up/Gap-Down",
  "safetyRating": "Safe/Moderate/Aggressive",
  "reasoning": "3-4 sentence detailed reasoning",
  "emotionAnalysis": {
    "fearGreedIndex": 0-100,
    "retailSentiment": "Bullish/Bearish/Neutral",
    "institutionalFlow": "Buying/Selling/Neutral",
    "contrarySignal": "what contrarian play exists here"
  }
}
`;

const MARKET_EMOTIONS = [
  { label: "Extreme Fear", range: [0, 20], color: "#ef4444", bg: "#fef2f2" },
  { label: "Fear", range: [21, 40], color: "#f97316", bg: "#fff7ed" },
  { label: "Neutral", range: [41, 60], color: "#eab308", bg: "#fefce8" },
  { label: "Greed", range: [61, 80], color: "#22c55e", bg: "#f0fdf4" },
  { label: "Extreme Greed", range: [81, 100], color: "#10b981", bg: "#ecfdf5" },
];

function getEmotionData(score) {
  return MARKET_EMOTIONS.find(e => score >= e.range[0] && score <= e.range[1]) || MARKET_EMOTIONS[2];
}

function ScoreBar({ value, color }) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 6, height: 8, overflow: "hidden" }}>
      <div style={{
        width: `${value}%`, height: "100%",
        background: `linear-gradient(90deg, ${color}88, ${color})`,
        borderRadius: 6, transition: "width 1s ease"
      }} />
    </div>
  );
}

function StatBox({ label, value, sub, color = "#60a5fa" }) {
  return (
    <div style={{
      background: "#0f172a", border: "1px solid #1e293b",
      borderRadius: 10, padding: "14px 16px", flex: 1, minWidth: 120
    }}>
      <div style={{ color: "#64748b", fontSize: 11, fontFamily: "monospace", letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
      <div style={{ color, fontSize: 20, fontWeight: 700, fontFamily: "monospace" }}>{value}</div>
      {sub && <div style={{ color: "#475569", fontSize: 11, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function EmotionGauge({ score }) {
  const emotion = getEmotionData(score);
  const angle = (score / 100) * 180 - 90;
  return (
    <div style={{ textAlign: "center" }}>
      <svg width="160" height="90" viewBox="0 0 160 90">
        <defs>
          <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="25%" stopColor="#f97316" />
            <stop offset="50%" stopColor="#eab308" />
            <stop offset="75%" stopColor="#22c55e" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>
        </defs>
        <path d="M 10 85 A 70 70 0 0 1 150 85" fill="none" stroke="#1e293b" strokeWidth="14" strokeLinecap="round"/>
        <path d="M 10 85 A 70 70 0 0 1 150 85" fill="none" stroke="url(#gaugeGrad)" strokeWidth="10" strokeLinecap="round"/>
        <line
          x1="80" y1="85"
          x2={80 + 55 * Math.cos((angle - 90) * Math.PI / 180)}
          y2={85 + 55 * Math.sin((angle - 90) * Math.PI / 180)}
          stroke="white" strokeWidth="2.5" strokeLinecap="round"
        />
        <circle cx="80" cy="85" r="5" fill="white"/>
        <text x="80" y="75" textAnchor="middle" fill={emotion.color} fontSize="13" fontWeight="bold" fontFamily="monospace">{score}</text>
      </svg>
      <div style={{ color: emotion.color, fontWeight: 700, fontSize: 14, marginTop: -8, fontFamily: "monospace" }}>{emotion.label}</div>
    </div>
  );
}

function StockCard({ data, onNew }) {
  const emotion = getEmotionData(data.emotionAnalysis?.fearGreedIndex || 50);
  const isGreen = data.strategy !== "Gap-Down" && data.strategy !== "Reversal";

  return (
    <div style={{
      background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
      border: "1px solid #334155", borderRadius: 16,
      padding: 24, color: "white", fontFamily: "'Inter', sans-serif"
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <span style={{
              background: isGreen ? "#052e16" : "#450a0a",
              color: isGreen ? "#4ade80" : "#f87171",
              fontFamily: "monospace", fontWeight: 800, fontSize: 22,
              padding: "4px 12px", borderRadius: 8, letterSpacing: 2
            }}>{data.stock}</span>
            <span style={{
              background: "#1e293b", color: "#94a3b8",
              fontSize: 11, padding: "3px 8px", borderRadius: 6, fontFamily: "monospace"
            }}>{data.exchange} · {data.sector}</span>
          </div>
          <div style={{ color: "#94a3b8", fontSize: 13 }}>{data.company}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ color: "#64748b", fontSize: 11, fontFamily: "monospace", marginBottom: 4 }}>STRATEGY</div>
          <span style={{
            background: "linear-gradient(135deg, #1d4ed8, #7c3aed)",
            color: "white", fontFamily: "monospace", fontSize: 12,
            padding: "5px 12px", borderRadius: 8, fontWeight: 700
          }}>{data.strategy}</span>
        </div>
      </div>

      {/* Price Levels */}
      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
        <StatBox label="Entry Zone" value={`₹${data.entry}`} color="#60a5fa" />
        <StatBox label="Target 1" value={`₹${data.target1}`} color="#4ade80" />
        <StatBox label="Target 2" value={`₹${data.target2}`} color="#34d399" />
        <StatBox label="Stop Loss" value={`₹${data.stopLoss}`} color="#f87171" sub={`R:R = ${data.riskReward}`} />
      </div>

      {/* Scores */}
      <div style={{ background: "#0f172a", borderRadius: 12, padding: 16, marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ fontFamily: "monospace", fontSize: 12, color: "#64748b", letterSpacing: 1 }}>SIGNAL STRENGTH</div>
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ background: data.safetyRating === "Safe" ? "#052e16" : data.safetyRating === "Moderate" ? "#422006" : "#450a0a", color: data.safetyRating === "Safe" ? "#4ade80" : data.safetyRating === "Moderate" ? "#fb923c" : "#f87171", fontSize: 11, padding: "2px 8px", borderRadius: 6, fontFamily: "monospace" }}>{data.safetyRating}</span>
            <span style={{ background: "#1e3a5f", color: "#60a5fa", fontSize: 11, padding: "2px 8px", borderRadius: 6, fontFamily: "monospace" }}>Vol: {data.volumeSignal}</span>
          </div>
        </div>
        <div style={{ marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ color: "#94a3b8", fontSize: 12 }}>Momentum</span>
            <span style={{ color: "#60a5fa", fontSize: 12, fontFamily: "monospace" }}>{data.momentumScore}/100</span>
          </div>
          <ScoreBar value={data.momentumScore} color="#60a5fa" />
        </div>
        <div style={{ marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ color: "#94a3b8", fontSize: 12 }}>Sentiment</span>
            <span style={{ color: "#a78bfa", fontSize: 12, fontFamily: "monospace" }}>{data.sentimentScore}/100</span>
          </div>
          <ScoreBar value={data.sentimentScore} color="#a78bfa" />
        </div>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ color: "#94a3b8", fontSize: 12 }}>Confidence</span>
            <span style={{ color: "#4ade80", fontSize: 12, fontFamily: "monospace" }}>{data.confidence}/100</span>
          </div>
          <ScoreBar value={data.confidence} color="#4ade80" />
        </div>
      </div>

      {/* Emotion Analysis */}
      <div style={{ background: "#0f172a", borderRadius: 12, padding: 16, marginBottom: 16 }}>
        <div style={{ fontFamily: "monospace", fontSize: 12, color: "#64748b", letterSpacing: 1, marginBottom: 12 }}>MARKET EMOTION TRACKER</div>
        <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
          <EmotionGauge score={data.emotionAnalysis?.fearGreedIndex || 50} />
          <div style={{ flex: 1, minWidth: 180 }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
              <span style={{ background: "#1e293b", padding: "4px 10px", borderRadius: 6, fontSize: 11, fontFamily: "monospace" }}>
                Retail: <span style={{ color: data.emotionAnalysis?.retailSentiment === "Bullish" ? "#4ade80" : data.emotionAnalysis?.retailSentiment === "Bearish" ? "#f87171" : "#eab308" }}>{data.emotionAnalysis?.retailSentiment}</span>
              </span>
              <span style={{ background: "#1e293b", padding: "4px 10px", borderRadius: 6, fontSize: 11, fontFamily: "monospace" }}>
                FII/DII: <span style={{ color: data.emotionAnalysis?.institutionalFlow === "Buying" ? "#4ade80" : data.emotionAnalysis?.institutionalFlow === "Selling" ? "#f87171" : "#eab308" }}>{data.emotionAnalysis?.institutionalFlow}</span>
              </span>
            </div>
            <div style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.6 }}>
              <span style={{ color: "#f59e0b" }}>⚡ Contrarian Play:</span> {data.emotionAnalysis?.contrarySignal}
            </div>
          </div>
        </div>
        <div style={{ marginTop: 12, background: "#1e293b", borderRadius: 8, padding: 10 }}>
          <span style={{ color: "#7c3aed", fontSize: 11, fontFamily: "monospace" }}>EMOTION EDGE → </span>
          <span style={{ color: "#c4b5fd", fontSize: 12 }}>{data.emotionOpportunity}</span>
        </div>
      </div>

      {/* Catalyst & Setup */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
        <div style={{ background: "#0f172a", borderRadius: 10, padding: 12 }}>
          <div style={{ color: "#64748b", fontSize: 11, fontFamily: "monospace", letterSpacing: 1, marginBottom: 6 }}>CATALYST</div>
          <div style={{ color: "#e2e8f0", fontSize: 12, lineHeight: 1.5 }}>{data.catalyst}</div>
        </div>
        <div style={{ background: "#0f172a", borderRadius: 10, padding: 12 }}>
          <div style={{ color: "#64748b", fontSize: 11, fontFamily: "monospace", letterSpacing: 1, marginBottom: 6 }}>CHART SETUP</div>
          <div style={{ color: "#e2e8f0", fontSize: 12, lineHeight: 1.5 }}>{data.technicalSetup}</div>
        </div>
      </div>

      {/* Reasoning */}
      <div style={{ background: "#0f172a", borderRadius: 10, padding: 14, marginBottom: 16, borderLeft: "3px solid #3b82f6" }}>
        <div style={{ color: "#64748b", fontSize: 11, fontFamily: "monospace", letterSpacing: 1, marginBottom: 6 }}>AI REASONING</div>
        <div style={{ color: "#cbd5e1", fontSize: 13, lineHeight: 1.7 }}>{data.reasoning}</div>
      </div>

      {/* Risk */}
      <div style={{ background: "#450a0a22", border: "1px solid #7f1d1d55", borderRadius: 10, padding: 12, marginBottom: 20 }}>
        <span style={{ color: "#f87171", fontSize: 11, fontFamily: "monospace" }}>⚠ KEY RISK: </span>
        <span style={{ color: "#fca5a5", fontSize: 12 }}>{data.keyRisk}</span>
      </div>

      {/* Disclaimer */}
      <div style={{ color: "#475569", fontSize: 11, textAlign: "center", lineHeight: 1.6, borderTop: "1px solid #1e293b", paddingTop: 14 }}>
        ⚠️ This is AI-generated research for educational purposes only. Not SEBI registered advice.<br/>
        Always apply your own judgement. Never risk more than 1-2% of capital per trade.
      </div>

      <button
        onClick={onNew}
        style={{
          width: "100%", marginTop: 16,
          background: "linear-gradient(135deg, #1d4ed8, #7c3aed)",
          color: "white", border: "none", borderRadius: 10,
          padding: "14px", fontSize: 14, fontWeight: 700,
          cursor: "pointer", fontFamily: "monospace", letterSpacing: 1
        }}
      >
        🔄 RESEARCH NEXT STOCK →
      </button>
    </div>
  );
}

export default function IntradayScreener() {
  const [loading, setLoading] = useState(false);
  const [stockData, setStockData] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [date] = useState(new Date().toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" }));

  async function fetchStock() {
    setLoading(true);
    setError(null);
    setStockData(null);

    const avoidList = history.map(h => h.stock).join(", ");
    const prompt = `${SCREENER_CRITERIA}

Today is ${date}. Indian market is open.
${avoidList ? `Stocks already researched today (avoid these): ${avoidList}` : ""}

Based on current Indian market conditions (NSE/BSE), apply the screener and pick ONE high-probability intraday stock for today.
Consider current macro trends: RBI policy, FII/DII flows, global cues, sector rotation.
Be specific with real NSE-listed stocks. Output ONLY valid JSON, no markdown, no explanation outside JSON.`;

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": import.meta.env.VITE_ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: "claude-sonnet-4-6",
          max_tokens: 1000,
          tools: [{ type: "web_search_20250305", name: "web_search" }],
          messages: [{ role: "user", content: prompt }]
        })
      });

      const data = await response.json();
      const fullText = data.content
        .filter(b => b.type === "text")
        .map(b => b.text)
        .join("\n");

      const jsonMatch = fullText.match(/\{[\s\S]*\}/);
      if (!jsonMatch) throw new Error("No valid JSON in response");

      const parsed = JSON.parse(jsonMatch[0]);
      setStockData(parsed);
      setHistory(prev => [...prev, { stock: parsed.stock, strategy: parsed.strategy, confidence: parsed.confidence }]);
    } catch (err) {
      setError("Failed to fetch research. Please try again. " + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(160deg, #020617 0%, #0f172a 50%, #1e1b4b 100%)",
      padding: "24px 16px", fontFamily: "'Inter', sans-serif"
    }}>
      <div style={{ maxWidth: 640, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            background: "#0f172a", border: "1px solid #334155",
            borderRadius: 50, padding: "6px 16px", marginBottom: 16
          }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4ade80", boxShadow: "0 0 8px #4ade80", animation: "pulse 2s infinite" }} />
            <span style={{ color: "#64748b", fontSize: 11, fontFamily: "monospace", letterSpacing: 1 }}>NSE · BSE LIVE SCREENER</span>
          </div>
          <h1 style={{
            color: "white", fontSize: 28, fontWeight: 900, margin: "0 0 6px",
            background: "linear-gradient(135deg, #fff, #94a3b8)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"
          }}>INTRADAY EDGE</h1>
          <p style={{ color: "#475569", fontSize: 13, margin: 0, fontFamily: "monospace" }}>
            AI Screener · Emotion Tracker · Daily Research
          </p>
          <p style={{ color: "#334155", fontSize: 11, marginTop: 6, fontFamily: "monospace" }}>{date}</p>
        </div>

        {/* Today's History */}
        {history.length > 0 && (
          <div style={{
            background: "#0f172a", border: "1px solid #1e293b",
            borderRadius: 12, padding: 14, marginBottom: 16
          }}>
            <div style={{ color: "#64748b", fontSize: 11, fontFamily: "monospace", letterSpacing: 1, marginBottom: 10 }}>TODAY'S RESEARCHED STOCKS</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {history.map((h, i) => (
                <span key={i} style={{
                  background: "#1e293b", color: "#94a3b8",
                  fontSize: 11, padding: "4px 10px", borderRadius: 6, fontFamily: "monospace"
                }}>
                  {h.stock} <span style={{ color: "#4ade80" }}>{h.confidence}%</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Main Content */}
        {!stockData && !loading && (
          <div style={{
            background: "#0f172a", border: "1px dashed #334155",
            borderRadius: 16, padding: 40, textAlign: "center"
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📊</div>
            <div style={{ color: "#94a3b8", fontSize: 16, marginBottom: 8 }}>Ready to research today's intraday pick</div>
            <div style={{ color: "#475569", fontSize: 13, marginBottom: 24, lineHeight: 1.6 }}>
              AI applies 8-point screener: momentum, volume surge,<br/>
              sentiment, support/resistance, emotion analysis & more
            </div>
            <button
              onClick={fetchStock}
              style={{
                background: "linear-gradient(135deg, #1d4ed8, #7c3aed)",
                color: "white", border: "none", borderRadius: 12,
                padding: "16px 40px", fontSize: 15, fontWeight: 700,
                cursor: "pointer", fontFamily: "monospace", letterSpacing: 1
              }}
            >
              🔍 SCREEN & RESEARCH →
            </button>
          </div>
        )}

        {loading && (
          <div style={{
            background: "#0f172a", border: "1px solid #334155",
            borderRadius: 16, padding: 50, textAlign: "center"
          }}>
            <div style={{ marginBottom: 20 }}>
              {["Scanning NSE momentum...", "Checking volume signals...", "Reading market emotions...", "Analyzing risk/reward...", "Finalizing research..."].map((step, i) => (
                <div key={i} style={{
                  color: i === 2 ? "#60a5fa" : "#334155",
                  fontSize: 12, fontFamily: "monospace",
                  marginBottom: 8, transition: "color 0.5s"
                }}>{'>'} {step}</div>
              ))}
            </div>
            <div style={{ color: "#475569", fontSize: 12, fontFamily: "monospace" }}>AI researching live market conditions...</div>
          </div>
        )}

        {error && (
          <div style={{
            background: "#450a0a", border: "1px solid #7f1d1d",
            borderRadius: 12, padding: 20, textAlign: "center", marginBottom: 16
          }}>
            <div style={{ color: "#f87171", fontSize: 13 }}>{error}</div>
            <button onClick={fetchStock} style={{
              marginTop: 12, background: "#7f1d1d", color: "#fca5a5",
              border: "none", borderRadius: 8, padding: "8px 20px",
              cursor: "pointer", fontSize: 12, fontFamily: "monospace"
            }}>RETRY</button>
          </div>
        )}

        {stockData && <StockCard data={stockData} onNew={fetchStock} />}

        <style>{`
          @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        `}</style>
      </div>
    </div>
  );
}
