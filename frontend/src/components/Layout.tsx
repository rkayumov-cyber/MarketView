import { NavLink, Outlet } from "react-router-dom";
import { useDataSource } from "../context/DataSourceContext";

const navItems = [
  { to: "/", label: "Dashboard", icon: "\u25C8" },
  { to: "/market-data", label: "Market Data", icon: "\u25C9" },
  { to: "/reports", label: "Reports", icon: "\u25CA" },
  { to: "/data-sources", label: "Data Sources", icon: "\u25C6" },
  { to: "/health", label: "Health", icon: "\u25CF" },
];

export default function Layout() {
  const { source, setSource } = useDataSource();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-terminal-surface border-r border-terminal-border flex flex-col">
        <div className="p-4 border-b border-terminal-border">
          <h1 className="text-lg font-bold tracking-wider text-terminal-accent">
            MARKETVIEW
          </h1>
          <p className="text-[10px] text-terminal-muted tracking-widest mt-0.5">
            TRADING TERMINAL
          </p>
        </div>

        <nav className="flex-1 py-3">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "text-terminal-accent bg-terminal-accent/10 border-r-2 border-terminal-accent"
                    : "text-terminal-muted hover:text-gray-300 hover:bg-white/[0.02]"
                }`
              }
            >
              <span className="text-xs">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-terminal-border">
          {/* Data source toggle */}
          <div className="flex items-center gap-1.5 mb-3">
            <button
              onClick={() => setSource("live")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                source === "live"
                  ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40"
                  : "text-terminal-muted hover:text-gray-300 hover:bg-white/[0.04]"
              }`}
            >
              <span
                className={`inline-block w-1.5 h-1.5 rounded-full ${
                  source === "live" ? "bg-emerald-400" : "bg-terminal-muted/50"
                }`}
              />
              Live
            </button>
            <button
              onClick={() => setSource("mock")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                source === "mock"
                  ? "bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/40"
                  : "text-terminal-muted hover:text-gray-300 hover:bg-white/[0.04]"
              }`}
            >
              <span
                className={`inline-block w-1.5 h-1.5 rounded-full ${
                  source === "mock" ? "bg-amber-400" : "bg-terminal-muted/50"
                }`}
              />
              Mock
            </button>
          </div>
          <div className="text-[10px] text-terminal-muted">
            <div>v1.0.0 — React Frontend</div>
            <div className="mt-1">API: localhost:8000</div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
