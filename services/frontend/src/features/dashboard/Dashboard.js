import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileUp, Search, BarChart3, ClipboardCheck, Shield, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats] = useState({
    totalTenders: 3,
    activeTenders: 1,
    totalBidders: 47,
    pendingReviews: 5,
  });

  const recentTenders = [
    { id: 'CRPF-2024-CONST-031', title: 'CRPF Barracks Construction — Phase III', status: 'evaluated', bidders: 12, score: 87.4 },
    { id: 'CRPF-2024-MAINT-018', title: 'Annual Maintenance Contract — Delhi Zone', status: 'locked', bidders: 23, score: null },
    { id: 'CRPF-2024-IT-009', title: 'IT Infrastructure Upgrade — HQ', status: 'draft', bidders: 12, score: null },
  ];

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of tender evaluations and system status</p>
      </div>

      {/* Stats Bar */}
      <div className="stats-bar">
        <div className="stat-card" onClick={() => navigate('/criteria')}>
          <div className="stat-label">Total Tenders</div>
          <div className="stat-value accent">{stats.totalTenders}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Evaluations</div>
          <div className="stat-value info">{stats.activeTenders}</div>
        </div>
        <div className="stat-card" onClick={() => navigate('/ranking')}>
          <div className="stat-label">Total Bidders</div>
          <div className="stat-value success">{stats.totalBidders}</div>
        </div>
        <div className="stat-card" onClick={() => navigate('/reviewer')}>
          <div className="stat-label">Pending Reviews</div>
          <div className="stat-value warning">{stats.pendingReviews}</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '32px' }}>
        {[
          { icon: FileUp, label: 'Upload Tender', path: '/upload', color: 'var(--accent-primary)' },
          { icon: Search, label: 'Review Criteria', path: '/criteria', color: 'var(--info)' },
          { icon: BarChart3, label: 'View Rankings', path: '/ranking', color: 'var(--success)' },
          { icon: ClipboardCheck, label: 'Reviewer Queue', path: '/reviewer', color: 'var(--warning)' },
          { icon: Shield, label: 'Audit Trail', path: '/audit', color: 'var(--danger)' },
        ].map(({ icon: Icon, label, path, color }) => (
          <button key={path} className="card" onClick={() => navigate(path)}
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px', border: 'none' }}>
            <Icon size={20} color={color} />
            <span style={{ fontSize: '13px', fontWeight: 600 }}>{label}</span>
          </button>
        ))}
      </div>

      {/* Recent Tenders */}
      <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Recent Tenders</h3>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Tender ID</th>
              <th>Title</th>
              <th>Status</th>
              <th>Bidders</th>
              <th>Top Score</th>
            </tr>
          </thead>
          <tbody>
            {recentTenders.map((tender) => (
              <tr key={tender.id} onClick={() => navigate('/ranking')}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-accent)' }}>
                  {tender.id}
                </td>
                <td>{tender.title}</td>
                <td>
                  <span className={`badge ${tender.status}`}>
                    {tender.status}
                  </span>
                </td>
                <td>{tender.bidders}</td>
                <td>
                  {tender.score ? (
                    <span style={{ fontWeight: 700, color: 'var(--success)' }}>{tender.score}</span>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
