import React, { useState } from 'react';
import { AlertTriangle, Check, X, ShieldAlert, ArrowUpRight } from 'lucide-react';

export default function ReviewerQueue() {
  const [items, setItems] = useState([
    {
      id: 'rq_001', tender_name: 'CRPF-2024-CONST-031', bidder_name: 'National Builders Alliance',
      criterion_id: 'C2', criterion_text: 'Minimum 3 similar works completed in last 5 years',
      flag_reason: 'Confidence 0.58 < 0.60 threshold. Semantic matcher flagged ambiguity in text.',
      extracted_value: 'We have completed 2 major barracks and 1 minor shed repair.',
      confidence: 0.58, status: 'pending', priority: 1, image_url: null,
    },
    {
      id: 'rq_002', tender_name: 'CRPF-2024-CONST-031', bidder_name: 'Metro Engineering Ltd',
      criterion_id: 'C1', criterion_text: 'Average annual turnover >= Rs. 5 Crore',
      flag_reason: 'OCR confidence 0.45 < 0.60 on financial table. Flagged with raw image.',
      extracted_value: '3.2 Cr',
      confidence: 0.45, status: 'escalated', priority: 0, image_url: 'placeholder_crop.jpg',
    }
  ]);

  const [selectedItem, setSelectedItem] = useState(null);
  const [decision, setDecision] = useState('');
  const [reason, setReason] = useState('');
  const [correctedValue, setCorrectedValue] = useState('');

  const handleDecide = () => {
    if (!reason.trim()) {
      alert("Reason is mandatory.");
      return;
    }
    // Update local state (mock API call)
    setItems(items.filter(i => i.id !== selectedItem.id));
    setSelectedItem(null);
    setDecision('');
    setReason('');
    setCorrectedValue('');
  };

  return (
    <div style={{ display: 'flex', gap: '24px', height: 'calc(100vh - 100px)' }}>
      {/* Queue List */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="page-header">
          <h2>Reviewer Queue</h2>
          <p>Resolve low-confidence extractions and semantic ambiguities</p>
        </div>
        
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {items.map(item => (
            <div 
              key={item.id} 
              className="card" 
              style={{ 
                cursor: 'pointer', padding: '16px',
                borderColor: selectedItem?.id === item.id ? 'var(--accent-primary)' : 'var(--border)',
                borderLeft: `4px solid ${item.status === 'escalated' ? 'var(--danger)' : 'var(--warning)'}`
              }}
              onClick={() => { setSelectedItem(item); setCorrectedValue(item.extracted_value); setReason(''); setDecision(''); }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{item.tender_name}</span>
                {item.status === 'escalated' ? (
                  <span className="badge fail"><ShieldAlert size={10} /> Escalated</span>
                ) : (
                  <span className="badge review">Pending</span>
                )}
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '4px' }}>{item.bidder_name}</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{item.criterion_id}: {item.criterion_text}</p>
            </div>
          ))}
          {items.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              <CheckCircle size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
              <p>Queue is empty.</p>
            </div>
          )}
        </div>
      </div>

      {/* Decision Panel */}
      {selectedItem && (
        <div className="card" style={{ width: '450px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
            Resolve Flag
          </h3>
          
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '12px', color: 'var(--danger)', fontWeight: 600, marginBottom: '8px', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <AlertTriangle size={14} style={{ marginTop: '2px' }} />
              {selectedItem.flag_reason}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Extracted Value (Confidence: {(selectedItem.confidence * 100).toFixed(0)}%)</label>
            <div style={{ 
              padding: '12px', background: 'var(--bg-input)', border: '1px solid var(--border)', 
              borderRadius: 'var(--radius-md)', fontSize: '14px', fontFamily: 'var(--font-mono)' 
            }}>
              {selectedItem.extracted_value}
            </div>
          </div>

          {selectedItem.image_url && (
            <div style={{ marginBottom: '20px' }}>
              <label className="form-label">Source Document Crop</label>
              <div style={{ 
                height: '100px', background: '#e2e8f0', borderRadius: 'var(--radius-md)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b'
              }}>
                [Image Crop Displayed Here]
              </div>
            </div>
          )}

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '20px', marginTop: 'auto' }}>
            <div className="form-group">
              <label className="form-label">Decision Action</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <button 
                  className={`btn ${decision === 'approve' ? 'btn-primary' : 'btn-secondary'}`} 
                  onClick={() => setDecision('approve')}
                >
                  <Check size={16} /> Approve As-Is
                </button>
                <button 
                  className={`btn ${decision === 'override' ? 'btn-primary' : 'btn-secondary'}`} 
                  onClick={() => setDecision('override')}
                >
                  <Edit3 size={16} /> Override Value
                </button>
                <button 
                  className={`btn ${decision === 'reject' ? 'btn-danger' : 'btn-secondary'}`} 
                  onClick={() => setDecision('reject')}
                >
                  <X size={16} /> Reject (Fail)
                </button>
                <button 
                  className={`btn ${decision === 'escalate' ? 'btn-secondary' : 'btn-secondary'}`} 
                  onClick={() => setDecision('escalate')}
                  style={{ borderColor: decision === 'escalate' ? 'var(--warning)' : '' }}
                >
                  <ArrowUpRight size={16} /> Escalate
                </button>
              </div>
            </div>

            {decision === 'override' && (
              <div className="form-group">
                <label className="form-label">Corrected Value (Will feed OCR/Gemini retraining)</label>
                <input 
                  type="text" className="form-input" 
                  value={correctedValue} onChange={e => setCorrectedValue(e.target.value)} 
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Reason (Mandatory) *</label>
              <textarea 
                className="form-textarea" style={{ minHeight: '80px' }}
                placeholder="Explain why you made this decision..."
                value={reason} onChange={e => setReason(e.target.value)}
              />
            </div>

            <button 
              className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleDecide} disabled={!decision || !reason.trim()}
            >
              Submit Decision
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
