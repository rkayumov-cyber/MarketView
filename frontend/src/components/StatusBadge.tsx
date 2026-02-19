interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

const colorMap: Record<string, string> = {
  healthy: "bg-terminal-green/20 text-terminal-green border-terminal-green/30",
  degraded: "bg-terminal-amber/20 text-terminal-amber border-terminal-amber/30",
  unhealthy: "bg-terminal-red/20 text-terminal-red border-terminal-red/30",
  ready: "bg-terminal-green/20 text-terminal-green border-terminal-green/30",
  not_ready: "bg-terminal-red/20 text-terminal-red border-terminal-red/30",

  // Market regimes
  goldilocks:
    "bg-terminal-green/20 text-terminal-green border-terminal-green/30",
  risk_on: "bg-terminal-green/20 text-terminal-green border-terminal-green/30",
  inflationary_expansion:
    "bg-terminal-amber/20 text-terminal-amber border-terminal-amber/30",
  stagflation: "bg-terminal-red/20 text-terminal-red border-terminal-red/30",
  deflationary:
    "bg-terminal-amber/20 text-terminal-amber border-terminal-amber/30",
  risk_off: "bg-terminal-red/20 text-terminal-red border-terminal-red/30",
};

const defaultColor =
  "bg-terminal-muted/20 text-terminal-muted border-terminal-muted/30";

export default function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const color = colorMap[status.toLowerCase()] ?? defaultColor;
  const sizeClass =
    size === "md" ? "text-sm px-3 py-1.5" : "text-xs px-2 py-0.5";

  return (
    <span
      className={`inline-flex items-center border rounded-full font-medium tracking-wide uppercase ${color} ${sizeClass}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5" />
      {status.replace(/_/g, " ")}
    </span>
  );
}
