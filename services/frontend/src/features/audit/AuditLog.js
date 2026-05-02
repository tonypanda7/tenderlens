import React, { useState } from 'react';
import { Shield, CheckCircle, XCircle, FileText, Download } from 'lucide-react';

export default function AuditLog() {
  const [logs] = useState([
    {
      id: 'a_004', event: 'tender.locked', payload: { tender_id: 'CRPF-2024-CONST-031', lock_hash: '8f43b2...' },
      prev_hash: 'a3d9f1...', this_hash: '8f43b2...', ts: '2026-05-02T10:30:00Z', valid: true
    },
    {
      id: 'a_005', event: 'bidder.scored', payload: { bidder_id: 'b_021', score: 87.4, formula: '(C1: 35% x 1.0) + ...' },
      prev_hash: '8f43b2...', this_hash: 'c2e8a9...', ts: '2026-05-02T10:35:12Z', valid: true
    },
    {
      id: 'a_006', event: 'reviewer.action', payload: { queue_id: 'rq_001', action: 'override', reason: 'Verified manually from Annexure B' },
      prev_hash: 'c2e8a9...', this_hash: 'd9f1b4...', ts: '2026-05-02T11:15:44Z', valid: true
    }
  ]);

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Audit Log & Integrity</h2>
          <p>Append-only cryptographic hash chain for tender CRPF-2024-CONST-031</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary">
            <Shield size={16} /> Verify Chain
          </button>
          <button className="btn btn-primary">
            <Download size={16} /> Export Signed PDF
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px', background: 'var(--success-bg)', borderColor: 'rgba(34,197,94,0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--success)' }}>
          <CheckCircle size={24} />
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 700 }}>Chain Integrity Verified</h3>
            <p style={{ fontSize: '13px', opacity: 0.9 }}>All 142 events match their cryptographic signatures. No tampering detected.</p>
          </div>
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Timestamp (UTC)</th>
              <th>Event Type</th>
              <th>Payload details</th>
              <th>Chain Hash (this_hash)</th>
              <th>Integrity</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.id}>
                <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {new Date(log.ts).toLocaleString()}
                </td>
                <td>
                  <span style={{ 
                    padding: '3px 8px', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                    borderRadius: '4px', fontSize: '12px', fontFamily: 'var(--font-mono)' 
                  }}>
                    {log.event}
                  </span>
                </td>
                <td style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                    {JSON.stringify(log.payload)}
                  </pre>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-accent)' }}>
                  {log.this_hash}
                </td>
                <td>
                  {log.valid ? <CheckCircle size={16} color="var(--success)" /> : <XCircle size={16} color="var(--danger)" />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
