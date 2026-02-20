import { useState, useCallback } from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import ChartCard from "../components/ChartCard";
import {
  getFredRates,
  getFredCredit,
  getFredYieldCurve,
  getEquities,
  getFx,
  getCommodities,
  getCrypto,
} from "../api/client";
import { useDataSource } from "../context/DataSourceContext";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import RefreshBar from "../components/RefreshBar";

type Tab = "equities" | "fixed-income" | "fx" | "commodities" | "crypto";

const tabs: { id: Tab; label: string }[] = [
  { id: "equities", label: "Equities" },
  { id: "fixed-income", label: "Fixed Income" },
  { id: "fx", label: "FX" },
  { id: "commodities", label: "Commodities" },
  { id: "crypto", label: "Crypto" },
];

// ── Helper ──────────────────────────────────────────────

function DataTable({
  rows,
  loading,
}: {
  rows: { name: string; value: string; change: number }[];
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 text-terminal-muted text-sm">
        <span className="animate-pulse">Loading...</span>
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-terminal-muted text-xs uppercase tracking-wider border-b border-terminal-border">
            <th className="text-left py-2 pr-4">Name</th>
            <th className="text-right py-2 pr-4">Price</th>
            <th className="text-right py-2">Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.name}
              className="border-b border-terminal-border/50 hover:bg-white/[0.02]"
            >
              <td className="py-2 pr-4 font-medium">{r.name}</td>
              <td className="py-2 pr-4 text-right tabular-nums">{r.value}</td>
              <td
                className={`py-2 text-right tabular-nums ${r.change >= 0 ? "text-terminal-green" : "text-terminal-red"}`}
              >
                {r.change >= 0 ? "+" : ""}
                {r.change.toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SourceBadge({ source }: { source: string }) {
  if (!source) return null;
  return (
    <span
      className={`text-[10px] px-2 py-0.5 rounded ml-2 ${
        source === "live"
          ? "bg-emerald-500/20 text-emerald-400"
          : source.includes("fallback")
            ? "bg-orange-500/20 text-orange-400"
            : "bg-amber-500/20 text-amber-400"
      }`}
    >
      {source}
    </span>
  );
}

const tooltipStyle = {
  background: "#111827",
  border: "1px solid #1e293b",
  borderRadius: 6,
  fontSize: 12,
};

function fmt(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: n >= 100 ? 0 : 2,
    maximumFractionDigits: n >= 100 ? 0 : 4,
  });
}

// ── Equity helpers ──────────────────────────────────────

function equityRow(key: string, d: any): { name: string; value: string; change: number } {
  return {
    name: d.name ?? key,
    value: fmt(d.current_price),
    change: d.change_percent,
  };
}

// ── Tab content components ──────────────────────────────

function EquitiesTab() {
  const { source } = useDataSource();
  const [data, setData] = useState<any>(null);
  const [src, setSrc] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchEquities = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getEquities(source);
      setData(res.data);
      setSrc(res.source);
    } catch {
      // keep existing data
    } finally {
      setLoading(false);
    }
  }, [source]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(fetchEquities, { deps: [source] });

  const usRows = data?.us
    ? Object.entries(data.us).map(([k, v]: [string, any]) => equityRow(k, v))
    : [];
  const globalRows = data?.global
    ? Object.entries(data.global).map(([k, v]: [string, any]) => equityRow(k, v))
    : [];

  // Build chart data from US indices
  const history = data?.us
    ? Array.from({ length: 30 }, (_, i) => {
        const spxBase = data.us.spx?.current_price ?? 5900;
        const nqBase = data.us.nasdaq?.current_price ?? 19200;
        return {
          day: i + 1,
          spx: spxBase - 120 + Math.random() * 240,
          nasdaq: nqBase - 400 + Math.random() * 800,
        };
      })
    : [];

  return (
    <div className="space-y-4">
      <RefreshBar lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={refresh} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-semibold mb-3">
            US Indices
            <SourceBadge source={src} />
          </h3>
          <DataTable rows={usRows} loading={loading} />
        </div>
        <div className="card">
          <h3 className="text-sm font-semibold mb-3">Global Indices</h3>
          <DataTable rows={globalRows} loading={loading} />
        </div>
      </div>
      {!loading && history.length > 0 && (
        <ChartCard
          title="S&P 500 vs NASDAQ"
          subtitle="30-day trend (simulated from current level)"
        >
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={history}>
              <XAxis
                dataKey="day"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#1e293b" }}
                tickLine={false}
              />
              <YAxis
                yAxisId="spx"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={58}
                tickFormatter={(v: number) => v.toLocaleString()}
              />
              <YAxis
                yAxisId="nq"
                orientation="right"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={58}
                tickFormatter={(v: number) => v.toLocaleString()}
              />
              <Tooltip contentStyle={tooltipStyle} />
              <Line
                yAxisId="spx"
                type="monotone"
                dataKey="spx"
                stroke="#3b82f6"
                dot={false}
                strokeWidth={2}
                name="S&P 500"
              />
              <Line
                yAxisId="nq"
                type="monotone"
                dataKey="nasdaq"
                stroke="#a855f7"
                dot={false}
                strokeWidth={2}
                name="NASDAQ"
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      )}
    </div>
  );
}

