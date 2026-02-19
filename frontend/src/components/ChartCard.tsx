import { ReactNode } from "react";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  loading?: boolean;
}

export default function ChartCard({
  title,
  subtitle,
  children,
  loading = false,
}: ChartCardProps) {
  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-200">{title}</h3>
        {subtitle && (
          <p className="text-xs text-terminal-muted mt-0.5">{subtitle}</p>
        )}
      </div>
      {loading ? (
        <div className="flex items-center justify-center h-48 text-terminal-muted text-xs">
          Loading chart data...
        </div>
      ) : (
        <div className="w-full">{children}</div>
      )}
    </div>
  );
}
