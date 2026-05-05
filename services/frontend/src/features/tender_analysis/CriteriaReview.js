import React, { useState, useEffect } from 'react';
import { Lock, Unlock, Edit3, AlertTriangle, Check } from 'lucide-react';
import { getTender, getTenders } from '../../api';

export default function CriteriaReview() {
  const [isLocked, setIsLocked] = useState(false);
  const [criteria, setCriteria] = useState([]);
  const [tender, setTender] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTenderData = async () => {
      try {
        const urlParams = new URLSearchParams(window.location.search);
        let tenderId = urlParams.get('tender_id');

        if (!tenderId) {
          // Fetch latest tender
          const listRes = await getTenders();
          if (listRes.data && listRes.data.length > 0) {
            tenderId = listRes.data[0].id;
          } else {
            setLoading(false);
            return;
          }
        }

        const res = await getTender(tenderId);
        setTender(res.data);
        setCriteria(res.data.criteria || []);
        setIsLocked(res.data.status === 'locked' || res.data.status === 'evaluated');
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch criteria:", err);
        setError("Failed to load tender data. Please try again.");
        setLoading(false);
      }
    };

    fetchTenderData();
  }, []);

  const typeColors = {
    financial: 'var(--success)',
    technical: 'var(--info)',
    compliance: 'var(--warning)',
    conditional: 'var(--accent-primary)',
  };

  const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0);

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Criterion Registry {tender && `— ${tender.title}`}</h2>
          <p>Extracted from tender PDF by Gemini 2.5 Flash — review and lock before evaluation</p>
        </div>
        <button className={`btn ${isLocked ? 'btn-secondary' : 'btn-primary'}`}
          onClick={() => setIsLocked(!isLocked)}>
          {isLocked ? <><Lock size={16} /> Locked</> : <><Unlock size={16} /> Lock Registry</>}
        </button>
      </div>

      {/* Summary Bar */}
      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-label">Total Criteria</div>
          <div className="stat-value accent">{criteria.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Mandatory</div>
          <div className="stat-value danger">{criteria.filter(c => c.mandatory).length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Weight</div>
          <div className="stat-value" style={{ color: totalWeight === 100 ? 'var(--success)' : 'var(--warning)' }}>
            {totalWeight}%
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Status</div>
          <div className="stat-value">
            <span className={`badge ${isLocked ? 'locked' : 'draft'}`}>{isLocked ? 'Locked' : 'Draft'}</span>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>Loading criteria...</div>
      ) : error ? (
        <div style={{ color: 'var(--danger)', padding: '20px' }}>{error}</div>
      ) : criteria.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>No criteria found for this tender.</div>
      ) : (
      <>
      {/* Criteria Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Criterion</th>
              <th>Type</th>
              <th>Mandatory</th>
              <th>Threshold</th>
              <th>Weight</th>
              <th>Source</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {criteria.map((c) => (
              <tr key={c.criterion_id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-accent)' }}>
                  {c.criterion_id}
                </td>
                <td>
                  <div style={{ maxWidth: '320px' }}>
                    {c.text}
                    {c.ambiguous && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px', color: 'var(--warning)', fontSize: '11px' }}>
                        <AlertTriangle size={12} /> Ambiguous — review threshold
                      </div>
                    )}
                  </div>
                </td>
                <td>
                  <span style={{
                    padding: '3px 8px', borderRadius: '100px', fontSize: '11px', fontWeight: 600,
                    background: `${typeColors[c.type]}20`, color: typeColors[c.type],
                  }}>
                    {c.type}
                  </span>
                </td>
                <td>
                  {c.mandatory ? (
                    <span className="badge fail" style={{ fontSize: '10px' }}>REQUIRED</span>
                  ) : (
                    <span className="badge draft" style={{ fontSize: '10px' }}>OPTIONAL</span>
                  )}
                </td>
                <td style={{ fontSize: '13px', fontFamily: 'var(--font-mono)' }}>
                  {c.threshold ? (
                    c.threshold.effect
                      ? <span style={{ color: 'var(--accent-primary)', fontSize: '11px' }}>{c.threshold.effect}</span>
                      : <span>{c.threshold.operator} {c.threshold.value} {c.threshold.unit || ''}</span>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>—</span>
                  )}
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{ width: '40px', height: '6px', borderRadius: '100px', background: 'var(--bg-input)', overflow: 'hidden' }}>
                      <div style={{ width: `${c.weight}%`, height: '100%', borderRadius: '100px', background: typeColors[c.type] }} />
                    </div>
                    <span style={{ fontSize: '13px', fontWeight: 600 }}>{c.weight}%</span>
                  </div>
                </td>
                <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {c.source_section} (p.{c.source_page})
                </td>
                <td>
                  {!isLocked && (
                    <button className="btn btn-secondary btn-sm">
                      <Edit3 size={12} /> Edit
                    </button>
                  )}
                  {isLocked && <Check size={16} color="var(--success)" />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </>
      )}
    </div>
  );
}
