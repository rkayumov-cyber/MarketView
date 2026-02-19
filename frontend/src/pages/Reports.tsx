import { useState, useEffect } from "react";
import {
  generateReport,
  listReports,
  getDownloadUrl,
  deleteReport,
  getLLMProviders,
  type ReportRequest,
  type LLMProvider,
} from "../api/client";
import StatusBadge from "../components/StatusBadge";

interface ReportSummary {
  report_id: string;
  title: string;
  level: number;
  created_at: string;
  format: string;
}

const levelLabels: Record<number, string> = {
  1: "Executive",
  2: "Standard",
  3: "Deep Dive",
};

function generateMockReport(level: 1 | 2 | 3): string {
  const timestamp = new Date().toLocaleString();
  const base = `# MarketView ${levelLabels[level]} Report
> Generated ${timestamp} (offline mock)

## Market Pulse
**Regime:** Risk-On — Moderate confidence (72%)
- Equities trending higher on strong earnings
- VIX subdued below 17, signaling low implied vol
- Credit spreads remain tight

## Key Metrics
| Asset       | Price      | Change  |
|-------------|-----------|---------|
| S&P 500     | 5,924.02  | +0.24%  |
| NASDAQ      | 19,223.84 | +0.56%  |
| VIX         | 16.32     | -3.18%  |
| 10Y UST     | 4.28%     | +2 bps  |
| Bitcoin     | $97,432   | +1.87%  |
| Gold        | $2,918    | +0.42%  |
| DXY         | 106.82    | -0.15%  |

## Macro Overview
- **Inflation:** CPI at 2.8% YoY, trending toward target
- **Growth:** GDP tracking 2.3% annualized
- **Labor:** Unemployment steady at 3.9%, initial claims benign
- **Policy:** Fed Funds at 5.33%, market pricing 2 cuts in 2025`;

  if (level === 1) return base + "\n\n---\n*End of Executive Summary*";

  const sentiment = `

## Sentiment Analysis
**Overall: Bullish** (score: +0.28, bullish ratio: 63%)
*842 posts analyzed across 6 subreddits (reddit)*

Retail sentiment across financial Reddit is **bullish** with an overall score of +0.28
and 63% of posts leaning bullish. Most-discussed tickers: $NVDA, $TSLA, $AAPL, $SPY, $BTC.
r/wallstreetbets is the most bullish community (+0.41). r/investing tilts most bearish (-0.08).

### Trending Tickers
| Ticker | Mentions |
|--------|----------|
| $NVDA | 127 |
| $TSLA | 98 |
| $AAPL | 76 |
| $SPY | 61 |
| $BTC | 55 |

### Subreddit Breakdown
| Subreddit | Score | Bullish | Posts | Top Ticker |
|-----------|-------|---------|-------|------------|
| r/wallstreetbets | +0.41 | 71% | 312 | $NVDA |
| r/stocks | +0.22 | 58% | 187 | $AAPL |
| r/cryptocurrency | +0.35 | 67% | 143 | $BTC |
| r/investing | -0.08 | 42% | 118 | $SPY |
| r/options | +0.18 | 55% | 82 | $TSLA |`;

  const standard = `

## Asset Class Breakdown

### Equities
US large caps leading with tech outperformance. Breadth improving as small caps
recover from January drawdown. Global indices mixed — Europe strong on ECB pause,
Asia-Pacific lagging on China property concerns.

### Fixed Income
Yield curve remains inverted at -105bps (2s10s). Long end selling off on supply
concerns. Credit: HY spreads at 321bps (tight), IG at 89bps. No stress signals.

### FX
Dollar index (DXY) consolidating near 107. EUR/USD testing 1.04 support.
USD/JPY volatile around 152 on BoJ intervention fears.

### Commodities
Gold pushing all-time highs on central bank buying. Crude rangebound $68-$74
on balanced OPEC+ supply. Copper firming on green transition demand.

### Crypto
Bitcoin holding above $95K, ETF inflows steady. Ethereum lagging at $2,700.
Crypto fear/greed index: 68 (Greed).`;

  if (level === 2) return base + sentiment + standard + "\n\n---\n*End of Standard Report*";

  const deep = `

## Technical Levels
| Asset   | Support 1 | Support 2 | Resistance 1 | Resistance 2 | RSI  | Signal |
|---------|-----------|-----------|--------------|--------------|------|--------|
| SPX     | 5,850     | 5,780     | 5,960        | 6,020        | 58.4 | Neutral|
| NASDAQ  | 18,900    | 18,500    | 19,400       | 19,800       | 62.1 | Bullish|
| 10Y UST | 4.20%     | 4.10%     | 4.35%        | 4.45%        | 51.2 | Neutral|
| Gold    | $2,880    | $2,840    | $2,950       | $3,000       | 67.8 | Bullish|
| BTC     | $93,000   | $88,500   | $100,000     | $105,000     | 55.3 | Neutral|

## Volatility Assessment
- VIX at 16.32 — 28th percentile (below avg)
- MOVE Index: 98.4 — rates vol subdued
- Skew: moderately elevated, put protection bid intact

## Correlation Matrix Highlights
- SPX / BTC: +0.42 (moderate, rising)
- Gold / DXY: -0.78 (strong inverse, as expected)
- 10Y / SPX: -0.31 (weak inverse, decoupling)
- VIX / Credit HY: +0.65 (risk-off correlation intact)

## Forward Look
### Key Events (Next 7 Days)
- **Wed:** FOMC Minutes release
- **Thu:** Initial jobless claims, existing home sales
- **Fri:** Flash PMIs (US, EU, Japan)

### Outlier Scenario
**Event:** Surprise BoJ rate hike to 0.50%
**Probability:** Low (15%)
**Impact:** JPY surge, carry trade unwind, equity vol spike
**Hedge:** Long JPY calls, short Nikkei futures`;

  return base + sentiment + standard + deep + "\n\n---\n*End of Deep Dive Report*";
}


