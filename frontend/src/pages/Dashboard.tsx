import { useState, useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import MetricCard from "../components/MetricCard";
import StatusBadge from "../components/StatusBadge";
import ChartCard from "../components/ChartCard";
import RefreshBar from "../components/RefreshBar";
import {
  getHealth,
  getFredYieldCurve,
  getFredRates,
  getFredInflation,
  getMarketSnapshot,
} from "../api/client";
import { useDataSource } from "../context/DataSourceContext";
import { useAutoRefresh } from "../hooks/useAutoRefresh";

// Fallback data when both API + snapshot are unavailable
const fallbackMetrics = {
  spx: { value: "5,924.02", change: 0.24 },
  vix: { value: "16.32", change: -3.18 },
  tenYear: { value: "4.28", change: 0.02, suffix: "%" },
  btc: { value: "97,432", change: 1.87 },
  gold: { value: "2,918", change: 0.42 },
  dxy: { value: "106.82", change: -0.15 },
};

const fallbackYieldCurve = [
  { maturity: "FF", yield: 5.33 },
  { maturity: "2Y", yield: 4.26 },
  { maturity: "5Y", yield: 4.13 },
  { maturity: "10Y", yield: 4.28 },
  { maturity: "30Y", yield: 4.51 },
];

const fallbackSectors = [
  { name: "Tech", value: 1.2 },
  { name: "Health", value: 0.8 },
  { name: "Finance", value: 0.3 },
  { name: "Energy", value: -0.5 },
  { name: "Cons.Disc", value: -0.9 },
  { name: "Utilities", value: 0.1 },
  { name: "Materials", value: -0.3 },
  { name: "Industrials", value: 0.6 },
];

function formatPrice(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: n >= 1000 ? 0 : 2,
    maximumFractionDigits: n >= 1000 ? 0 : 2,
  });
}

