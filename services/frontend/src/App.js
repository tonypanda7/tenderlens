import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import {
  LayoutDashboard, FileUp, Search, BarChart3,
  ClipboardCheck, Shield, MessageSquare, Settings
} from 'lucide-react';

// Lazy-load feature pages — one folder per feature (PRD Section 9.2)
const Dashboard = lazy(() => import('./features/dashboard/Dashboard'));
const TenderUpload = lazy(() => import('./features/ingest/TenderUpload'));
const CriteriaReview = lazy(() => import('./features/tender_analysis/CriteriaReview'));
const RankedTable = lazy(() => import('./features/scoring/RankedTable'));
const ReviewerQueue = lazy(() => import('./features/reviewer/ReviewerQueue'));
const AuditLog = lazy(() => import('./features/audit/AuditLog'));
const Feedback = lazy(() => import('./features/feedback/Feedback'));

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/upload', icon: FileUp, label: 'Upload' },
  { path: '/criteria', icon: Search, label: 'Criteria' },
  { path: '/ranking', icon: BarChart3, label: 'Ranking' },
  { path: '/reviewer', icon: ClipboardCheck, label: 'Reviewer' },
  { path: '/audit', icon: Shield, label: 'Audit' },
  { path: '/feedback', icon: MessageSquare, label: 'Feedback' },
];

function LoadingFallback() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
      <div className="spinner" />
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="app-layout">
        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <div className="sidebar-logo">
              <div className="logo-icon">TL</div>
              <h1>TenderLens</h1>
            </div>
          </div>
          <nav className="sidebar-nav">
            {navItems.map(({ path, icon: Icon, label }) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon size={18} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <div style={{ padding: '16px 12px', borderTop: '1px solid var(--border)' }}>
            <div className="nav-item" style={{ opacity: 0.6 }}>
              <Settings size={18} />
              <span>Settings</span>
            </div>
          </div>
        </aside>

        {/* ── Main Content ── */}
        <main className="main-content">
          <Suspense fallback={<LoadingFallback />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<TenderUpload />} />
              <Route path="/criteria" element={<CriteriaReview />} />
              <Route path="/ranking" element={<RankedTable />} />
              <Route path="/reviewer" element={<ReviewerQueue />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/feedback" element={<Feedback />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </Router>
  );
}

export default App;
