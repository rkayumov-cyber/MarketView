import { useRefreshInterval, REFRESH_OPTIONS } from "../context/RefreshContext";

interface RefreshBarProps {
  lastUpdated: Date | null;
  refreshing: boolean;
  onRefresh: () => void;
}

function timeAgo(d: Date): string {
  const sec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  return `${min}m ago`;
}

export default function RefreshBar({ lastUpdated, refreshing, onRefresh }: RefreshBarProps) {
  const { interval } = useRefreshInterval();
  const label = REFRESH_OPTIONS.find((o) => o.value === interval)?.label ?? "Off";

  return (
    <div className="flex items-center gap-3 text-[11px] text-terminal-muted">
      {lastUpdated && (
        <span>
          Updated {timeAgo(lastUpdated)}
        </span>
      )}
      <span className="opacity-50">|</span>
      <span>
        Auto-refresh: <span className={interval > 0 ? "text-blue-400" : "text-terminal-muted"}>{label}</span>
      </span>
      <button
        onClick={onRefresh}
        disabled={refreshing}
        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
          refreshing
            ? "bg-white/5 text-terminal-muted cursor-not-allowed"
            : "bg-white/5 text-gray-300 hover:bg-white/10"
        }`}
      >
        {refreshing ? "Refreshing..." : "Refresh"}
      </button>
    </div>
  );
}