function FixedIncomeTab() {
  const [ratesData, setRatesData] = useState<Record<string, any> | null>(null);
  const [yieldCurve, setYieldCurve] = useState([
    { maturity: "FF", yield: 5.33 },
    { maturity: "2Y", yield: 4.26 },
    { maturity: "10Y", yield: 4.28 },
    { maturity: "30Y", yield: 4.51 },
  ]);
  const [creditData, setCreditData] = useState<Record<string, any> | null>(
    null,
  );

  const fetchFixedIncome = useCallback(async () => {
    const [rates, yc, credit] = await Promise.all([
      getFredRates().catch(() => null),
      getFredYieldCurve().catch(() => null),
      getFredCredit().catch(() => null),
    ]);
    if (rates?.data) setRatesData(rates.data);
    if (yc?.data) {
      const curve = [
        { maturity: "FF", yield: yc.data.fed_funds },
        { maturity: "2Y", yield: yc.data.treasury_2y },
        { maturity: "10Y", yield: yc.data.treasury_10y },
        { maturity: "30Y", yield: yc.data.treasury_30y },
      ].filter((p) => p.yield != null);
      if (curve.length > 0) setYieldCurve(curve);
    }
    if (credit?.data) setCreditData(credit.data);
  }, []);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(fetchFixedIncome);

  const ratesRows = ratesData
    ? Object.entries(ratesData).map(([key, val]: [string, any]) => ({
        name: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        value:
          val?.latest_value != null ? `${val.latest_value.toFixed(2)}%` : "N/A",
        change: val?.pct_change ?? 0,
      }))
    : [
        { name: "Fed Funds", value: "5.33%", change: 0 },
        { name: "2Y Treasury", value: "4.26%", change: -0.47 },
        { name: "10Y Treasury", value: "4.28%", change: 0.02 },
        { name: "30Y Treasury", value: "4.51%", change: 0.05 },
      ];

  const creditRows = creditData
    ? Object.entries(creditData).map(([key, val]: [string, any]) => ({
        name: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        value:
          val?.latest_value != null
            ? `${val.latest_value.toFixed(0)} bps`
            : "N/A",
        change: val?.pct_change ?? 0,
      }))
    : [
        { name: "HY Spread", value: "321 bps", change: -1.2 },
        { name: "IG Spread", value: "89 bps", change: -0.5 },
      ];

  return (
    <div className="space-y-4">
      <RefreshBar lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={refresh} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-semibold mb-3">Key Rates</h3>
          <DataTable rows={ratesRows} />
        </div>
        <div className="card">
          <h3 className="text-sm font-semibold mb-3">Credit Spreads</h3>
          <DataTable rows={creditRows} />
        </div>
      </div>
      <ChartCard title="Yield Curve" subtitle="Current snapshot">
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={yieldCurve}>
            <defs>
              <linearGradient id="ycGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="maturity"
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={{ stroke: "#1e293b" }}
              tickLine={false}
            />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `${v.toFixed(1)}%`}
              width={48}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v: number) => [`${v.toFixed(2)}%`, "Yield"]}
            />
            <Area
              type="monotone"
              dataKey="yield"
              stroke="#3b82f6"
              fill="url(#ycGrad)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

function FXTab() {
  const { source } = useDataSource();
  const [data, setData] = useState<any>(null);
  const [src, setSrc] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchFx = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getFx(source);
      setData(res.data);
      setSrc(res.source);
    } catch {
      // keep existing data
    } finally {
      setLoading(false);
    }
  }, [source]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(fetchFx, { deps: [source] });

  const rows: { name: string; value: string; change: number }[] = [];

  if (data) {
    // DXY first
    if (data.dxy) {
      rows.push({
        name: "DXY",
        value: (data.dxy.value ?? 0).toFixed(2),
        change: data.dxy.change_percent,
      });
    }
    // All pairs
    if (data.pairs) {
      for (const [key, v] of Object.entries(data.pairs) as [string, any][]) {
        rows.push({
          name: v.pair ?? key.toUpperCase(),
          value: v.rate?.toFixed(4) ?? "—",
          change: v.change_percent,
        });
      }
    }
  }

  return (
    <div className="space-y-4">
      <RefreshBar lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={refresh} />
      <div className="card">
        <h3 className="text-sm font-semibold mb-3">
          Currency Pairs
          <SourceBadge source={src} />
        </h3>
        <DataTable rows={rows} loading={loading} />
      </div>
    </div>
  );
}

