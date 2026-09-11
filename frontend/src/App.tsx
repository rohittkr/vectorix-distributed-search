import { NavLink, Route, Routes } from "react-router-dom";

import AnalyticsPage from "./pages/AnalyticsPage";
import DocumentExplorerPage from "./pages/DocumentExplorerPage";
import IndexingPage from "./pages/IndexingPage";
import SearchPage from "./pages/SearchPage";
import SystemHealthPage from "./pages/SystemHealthPage";

const NAV_ITEMS = [
  { to: "/", label: "Search", end: true },
  { to: "/analytics", label: "Analytics" },
  { to: "/indexing", label: "Indexing" },
  { to: "/documents", label: "Documents" },
  { to: "/system", label: "System health" },
];

export default function App() {
  return (
    <div className="app-shell">
      <nav className="app-nav">
        <div className="app-nav-brand">Meridian Search</div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `app-nav-link${isActive ? " active" : ""}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/indexing" element={<IndexingPage />} />
          <Route path="/documents" element={<DocumentExplorerPage />} />
          <Route path="/system" element={<SystemHealthPage />} />
        </Routes>
      </main>
    </div>
  );
}
