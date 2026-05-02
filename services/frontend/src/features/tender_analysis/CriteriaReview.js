import React, { useState } from 'react';
import { Lock, Unlock, Edit3, AlertTriangle, Check } from 'lucide-react';

export default function CriteriaReview() {
  const [isLocked, setIsLocked] = useState(false);

  // Sample extracted criteria matching PRD Section 4.2 JSON schema
  const [criteria, setCriteria] = useState([
    {
      criterion_id: 'C1', text: 'Average annual turnover for last 3 financial years',
      type: 'financial', mandatory: true, weight: 35, source_section: 'Section 4.1',
      source_page: 7, ambiguous: false,
      threshold: { value: 5, unit: 'crore_inr', period: 'FY22-FY24', operator: 'gte' },
    },
    {
      criterion_id: 'C2', text: 'Minimum 3 similar works completed in last 5 years',
      type: 'technical', mandatory: true, weight: 35, source_section: 'Section 4.2',
      source_page: 7, ambiguous: false,
      threshold: { value: 3, unit: 'works', each_value: 1.5, each_unit: 'crore_inr', operator: 'gte' },
    },
    {
      criterion_id: 'C3', text: 'Valid GST registration',
      type: 'compliance', mandatory: true, weight: 20, source_section: 'Section 4.3',
      source_page: 8, ambiguous: false,
      threshold: { value: 'active_gstin', operator: 'eq' },
    },
    {
      criterion_id: 'C4', text: 'ISO 9001:2015 certification — NABCB accredited',
      type: 'compliance', mandatory: true, weight: 0, source_section: 'Section 4.3',
      source_page: 8, ambiguous: false,
      threshold: { value: 'valid_nabcb', operator: 'eq' },
    },
    {
      criterion_id: 'C5', text: 'Defence sector experience',
      type: 'technical', mandatory: false, weight: 10, source_section: 'Section 4.5',
      source_page: 9, ambiguous: false,
      threshold: null,
    },
    {
      criterion_id: 'C6', text: 'MSME registration',
      type: 'conditional', mandatory: false, weight: 0, source_section: 'Section 4.6',
      source_page: 9, ambiguous: false,
      threshold: { effect: 'exempts_C1_turnover_threshold', operator: 'modifier' },
    },
  ]);

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
          <h2>Criterion Registry</h2>
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
    </div>
  );
}