export default function Reports() {
  const [level, setLevel] = useState<1 | 2 | 3>(1);
  const [format, setFormat] = useState<ReportRequest["format"]>("markdown");
  const [includeTechnicals, setIncludeTechnicals] = useState(false);
  const [includeSentiment, setIncludeSentiment] = useState(false);
  const [includeCorrelations, setIncludeCorrelations] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loadingReports, setLoadingReports] = useState(true);
  const [llmProviders, setLlmProviders] = useState<LLMProvider[]>([]);
  const [selectedLLMProvider, setSelectedLLMProvider] = useState<string | null>(null);
  const [selectedLLMModel, setSelectedLLMModel] = useState<string | null>(null);

  useEffect(() => {
    loadReports();
    loadLLMProviders();
  }, []);

  async function loadReports() {
    try {
      const data = await listReports(20);
      setReports(data.reports ?? []);
    } catch {
      // API unavailable — show empty state
    } finally {
      setLoadingReports(false);
    }
  }

  async function loadLLMProviders() {
    try {
      const data = await getLLMProviders();
      setLlmProviders(data.providers ?? []);
    } catch {
      // API unavailable
    }
  }

  function selectProvider(providerId: string | null) {
    if (providerId === selectedLLMProvider) {
      setSelectedLLMProvider(null);
      setSelectedLLMModel(null);
      return;
    }
    setSelectedLLMProvider(providerId);
    const provider = llmProviders.find((p) => p.id === providerId);
    setSelectedLLMModel(provider?.default_model ?? null);
  }

  async function handleGenerate() {
    setGenerating(true);
    setOffline(false);
    setGeneratedContent(null);
    try {
      const result = await generateReport({
        level,
        format,
        include_technicals: includeTechnicals,
        include_sentiment: includeSentiment,
        include_correlations: includeCorrelations,
        llm_provider: selectedLLMProvider ?? undefined,
        llm_model: selectedLLMModel ?? undefined,
      });
      setGeneratedContent(result.content ?? "Report generated successfully.");
      loadReports();
    } catch {
      // API unavailable — generate a local mock report
      setGeneratedContent(generateMockReport(level));
      setOffline(true);
    } finally {
      setGenerating(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteReport(id);
      setReports((prev) => prev.filter((r) => r.report_id !== id));
    } catch {
      // silent fail
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Reports</h1>
        <p className="text-xs text-terminal-muted mt-1">
          Generate and manage market analysis reports
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Generator panel */}
        <div className="lg:col-span-1 card space-y-4">
          <h2 className="text-sm font-semibold border-b border-terminal-border pb-2">
            Generate Report
          </h2>

          {/* Level */}
          <div>
            <label className="text-xs text-terminal-muted uppercase tracking-wider block mb-2">
              Detail Level
            </label>
            <div className="flex gap-2">
              {([1, 2, 3] as const).map((l) => (
                <button
                  key={l}
                  onClick={() => setLevel(l)}
                  className={`flex-1 py-2 text-xs rounded-md border transition-colors ${
                    level === l
                      ? "border-terminal-accent bg-terminal-accent/10 text-terminal-accent"
                      : "border-terminal-border text-terminal-muted hover:text-gray-300"
                  }`}
                >
                  L{l}
                  <span className="block text-[10px] mt-0.5">
                    {levelLabels[l]}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Format */}
          <div>
            <label className="text-xs text-terminal-muted uppercase tracking-wider block mb-2">
              Format
            </label>
            <select
              value={format}
              onChange={(e) =>
                setFormat(e.target.value as ReportRequest["format"])
              }
              className="w-full bg-terminal-bg border border-terminal-border rounded-md px-3 py-2 text-sm text-gray-300 focus:border-terminal-accent focus:outline-none"
            >
              <option value="markdown">Markdown</option>
              <option value="json">JSON</option>
              <option value="html">HTML</option>
              <option value="pdf">PDF</option>
            </select>
          </div>

          {/* Toggles (show for L2+) */}
          {level >= 2 && (
            <div className="space-y-2">
              <label className="text-xs text-terminal-muted uppercase tracking-wider block">
                Include
              </label>
              {[
                {
                  label: "Technicals",
                  checked: includeTechnicals,
                  set: setIncludeTechnicals,
                },
                {
                  label: "Sentiment",
                  checked: includeSentiment,
                  set: setIncludeSentiment,
                },
                {
                  label: "Correlations",
                  checked: includeCorrelations,
                  set: setIncludeCorrelations,
                },
              ].map(({ label, checked, set }) => (
                <label
                  key={label}
                  className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => set(e.target.checked)}
                    className="accent-terminal-accent"
                  />
                  {label}
                </label>
              ))}
            </div>
          )}

          {/* AI Enhancement */}
          <div>
            <label className="text-xs text-terminal-muted uppercase tracking-wider block mb-2">
              AI Enhancement
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => selectProvider(null)}
                className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                  selectedLLMProvider === null
                    ? "border-terminal-accent bg-terminal-accent/10 text-terminal-accent"
                    : "border-terminal-border text-terminal-muted hover:text-gray-300"
                }`}
              >
                Rule-based
              </button>
              {llmProviders.map((p) => (
                <button
                  key={p.id}
                  onClick={() => p.available && selectProvider(p.id)}
                  disabled={!p.available}
                  title={
                    p.available
                      ? p.label
                      : `${p.label} — ${p.needs_key ? "API key not configured" : "not running"}`
                  }
                  className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                    selectedLLMProvider === p.id
                      ? "border-terminal-accent bg-terminal-accent/10 text-terminal-accent"
                      : p.available
                        ? "border-terminal-border text-terminal-muted hover:text-gray-300"
                        : "border-terminal-border/50 text-terminal-muted/40 cursor-not-allowed"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
            {selectedLLMProvider && (
              <select
                value={selectedLLMModel ?? ""}
                onChange={(e) => setSelectedLLMModel(e.target.value)}
                className="w-full mt-2 bg-terminal-bg border border-terminal-border rounded-md px-3 py-2 text-sm text-gray-300 focus:border-terminal-accent focus:outline-none"
              >
                {llmProviders
                  .find((p) => p.id === selectedLLMProvider)
                  ?.models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
              </select>
            )}
          </div>

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating
              ? selectedLLMProvider
                ? "Enhancing with AI..."
                : "Generating..."
              : selectedLLMProvider
                ? `Generate + ${llmProviders.find((p) => p.id === selectedLLMProvider)?.label ?? "AI"}`
                : "Generate Report"}
          </button>

          {offline && (
            <div className="text-xs text-terminal-amber bg-terminal-amber/10 border border-terminal-amber/20 rounded-md p-3">
              API offline — showing mock report with sample data
            </div>
          )}
        </div>

        {/* Output / report content */}
        <div className="lg:col-span-2 space-y-4">
          {generatedContent && (
            <div className="card">
              <h2 className="text-sm font-semibold mb-3">Generated Report</h2>
              <pre className="text-xs text-gray-300 whitespace-pre-wrap max-h-[60vh] overflow-y-auto leading-relaxed">
                {generatedContent}
              </pre>
            </div>
          )}

          {/* Past reports */}
          <div className="card">
            <h2 className="text-sm font-semibold mb-3">Past Reports</h2>
            {loadingReports ? (
              <p className="text-xs text-terminal-muted">Loading...</p>
            ) : reports.length === 0 ? (
              <p className="text-xs text-terminal-muted">
                No reports yet. Generate one to get started.
              </p>
            ) : (
              <div className="space-y-2">
                {reports.map((r) => (
                  <div
                    key={r.report_id}
                    className="flex items-center justify-between py-2 border-b border-terminal-border/50 last:border-0"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        {r.title || r.report_id}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <StatusBadge status={levelLabels[r.level] ?? "L1"} />
                        <span className="text-[10px] text-terminal-muted uppercase">
                          {r.format}
                        </span>
                        <span className="text-[10px] text-terminal-muted">
                          {new Date(r.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-3">
                      <a
                        href={getDownloadUrl(r.report_id, r.format)}
                        className="text-xs text-terminal-accent hover:underline"
                      >
                        Download
                      </a>
                      <button
                        onClick={() => handleDelete(r.report_id)}
                        className="text-xs text-terminal-red hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
