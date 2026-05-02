import React from 'react';
import { RefreshCw, BrainCircuit, ScanText } from 'lucide-react';

export default function Feedback() {
  const stats = {
    totalOverrides: 124,
    ocrCorrections: 82,
    semanticMismatches: 42,
    ocrRetrainThreshold: 200,
    promptUpdateThreshold: 50,
  };

  return (
    <div>
      <div className="page-header">
        <h2>Feedback Loop & Retraining</h2>
        <p>Reviewer corrections automatically feed model retraining pipelines</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* OCR Retraining Status */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'var(--info-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ScanText size={20} color="var(--info)" />
              </div>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Local OCR Model</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>PaddleOCR v3 Fine-tuning</p>
              </div>
            </div>
            <span className="badge pass">Active</span>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '8px' }}>
              <span>Corrections collected: <strong style={{ color: 'var(--text-primary)' }}>{stats.ocrCorrections}</strong></span>
              <span style={{ color: 'var(--text-muted)' }}>Target: {stats.ocrRetrainThreshold}</span>
            </div>
            <div className="score-bar">
              <div className="score-bar-fill high" style={{ width: `${(stats.ocrCorrections / stats.ocrRetrainThreshold) * 100}%` }} />
            </div>
          </div>

          <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center' }} disabled={stats.ocrCorrections < stats.ocrRetrainThreshold}>
            <RefreshCw size={16} /> Trigger Retraining Job
          </button>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '12px' }}>
            Retraining fires automatically when threshold is met during nightly job.
          </p>
        </div>

        {/* Gemini Few-Shot Status */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <BrainCircuit size={20} color="var(--accent-primary)" />
              </div>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Gemini Semantic Matcher</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Few-shot prompt pool update</p>
              </div>
            </div>
            <span className="badge pass">Active</span>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '8px' }}>
              <span>Mismatches collected: <strong style={{ color: 'var(--text-primary)' }}>{stats.semanticMismatches}</strong></span>
              <span style={{ color: 'var(--text-muted)' }}>Target: {stats.promptUpdateThreshold}</span>
            </div>
            <div className="score-bar">
              <div className="score-bar-fill mid" style={{ width: `${(stats.semanticMismatches / stats.promptUpdateThreshold) * 100}%` }} />
            </div>
          </div>

          <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center' }} disabled={stats.semanticMismatches < stats.promptUpdateThreshold}>
            <RefreshCw size={16} /> Update Prompt Pool
          </button>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '12px' }}>
            Updates the extract_v2.py few-shot examples automatically.
          </p>
        </div>
      </div>
    </div>
  );
}
