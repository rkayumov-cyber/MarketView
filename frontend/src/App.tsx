import { Routes, Route, Navigate } from "react-router-dom";
import { DataSourceProvider } from "./context/DataSourceContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import MarketData from "./pages/MarketData";
import Reports from "./pages/Reports";
import Health from "./pages/Health";
import DataSources from "./pages/DataSources";

export default function App() {
  return (
    <DataSourceProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/market-data" element={<MarketData />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/data-sources" element={<DataSources />} />
          <Route path="/health" element={<Health />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </DataSourceProvider>
  );
}