export default function Dashboard() {
  const { source } = useDataSource();
  const [regime, setRegime] = useState("risk_on");
  const [apiStatus, setApiStatus] = useState<"online" | "offline">("offline");
  const [dataSource, setDataSource] = useState<string>("");
  const [yieldCurve, setYieldCurve] = useState(fallbackYieldCurve);
  const [metrics, setMetrics] = useState(fallbackMetrics);
  const [sectors, setSectors] = useState(fallbackSectors);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [health, snapshotRes, ycData, ratesData, inflationData] =
        await Promise.all([
          getHealth().catch(() => null),
          getMarketSnapshot(source).catch(() => null),
          getFredYieldCurve().catch(() => null),
          getFredRates().catch(() => null),
          getFredInflation().catch(() => null),
        ]);

      if (health) setApiStatus("online");

      // Use snapshot data for metrics
      if (snapshotRes?.data) {
        const d = snapshotRes.data;
        setDataSource(snapshotRes.source ?? "");

        const newMetrics = { ...fallbackMetrics };

        if (d.spx) {
          newMetrics.spx = {
            value: formatPrice(d.spx.current_price),
            change: d.spx.change_percent,
          };
        }
        if (d.vix) {
          newMetrics.vix = {
            value: formatPrice(d.vix.current_price),
            change: d.vix.change_percent,
          };
        }
        if (d.dxy) {
          newMetrics.dxy = {
            value: d.dxy.value?.toFixed(2) ?? d.dxy.rate?.toFixed(2) ?? "—",
            change: d.dxy.change_percent,
          };
        }
        if (d.bitcoin) {
          newMetrics.btc = {
            value: formatPrice(d.bitcoin.current_price),
            change:
              d.bitcoin.price_change_percentage_24h ??
              d.bitcoin.change_percent ??
              0,
          };
        }
        if (d.gold) {
          newMetrics.gold = {
            value: formatPrice(d.gold.price ?? d.gold.current_price ?? 0),
            change: d.gold.change_percent,
          };
        }

        // Yield curve from snapshot
        if (d.yield_curve) {
          const yc = d.yield_curve;
          const curve = [
            { maturity: "FF", yield: yc.fed_funds },
            { maturity: "2Y", yield: yc.treasury_2y },
            ...(yc.treasury_5y != null
              ? [{ maturity: "5Y", yield: yc.treasury_5y }]
              : []),
            { maturity: "10Y", yield: yc.treasury_10y },
            { maturity: "30Y", yield: yc.treasury_30y },
          ].filter((p) => p.yield != null);
          if (curve.length > 0) setYieldCurve(curve);
        }

        setMetrics(newMetrics);
      }

      // Override yield curve from FRED if available (more granular)
      if (ycData?.data) {
        const d = ycData.data;
        const curve = [
          { maturity: "FF", yield: d.fed_funds },
          { maturity: "2Y", yield: d.treasury_2y },
          { maturity: "10Y", yield: d.treasury_10y },
          { maturity: "30Y", yield: d.treasury_30y },
        ].filter((p) => p.yield != null);
        if (curve.length > 0) setYieldCurve(curve);
      }

      // Override 10Y from FRED rates
      if (ratesData?.data) {
        const tenY = ratesData.data.treasury_10y;
        if (tenY?.latest_value != null) {
          setMetrics((prev) => ({
            ...prev,
            tenYear: {
              value: tenY.latest_value.toFixed(2),
              change: tenY.pct_change ?? 0,
              suffix: "%",
            },
          }));
        }
      }

      // Regime from inflation
      if (inflationData?.data) {
        const cpi = inflationData.data.cpi;
        if (cpi?.latest_value != null) {
          if (cpi.latest_value > 3.0) setRegime("inflationary_expansion");
          else if (cpi.latest_value < 1.5) setRegime("deflationary");
          else setRegime("goldilocks");
        }
      }
    } catch {
      // keep fallback data
    } finally {
      setLoading(false);
    }
  }, [source]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(fetchData, {
    deps: [source],
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Dashboard</h1>
          <div className="mt-1">
            <RefreshBar lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={refresh} />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={regime} size="md" />
          <span
            className={`text-xs px-2 py-1 rounded ${apiStatus === "online" ? "bg-terminal-green/20 text-terminal-green" : "bg-terminal-red/20 text-terminal-red"}`}
          >
            API {apiStatus}
          </span>
          {dataSource && (
            <span
              className={`text-[10px] px-2 py-0.5 rounded ${
                dataSource === "live"
                  ? "bg-emerald-500/20 text-emerald-400"
                  : dataSource.includes("fallback")
                    ? "bg-orange-500/20 text-orange-400"
                    : "bg-amber-500/20 text-amber-400"
              }`}
            >
              {dataSource}
            </span>
          )}
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          label="S&P 500"
          value={metrics.spx.value}
          change={metrics.spx.change}
          loading={loading}
        />
        <MetricCard
          label="VIX"
          value={metrics.vix.value}
          change={metrics.vix.change}
          loading={loading}
        />
        <MetricCard
          label="10Y Treasury"
          value={metrics.tenYear.value}
          change={metrics.tenYear.change}
          suffix={metrics.tenYear.suffix}
          loading={loading}
        />
        <MetricCard
          label="Bitcoin"
          value={metrics.btc.value}
          change={metrics.btc.change}
          loading={loading}
        />
        <MetricCard
          label="Gold"
          value={metrics.gold.value}
          change={metrics.gold.change}
          loading={loading}
        />
        <MetricCard
          label="DXY"
          value={metrics.dxy.value}
          change={metrics.dxy.change}
          loading={loading}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="US Treasury Yield Curve" subtitle="Current snapshot">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={yieldCurve}>
              <defs>
                <linearGradient id="yieldGrad" x1="0" y1="0" x2="0" y2="1">
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
                contentStyle={{
                  background: "#111827",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  fontSize: 12,
                }}
                formatter={(v: number) => [`${v.toFixed(2)}%`, "Yield"]}
              />
              <Area
                type="monotone"
                dataKey="yield"
                stroke="#3b82f6"
                fill="url(#yieldGrad)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Sector Performance" subtitle="Daily change">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={sectors} layout="vertical">
              <XAxis
                type="number"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#1e293b" }}
                tickLine={false}
                tickFormatter={(v: number) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={72}
              />
              <Tooltip
                contentStyle={{
                  background: "#111827",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  fontSize: 12,
                }}
                formatter={(v: number) => [`${v.toFixed(2)}%`, "Change"]}
              />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                {sectors.map((s, i) => (
                  <Cell
                    key={i}
                    fill={s.value >= 0 ? "#22c55e" : "#ef4444"}
                    fillOpacity={0.7}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Quick actions */}
      <div className="card">
        <h3 className="text-sm font-semibold mb-3">Quick Actions</h3>
        <div className="flex flex-wrap gap-2">
          <a href="/reports" className="btn-primary text-sm">
            Generate Report
          </a>
          <a href="/market-data" className="btn-secondary text-sm">
            Explore Market Data
          </a>
          <a href="/health" className="btn-secondary text-sm">
            System Health
          </a>
        </div>
      </div>
    </div>
  );
}
