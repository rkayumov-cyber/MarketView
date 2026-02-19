interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number;
  suffix?: string;
  loading?: boolean;
}

export default function MetricCard({
  label,
  value,
  change,
  suffix = "",
  loading = false,
}: MetricCardProps) {
  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-3 w-20 bg-terminal-border rounded mb-3" />
        <div className="h-7 w-24 bg-terminal-border rounded" />
      </div>
    );
  }

  const changeColor =
    change === undefined
      ? "text-terminal-muted"
      : change >= 0
        ? "text-terminal-green"
        : "text-terminal-red";

  const changePrefix = change !== undefined && change >= 0 ? "+" : "";

  return (
    <div className="card hover:border-terminal-accent/40 transition-colors">
      <div className="text-xs text-terminal-muted uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className="text-2xl font-semibold tabular-nums">
        {value}
        {suffix && (
          <span className="text-sm text-terminal-muted ml-1">{suffix}</span>
        )}
      </div>
      {change !== undefined && (
        <div className={`text-xs mt-1 tabular-nums ${changeColor}`}>
          {changePrefix}
          {change.toFixed(2)}%
        </div>
      )}
    </div>
  );
}