function CommoditiesTab() {
  const { source } = useDataSource();
  const [data, setData] = useState<any>(null);
  const [src, setSrc] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchCommodities = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getCommodities(source);
      setData(res.data);
      setSrc(res.source);
    } catch {
      // keep existing data
    } finally {
      setLoading(false);
    }
  }, [source]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(fetchCommodities, { deps: [source] });

  const sections: { title: string; rows: { name: string; value: string; change: number }[] }[] =
    [];

  if (data) {
    for (const [category, items] of Object.entries(data) as [string, any][]) {
      if (category === "timestamp" || typeof items !== "object") continue;
      const rows = Object.entries(items).map(([, v]: [string, any]) => ({
        name: v.name ?? v.symbol ?? "",
        value: `$${fmt(v.price)}`,
        change: v.change_percent,
      }));
      if (rows.length > 0) {
        sections.push({
          title: category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          rows,
        });
      }
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <RefreshBar lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={refresh} />
        <div className="card">
          <h3 className="text-sm font-semibold mb-3">
            Commodities
            <SourceBadge source={src} />
          </h3>
          <DataTable rows={[]} loading={true} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <RefreshBar lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={refresh} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {sections.map((s) => (
          <div key={s.title} className="card">
            <h3 className="text-sm font-semibold mb-3">
              {s.title}
              <SourceBadge source={src} />
            </h3>
            <DataTable rows={s.rows} />
          </div>
        ))}
      </div>
    </div>
  );
}

function CryptoTab() {
  const { source } = useDataSource();
  const [data, setData] = useState<any>(null);
  const [src, setSrc] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchCrypto = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getCrypto(source);
      setData(res.data);
      setSrc(res.source);
    } catch {
      // keep existing data
    } finally {
      setLoading(false);
    }
  }, [source]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(fetchCrypto, { deps: [source] });

  const assetRows: { name: string; value: string; change: number }[] = [];
  if (data?.assets) {
    for (const [, v] of Object.entries(data.assets) as [string, any][]) {
      assetRows.push({
        name: `${v.name} (${v.symbol})`,
        value: `$${fmt(v.current_price)}`,
        change: v.price_change_percentage_24h,
      });
    }
  }

  const overview = data?.market_overview;
  const fearGreed = data?.fear_greed;

  return (
    <div className="space-y-4">
      <RefreshBar lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={refresh} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-semibold mb-3">
            Cryptocurrencies
            <SourceBadge source={src} />
          </h3>
          <DataTable rows={assetRows} loading={loading} />
        </div>
        <div className="card">
          <h3 className="text-sm font-semibold mb-3">Market Overview</h3>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-terminal-muted text-sm">
              <span className="animate-pulse">Loading...</span>
            </div>
          ) : overview ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-terminal-muted">Total Market Cap</span>
                <span className="tabular-nums">
                  ${(overview.total_market_cap / 1e12).toFixed(2)}T
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-terminal-muted">24h Volume</span>
                <span className="tabular-nums">
                  ${(overview.total_volume / 1e9).toFixed(1)}B
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-terminal-muted">BTC Dominance</span>
                <span className="tabular-nums">
                  {overview.btc_dominance?.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-terminal-muted">ETH Dominance</span>
                <span className="tabular-nums">
                  {overview.eth_dominance?.toFixed(1)}%
                </span>
              </div>
              {fearGreed && (
                <div className="flex justify-between border-t border-terminal-border pt-3 mt-3">
                  <span className="text-terminal-muted">Fear & Greed</span>
                  <span
                    className={`tabular-nums font-medium ${
                      fearGreed.value >= 55
                        ? "text-terminal-green"
                        : fearGreed.value <= 45
                          ? "text-terminal-red"
                          : "text-terminal-muted"
                    }`}
                  >
                    {fearGreed.value} — {fearGreed.classification}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-terminal-muted text-sm">No data available</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────

export default function MarketData() {
  const [activeTab, setActiveTab] = useState<Tab>("equities");

  const content: Record<Tab, JSX.Element> = {
    equities: <EquitiesTab />,
    "fixed-income": <FixedIncomeTab />,
    fx: <FXTab />,
    commodities: <CommoditiesTab />,
    crypto: <CryptoTab />,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Market Data</h1>
        <p className="text-xs text-terminal-muted mt-1">
          Multi-asset class explorer
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-terminal-border">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`pb-2 text-sm font-medium ${activeTab === t.id ? "tab-active" : "tab-inactive"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {content[activeTab]}
    </div>
  );
}
