import { useEffect, useState, useCallback, useRef } from "react";
import { useRefreshInterval } from "../context/RefreshContext";

interface UseAutoRefreshOptions {
  /** Extra deps that trigger an immediate re-fetch (e.g. data source) */
  deps?: unknown[];
}

interface UseAutoRefreshReturn {
  lastUpdated: Date | null;
  refreshing: boolean;
  refresh: () => void;
}

/**
 * Hook that calls `fetchFn` on mount, then auto-refreshes at the global
 * interval.  Returns last-updated time, refreshing state, and a manual
 * refresh trigger.
 */
export function useAutoRefresh(
  fetchFn: () => Promise<void>,
  opts?: UseAutoRefreshOptions,
): UseAutoRefreshReturn {
  const { interval } = useRefreshInterval();
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const deps = opts?.deps ?? [];
  const mountedRef = useRef(true);

  // Stable reference to fetchFn so the interval doesn't reset on every render
  const fnRef = useRef(fetchFn);
  fnRef.current = fetchFn;

  const doFetch = useCallback(async () => {
    setRefreshing(true);
    try {
      await fnRef.current();
      if (mountedRef.current) setLastUpdated(new Date());
    } catch {
      // errors handled by the caller's fetch function
    } finally {
      if (mountedRef.current) setRefreshing(false);
    }
  }, []);

  // Fetch on mount + whenever deps change
  useEffect(() => {
    doFetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps]);

  // Auto-refresh interval
  useEffect(() => {
    if (interval === 0) return; // paused
    const id = window.setInterval(doFetch, interval * 1000);
    return () => window.clearInterval(id);
  }, [interval, doFetch]);

  // Cleanup
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return { lastUpdated, refreshing, refresh: doFetch };
}
