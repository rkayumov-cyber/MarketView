import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

export type DataSource = "live" | "mock";

interface DataSourceContextValue {
  source: DataSource;
  setSource: (s: DataSource) => void;
}

const DataSourceContext = createContext<DataSourceContextValue>({
  source: "live",
  setSource: () => {},
});

const STORAGE_KEY = "marketview_data_source";

export function DataSourceProvider({ children }: { children: ReactNode }) {
  const [source, setSource] = useState<DataSource>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "mock" ? "mock" : "live";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, source);
  }, [source]);

  return (
    <DataSourceContext.Provider value={{ source, setSource }}>
      {children}
    </DataSourceContext.Provider>
  );
}

export function useDataSource() {
  return useContext(DataSourceContext);
}
