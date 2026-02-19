import { useEffect, useState } from "react";
import StatusBadge from "../components/StatusBadge";
import { getHealth, getHealthDetailed } from "../api/client";

interface ServiceStatus {
  status: string;
  latency_ms?: number;
}

interface HealthData {
  status: string;
  timestamp: string;
  version?: string;
  environment?: string;
  services?: Record<string, ServiceStatus>;
}

export default function Health() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  async function fetchHealth() {
    setLoading(true);
    try {
      // Try detailed first, fall back to basic
      let data: HealthData;
      try {
        data = await getHealthDetailed();
      } catch {
        data = await getHealth();
      }
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  }

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const apiReachable = health !== null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">System Health</h1>
          <p className="text-xs text-terminal-muted mt-1">
            Data source and service status
          </p>
        </div>
        <button onClick={fetchHealth} className="btn-secondary text-xs">
          Refresh
        </button>
      </div>

      {/* Overall status */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold mb-2">API Server</h2>
            <div className="flex items-center gap-3">
              <StatusBadge
                status={apiReachable ? health!.status : "unhealthy"}
                size="md"
              />
              {health?.version && (
                <span className="text-xs text-terminal-muted">
                  v{health.version}
                </span>
              )}
              {health?.environment && (
                <span className="text-xs text-terminal-muted uppercase">
                  {health.environment}
                </span>
              )}
            </div>
          </div>
          <div className="text-right text-xs text-terminal-muted">
            {lastChecked && (
              <div>Checked: {lastChecked.toLocaleTimeString()}</div>
            )}
            {health?.timestamp && (
              <div>Server: {new Date(health.timestamp).toLocaleString()}</div>
            )}
          </div>
        </div>
      </div>

      {/* Services */}
      {loading ? (
        <div className="card animate-pulse">
          <div className="h-4 w-32 bg-terminal-border rounded mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-terminal-border/50 rounded" />
            ))}
          </div>
        </div>
      ) : apiReachable && health?.services ? (
        <div className="card">
          <h2 className="text-sm font-semibold mb-4">Services</h2>
          <div className="space-y-3">
            {Object.entries(health.services).map(([name, svc]) => (
              <div
                key={name}
                className="flex items-center justify-between py-2 border-b border-terminal-border/50 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium capitalize">
                    {name}
                  </span>
                  <StatusBadge status={svc.status} />
                </div>
                {svc.latency_ms !== undefined && (
                  <span className="text-xs text-terminal-muted tabular-nums">
                    {svc.latency_ms}ms
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : !apiReachable ? (
        <div className="card border-terminal-red/30">
          <h2 className="text-sm font-semibold text-terminal-red mb-2">
            API Unreachable
          </h2>
          <p className="text-xs text-terminal-muted leading-relaxed">
            Cannot connect to the FastAPI backend at{" "}
            <code className="text-terminal-amber">localhost:8000</code>. Ensure
            the server is running:
          </p>
          <pre className="mt-3 text-xs bg-terminal-bg rounded-md p-3 text-terminal-muted">
            {`# Start the API server\ncd MarketView\nuvicorn src.api.main:app --reload --port 8000`}
          </pre>
        </div>
      ) : null}

      {/* Data sources status (static reference) */}
      <div className="card">
        <h2 className="text-sm font-semibold mb-4">Data Sources</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            {
              name: "FRED (Federal Reserve)",
              desc: "Economic indicators, rates, inflation",
              rate: "120 req/min",
            },
            {
              name: "Yahoo Finance",
              desc: "Equities, indices, sectors",
              rate: "33 req/min",
            },
            {
              name: "CoinGecko",
              desc: "Cryptocurrency prices & metrics",
              rate: "30 req/min",
            },
            {
              name: "Reddit (PRAW)",
              desc: "Sentiment analysis",
              rate: "60 req/min",
            },
          ].map((ds) => (
            <div
              key={ds.name}
              className="flex items-start gap-3 p-3 rounded-md bg-terminal-bg"
            >
              <div className="w-2 h-2 rounded-full bg-terminal-muted mt-1.5 shrink-0" />
              <div>
                <div className="text-sm font-medium">{ds.name}</div>
                <div className="text-xs text-terminal-muted mt-0.5">
                  {ds.desc}
                </div>
                <div className="text-[10px] text-terminal-muted mt-1">
                  Rate limit: {ds.rate}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
