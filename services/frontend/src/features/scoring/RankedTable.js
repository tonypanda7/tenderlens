import React, { useState } from 'react';
import { ChevronRight, Download, X, Search, CheckCircle, AlertCircle, Clock } from 'lucide-react';

export default function RankedTable() {
  const [selectedBidder, setSelectedBidder] = useState(null);

  // Mock data representing F-05 Output
  const [rankings] = useState([
    {
      bidder_id: 'b_021', bidder_name: 'M/s Sharma Construction Pvt Ltd', rank: 1,
      final_score: 87.4, financial_score: 35.0, technical_score: 35.0, compliance_score: 17.4,
      status: 'auto_approved', eligible: true,
      rationale: 'Ranked #1 because it has the highest turnover among eligible bidders at Rs. 7.24 Cr average (44.8% above the Rs. 5 Cr threshold), completed 4 qualifying works exceeding the 3-work requirement, and holds valid GST and ISO certifications. No mandatory criterion failed.',
      criteria: [
        { id: 'C1', verdict: 'pass', score: 35.0, max: 35, type: 'financial', value: '7.24 Cr avg FY22-24', conf: 0.96 },
        { id: 'C2', verdict: 'pass', score: 35.0, max: 35, type: 'technical', value: '4 works, each above Rs. 1.5 Cr', conf: 0.89 },
        { id: 'C3', verdict: 'pass', score: 20.0, max: 20, type: 'compliance', value: '29AABCT1332L1ZN', conf: 0.98 },
        { id: 'C4', verdict: 'fail', score: 0.0, max: 0, type: 'compliance', value: 'Not accredited', conf: 0.91 }, // non-mandatory fail
      ]
    },
    {
      bidder_id: 'b_088', bidder_name: 'Apex Infrastructure Group', rank: 2,
      final_score: 76.2, financial_score: 28.5, technical_score: 27.7, compliance_score: 20.0,
      status: 'reviewer_approved', eligible: true,
      rationale: 'Ranked #2 due to lower financial turnover (Rs. 5.8 Cr) compared to the top bidder, but still meets all mandatory technical and compliance thresholds. Required reviewer override on MSME certificate validation.',
      criteria: [
        { id: 'C1', verdict: 'pass', score: 28.5, max: 35, type: 'financial', value: '5.8 Cr avg FY22-24', conf: 0.92 },
        { id: 'C2', verdict: 'pass', score: 27.7, max: 35, type: 'technical', value: '3 works completed', conf: 0.88 },
        { id: 'C3', verdict: 'pass', score: 20.0, max: 20, type: 'compliance', value: 'Valid GSTIN', conf: 0.99 },
      ]
    },
    {
      bidder_id: 'b_015', bidder_name: 'National Builders Alliance', rank: 3,
      final_score: 65.0, financial_score: 35.0, technical_score: 10.0, compliance_score: 20.0,
      status: 'pending_review', eligible: true,
      rationale: 'Ranked #3. While turnover is very high (Rs. 12 Cr), technical qualification is borderline. Currently awaiting human review on one technical criterion flag.',
      criteria: [
        { id: 'C1', verdict: 'pass', score: 35.0, max: 35, type: 'financial', value: '12.1 Cr avg FY22-24', conf: 0.97 },
        { id: 'C2', verdict: 'review', score: 10.0, max: 35, type: 'technical', value: '2 works clearly stated, 1 ambiguous', conf: 0.58 },
        { id: 'C3', verdict: 'pass', score: 20.0, max: 20, type: 'compliance', value: 'Active GST', conf: 0.99 },
      ]
    }
  ]);

  const [disqualified] = useState([
    {
      bidder_id: 'b_044', bidder_name: 'Metro Engineering Ltd',
      reason: 'Turnover below mandatory threshold of Rs. 5 Cr (Found: Rs. 3.2 Cr). MSME exemption not applicable as certificate expired.',
    },
    {
      bidder_id: 'b_092', bidder_name: 'Rao & Sons Contractors',
      reason: 'GST certificate not found in any submitted document.',
    }
  ]);

  return (
    <div style={{ position: 'relative' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Comparative Ranking</h2>
          <p>Tender: <strong>CRPF-2024-CONST-031</strong></p>
        </div>
        <button className="btn btn-secondary">
          <Download size={16} /> Export Signed PDF
        </button>
      </div>

      {/* Summary Bar */}
      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-label">Total Bidders</div>
          <div className="stat-value accent">47</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Eligible</div>
          <div className="stat-value success">38</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Disqualified</div>
          <div className="stat-value danger">9</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Pending Reviews</div>
          <div className="stat-value warning">5</div>
        </div>
      </div>

      {/* Ranked Table */}
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
              <th>Financial</th>
              <th>Technical</th>
              <th>Status</th>
              <th>Criteria</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rankings.map(b => (
              <tr key={b.bidder_id} onClick={() => setSelectedBidder(b)} style={{ background: selectedBidder?.bidder_id === b.bidder_id ? 'var(--bg-card-hover)' : '' }}>
                <td>
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '50%', background: b.rank === 1 ? 'var(--accent-gradient)' : 'var(--bg-elevated)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '13px',
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
                    <span className="score-value">{b.final_score.toFixed(1)}</span>
                  </div>
                </td>
                <td style={{ fontSize: '13px' }}>{b.financial_score.toFixed(1)} <span style={{ color: 'var(--text-muted)' }}>/ 35</span></td>
                <td style={{ fontSize: '13px' }}>{b.technical_score.toFixed(1)} <span style={{ color: 'var(--text-muted)' }}>/ 35</span></td>
                <td>
                  {b.status === 'auto_approved' && <span className="badge auto"><CheckCircle size={10} /> Auto</span>}
                  {b.status === 'reviewer_approved' && <span className="badge pass"><CheckCircle size={10} /> Reviewed</span>}
                  {b.status === 'pending_review' && <span className="badge review"><Clock size={10} /> Pending</span>}
                </td>
                <td>
                  <div className="criterion-dots">
                    {b.criteria.map(c => (
                      <div key={c.id} className={`criterion-dot ${c.verdict}`} title={`${c.id}: ${c.verdict}`} />
                    ))}
                  </div>
                </td>
                <td style={{ color: 'var(--text-muted)' }}><ChevronRight size={18} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Disqualified Bidders */}
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
                <td style={{ fontSize: '13px', color: 'var(--danger)' }}>{b.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
                  <span style={{ fontSize: '18px', fontWeight: 700 }}>{selectedBidder.final_score.toFixed(1)} / 100</span>
                </div>
                <h3 style={{ fontSize: '15px', fontWeight: 600, marginTop: '8px' }}>{selectedBidder.bidder_name}</h3>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedBidder(null)} style={{ padding: '6px' }}>
                <X size={18} />
              </button>
            </div>
            <div className="side-panel-body">
              {/* Rationale */}
              <div style={{
                background: 'var(--accent-glow)', border: '1px solid var(--border-accent)',
                padding: '16px', borderRadius: 'var(--radius-md)', marginBottom: '24px'
              }}>
                <h4 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Search size={14} /> Gemini Rationale
                </h4>
                <p style={{ fontSize: '14px', lineHeight: 1.6 }}>{selectedBidder.rationale}</p>
              </div>

              {/* Breakdown Table */}
              <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>Criterion Breakdown</h4>
              <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                {selectedBidder.criteria.map((c, i) => (
                  <div key={c.id} style={{
                    padding: '12px 16px', borderBottom: i < selectedBidder.criteria.length - 1 ? '1px solid var(--border)' : 'none',
                    display: 'flex', alignItems: 'flex-start', gap: '12px', background: 'var(--bg-card)'
                  }}>
                    <div className={`criterion-dot ${c.verdict}`} style={{ marginTop: '6px' }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 700 }}>{c.id} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>— {c.type}</span></span>
                        <span style={{ fontSize: '13px', fontWeight: 700 }}>{c.score.toFixed(1)} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>/ {c.max}</span></span>
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                        Extracted: <span style={{ color: 'var(--text-primary)' }}>"{c.value}"</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
                        <span>Confidence: <strong style={{ color: c.conf >= 0.85 ? 'var(--success)' : c.conf >= 0.6 ? 'var(--warning)' : 'var(--danger)' }}>{(c.conf * 100).toFixed(0)}%</strong></span>
                        <span>Source: Page 7</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
