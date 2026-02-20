import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

export type RefreshInterval = 60 | 180 | 300 | 0; // seconds; 0 = paused

export const REFRESH_OPTIONS: { label: string; value: RefreshInterval }[] = [
  { label: "1 min", value: 60 },
  { label: "3 min", value: 180 },
  { label: "5 min", value: 300 },
  { label: "Off", value: 0 },
];

interface RefreshContextValue {
  interval: RefreshInterval;
  setInterval: (v: RefreshInterval) => void;
}

const RefreshContext = createContext<RefreshContextValue>({
  interval: 300,
  setInterval: () => {},
});

const STORAGE_KEY = "marketview_refresh_interval";

export function RefreshProvider({ children }: { children: ReactNode }) {
  const [interval, setInterval] = useState<RefreshInterval>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) {
      const n = Number(stored);
      if ([0, 60, 180, 300].includes(n)) return n as RefreshInterval;
    }
    return 300; // default 5 min
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(interval));
  }, [interval]);

  return (
    <RefreshContext.Provider value={{ interval, setInterval }}>
      {children}
    </RefreshContext.Provider>
  );
}

export function useRefreshInterval() {
  return useContext(RefreshContext);
}
