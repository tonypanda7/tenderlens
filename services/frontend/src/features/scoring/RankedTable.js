import React, { useState, useEffect } from 'react';
import { ChevronRight, Download, X, Search, CheckCircle, AlertCircle, Clock, BarChart3, RefreshCw } from 'lucide-react';
import { getTenderRanking, getTenders } from '../../api';

export default function RankedTable() {
  const [selectedBidder, setSelectedBidder] = useState(null);
  const [rankings, setRankings] = useState([]);
  const [disqualified, setDisqualified] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tenders, setTenders] = useState([]);
  const [selectedTenderId, setSelectedTenderId] = useState(null);
  const [tenderTitle, setTenderTitle] = useState('');
  const [stats, setStats] = useState({ total: 0, eligible: 0, disqualified: 0, pending: 0 });

  // Fetch tenders list on mount
  useEffect(() => {
    const fetchTenders = async () => {
      try {
        const res = await getTenders();
        if (res.data && res.data.length > 0) {
          setTenders(res.data);
          // Check URL for tender_id param
          const urlParams = new URLSearchParams(window.location.search);
          const urlTenderId = urlParams.get('tender_id');
          const targetId = urlTenderId || res.data[0].id;
          setSelectedTenderId(targetId);
          const found = res.data.find(t => t.id === targetId);
          setTenderTitle(found?.title || targetId);
        } else {
          setLoading(false);
        }
      } catch (err) {
        setError('Failed to load tenders');
        setLoading(false);
      }
    };
    fetchTenders();
  }, []);

  // Fetch ranking when tender changes
  useEffect(() => {
    if (selectedTenderId) {
      fetchRanking(selectedTenderId);
    }
  }, [selectedTenderId]);

  const fetchRanking = async (tenderId) => {
    try {
      setLoading(true);
      setError(null);
      const res = await getTenderRanking(tenderId);
      const data = res.data;

      setRankings(data.rankings || []);
      setDisqualified(data.disqualified || []);
      setStats({
        total: data.total_bidders || 0,
        eligible: data.eligible_count || 0,
        disqualified: data.disqualified_count || 0,
        pending: data.pending_reviews || 0,
      });
      setLoading(false);
    } catch (err) {
      setError('Failed to load ranking data');
      setLoading(false);
    }
  };

  const handleTenderChange = (e) => {
    const id = e.target.value;
    setSelectedTenderId(id);
    const found = tenders.find(t => t.id === id);
    setTenderTitle(found?.title || id);
    setSelectedBidder(null);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Comparative Ranking</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
            <p>Tender:</p>
            {tenders.length > 1 ? (
              <select className="form-input" style={{ width: 'auto', padding: '4px 12px', fontSize: '13px' }}
                value={selectedTenderId || ''} onChange={handleTenderChange}>
                {tenders.map(t => (
                  <option key={t.id} value={t.id}>{t.title}</option>
                ))}
              </select>
            ) : (
              <strong>{tenderTitle}</strong>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={() => fetchRanking(selectedTenderId)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '16px', borderRadius: 'var(--radius-md)', marginBottom: '24px',
          background: 'var(--danger-bg)', color: 'var(--danger)',
          border: '1px solid rgba(239,68,68,0.2)', display: 'flex', alignItems: 'center', gap: '8px',
        }}>
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Summary Bar */}
      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-label">Total Bidders</div>
          <div className="stat-value accent">{stats.total}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Eligible</div>
          <div className="stat-value success">{stats.eligible}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Disqualified</div>
          <div className="stat-value danger">{stats.disqualified}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Pending Reviews</div>
          <div className="stat-value warning">{stats.pending}</div>
        </div>
      </div>

      {/* Empty State */}
      {rankings.length === 0 && disqualified.length === 0 && !error && (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <BarChart3 size={40} style={{ opacity: 0.3, marginBottom: '16px' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '8px', color: 'var(--text-secondary)' }}>
            No Rankings Available Yet
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '400px', margin: '0 auto' }}>
            Upload bidder documents and run the evaluation to see comparative rankings here.
            Go to the <a href="/upload" style={{ color: 'var(--accent-primary)' }}>Upload page</a> to get started.
          </p>
        </div>
      )}

      {/* Ranked Table */}
      {rankings.length > 0 && (
        <>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart3 size={18} color="var(--accent-primary)" /> Eligible Bidders
          </h3>
          <div className="table-container" style={{ marginBottom: '40px' }}>
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Bidder Name</th>
                  <th style={{ width: '25%' }}>Overall Score</th>
                  <th>Status</th>
                  <th>Criteria</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rankings.map(b => (
                  <tr key={b.bidder_id} onClick={() => setSelectedBidder(b)}
                    style={{ background: selectedBidder?.bidder_id === b.bidder_id ? 'var(--bg-card-hover)' : '', cursor: 'pointer' }}>
                    <td>
                      <div style={{
                        width: '28px', height: '28px', borderRadius: '50%',
                        background: b.rank === 1 ? 'var(--accent-gradient)' : 'var(--bg-elevated)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: 800, fontSize: '13px',
                        color: b.rank === 1 ? 'white' : 'var(--text-primary)',
                      }}>
                        {b.rank}
                      </div>
                    </td>
                    <td style={{ fontWeight: 600 }}>{b.bidder_name}</td>
                    <td>
                      <div className="score-bar-container">
                        <div className="score-bar">
                          <div className={`score-bar-fill ${b.final_score >= 80 ? 'high' : b.final_score >= 60 ? 'mid' : 'low'}`}
                            style={{ width: `${b.final_score}%` }} />
                        </div>
                        <span className="score-value">{(b.final_score || 0).toFixed(1)}</span>
                      </div>
                    </td>
                    <td>
                      {b.eligible && <span className="badge pass"><CheckCircle size={10} /> Eligible</span>}
                    </td>
                    <td>
                      <div className="criterion-dots">
                        {(b.criterion_scores || []).map((c, i) => (
                          <div key={i} className={`criterion-dot ${c.verdict}`}
                            title={`${c.criterion_id}: ${c.verdict}`} />
                        ))}
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}><ChevronRight size={18} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Disqualified Bidders */}
      {disqualified.length > 0 && (
        <>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={18} color="var(--danger)" /> Disqualified Bidders
          </h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Bidder Name</th>
                  <th>Disqualification Reason</th>
                </tr>
              </thead>
              <tbody>
                {disqualified.map(b => (
                  <tr key={b.bidder_id}>
                    <td style={{ fontWeight: 600, width: '30%' }}>{b.bidder_name}</td>
                    <td style={{ fontSize: '13px', color: 'var(--danger)' }}>{b.disqualify_reason || 'Mandatory criterion failed'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Side Panel Detail */}
      <div className={`side-panel ${selectedBidder ? 'open' : ''}`}>
        {selectedBidder && (
          <>
            <div className="side-panel-header">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{
                    padding: '2px 8px', background: 'var(--accent-gradient)', borderRadius: '100px',
                    fontSize: '11px', fontWeight: 800, color: 'white'
                  }}>
                    RANK #{selectedBidder.rank}
                  </span>
                  <span style={{ fontSize: '18px', fontWeight: 700 }}>
                    {(selectedBidder.final_score || 0).toFixed(1)} / 100
                  </span>
                </div>
                <h3 style={{ fontSize: '15px', fontWeight: 600, marginTop: '8px' }}>{selectedBidder.bidder_name}</h3>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedBidder(null)} style={{ padding: '6px' }}>
                <X size={18} />
              </button>
            </div>
            <div className="side-panel-body">
              {/* Rationale */}
              {selectedBidder.rationale && (
                <div style={{
                  background: 'var(--accent-glow)', border: '1px solid var(--border-accent)',
                  padding: '16px', borderRadius: 'var(--radius-md)', marginBottom: '24px'
                }}>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Search size={14} /> AI Rationale
                  </h4>
                  <p style={{ fontSize: '14px', lineHeight: 1.6 }}>{selectedBidder.rationale}</p>
                </div>
              )}

              {/* Breakdown Table */}
              <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>Criterion Breakdown</h4>
              <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                {(selectedBidder.criterion_scores || []).map((c, i) => (
                  <div key={c.criterion_id || i} style={{
                    padding: '12px 16px',
                    borderBottom: i < (selectedBidder.criterion_scores || []).length - 1 ? '1px solid var(--border)' : 'none',
                    display: 'flex', alignItems: 'flex-start', gap: '12px', background: 'var(--bg-card)'
                  }}>
                    <div className={`criterion-dot ${c.verdict}`} style={{ marginTop: '6px' }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 700 }}>
                          {c.criterion_id}
                          <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> — {c.layer || 'unknown'}</span>
                        </span>
                        <span style={{ fontSize: '13px', fontWeight: 700 }}>
                          {(c.weighted_score || 0).toFixed(1)}
                        </span>
                      </div>
                      {c.extracted_value && (
                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                          Extracted: <span style={{ color: 'var(--text-primary)' }}>"{c.extracted_value}"</span>
                        </div>
                      )}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
                        <span>Confidence: <strong style={{
                          color: c.confidence >= 0.85 ? 'var(--success)' : c.confidence >= 0.6 ? 'var(--warning)' : 'var(--danger)'
                        }}>{((c.confidence || 0) * 100).toFixed(0)}%</strong></span>
                        {c.source_page && <span>Source: Page {c.source_page}</span>}
                        {c.auto_approved && <span style={{ color: 'var(--success)' }}>✓ Auto-approved</span>}
                      </div>
                    </div>
                  </div>
                ))}
                {(selectedBidder.criterion_scores || []).length === 0 && (
                  <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                    No criterion scores available
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
