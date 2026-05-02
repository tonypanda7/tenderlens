import React, { useState, useCallback } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { createTender, uploadDocuments, analyseTender } from '../../api';

export default function TenderUpload() {
  const [step, setStep] = useState(1); // 1: Create, 2: Upload tender PDF, 3: Upload bidders
  const [tenderTitle, setTenderTitle] = useState('');
  const [tenderDesc, setTenderDesc] = useState('');
  const [tenderId, setTenderId] = useState(null);
  const [tenderFiles, setTenderFiles] = useState([]);
  const [bidderName, setBidderName] = useState('');
  const [bidderFiles, setBidderFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [messages, setMessages] = useState([]);

  const handleCreateTender = async () => {
    if (!tenderTitle.trim()) return;
    try {
      const res = await createTender({ title: tenderTitle, description: tenderDesc });
      setTenderId(res.data.id);
      addMessage('success', `Tender created: ${res.data.id}`);
      setStep(2);
    } catch (err) {
      addMessage('error', `Failed to create tender: ${err.message}`);
    }
  };

  const handleAnalyse = async () => {
    if (!tenderId) return;
    try {
      setUploading(true);
      const res = await analyseTender(tenderId);
      addMessage('success', `Extracted ${res.data.criteria_count} criteria from tender PDF`);
      setStep(3);
    } catch (err) {
      addMessage('error', `Analysis failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleBidderUpload = async () => {
    if (!bidderName.trim() || bidderFiles.length === 0) return;
    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('tender_id', tenderId);
      formData.append('bidder_name', bidderName);
      bidderFiles.forEach(f => formData.append('files', f));
      const res = await uploadDocuments(formData);
      addMessage('success', `Uploaded ${res.data.files.length} files for ${bidderName}`);
      setBidderName('');
      setBidderFiles([]);
    } catch (err) {
      addMessage('error', `Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const addMessage = (type, text) => {
    setMessages(prev => [{ type, text, id: Date.now() }, ...prev].slice(0, 5));
  };

  const onDrop = useCallback((e, setter) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer?.files || e.target?.files || []);
    setter(files);
  }, []);

  return (
    <div>
      <div className="page-header">
        <h2>Upload Documents</h2>
        <p>Upload tender PDF and bidder submission bundles</p>
      </div>

      {/* Progress Steps */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '32px' }}>
        {['Create Tender', 'Upload & Analyse', 'Add Bidders'].map((label, i) => (
          <div key={i} style={{
            flex: 1, padding: '12px 16px', borderRadius: 'var(--radius-md)',
            background: step > i + 1 ? 'var(--success-bg)' : step === i + 1 ? 'var(--accent-glow)' : 'var(--bg-card)',
            border: `1px solid ${step === i + 1 ? 'var(--accent-primary)' : 'var(--border)'}`,
            display: 'flex', alignItems: 'center', gap: '10px',
          }}>
            <span style={{
              width: '28px', height: '28px', borderRadius: '50%', display: 'flex',
              alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 700,
              background: step > i + 1 ? 'var(--success)' : step === i + 1 ? 'var(--accent-primary)' : 'var(--bg-elevated)',
              color: 'white',
            }}>
              {step > i + 1 ? '✓' : i + 1}
            </span>
            <span style={{ fontSize: '13px', fontWeight: 600, color: step === i + 1 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
              {label}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Create Tender */}
      {step === 1 && (
        <div className="card" style={{ maxWidth: '600px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '20px' }}>Create New Tender</h3>
          <div className="form-group">
            <label className="form-label">Tender Title *</label>
            <input className="form-input" placeholder="e.g. CRPF Barracks Construction — Phase III"
              value={tenderTitle} onChange={e => setTenderTitle(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea className="form-textarea" placeholder="Brief description of the tender..."
              value={tenderDesc} onChange={e => setTenderDesc(e.target.value)} />
          </div>
          <button className="btn btn-primary" onClick={handleCreateTender} disabled={!tenderTitle.trim()}>
            Create Tender
          </button>
        </div>
      )}

      {/* Step 2: Upload Tender PDF */}
      {step === 2 && (
        <div className="card" style={{ maxWidth: '600px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '20px' }}>Upload Tender PDF</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '16px' }}>
            Tender ID: <code style={{ color: 'var(--text-accent)' }}>{tenderId}</code>
          </p>
          <div className="upload-zone" onDrop={e => onDrop(e, setTenderFiles)}
            onDragOver={e => e.preventDefault()} onClick={() => document.getElementById('tender-file').click()}>
            <div className="upload-icon">📄</div>
            <p><strong>Drop tender PDF here</strong> or click to browse</p>
            <p style={{ fontSize: '12px', marginTop: '8px' }}>PDF files only</p>
            <input id="tender-file" type="file" accept=".pdf" style={{ display: 'none' }}
              onChange={e => setTenderFiles(Array.from(e.target.files))} />
          </div>
          {tenderFiles.length > 0 && (
            <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={16} color="var(--success)" />
              <span style={{ fontSize: '13px' }}>{tenderFiles[0].name}</span>
            </div>
          )}
          <button className="btn btn-primary" style={{ marginTop: '20px' }}
            onClick={handleAnalyse} disabled={uploading}>
            {uploading ? 'Analysing...' : 'Upload & Extract Criteria'}
          </button>
        </div>
      )}

      {/* Step 3: Upload Bidder Documents */}
      {step === 3 && (
        <div className="card" style={{ maxWidth: '600px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '20px' }}>Add Bidder Documents</h3>
          <div className="form-group">
            <label className="form-label">Bidder / Company Name *</label>
            <input className="form-input" placeholder="e.g. M/s Sharma Construction Pvt Ltd"
              value={bidderName} onChange={e => setBidderName(e.target.value)} />
          </div>
          <div className="upload-zone" onDrop={e => onDrop(e, setBidderFiles)}
            onDragOver={e => e.preventDefault()} onClick={() => document.getElementById('bidder-files').click()}>
            <div className="upload-icon">📁</div>
            <p><strong>Drop bidder documents here</strong></p>
            <p style={{ fontSize: '12px', marginTop: '8px' }}>PDF, JPEG, PNG, DOCX — up to 50 files</p>
            <input id="bidder-files" type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.docx" style={{ display: 'none' }}
              onChange={e => setBidderFiles(Array.from(e.target.files))} />
          </div>
          {bidderFiles.length > 0 && (
            <div style={{ marginTop: '12px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              {bidderFiles.length} file(s) selected
            </div>
          )}
          <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
            <button className="btn btn-primary" onClick={handleBidderUpload}
              disabled={uploading || !bidderName.trim() || bidderFiles.length === 0}>
              {uploading ? 'Uploading...' : 'Upload Bidder Bundle'}
            </button>
            <button className="btn btn-secondary" onClick={() => window.location.href = '/criteria'}>
              Done — Review Criteria →
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      {messages.length > 0 && (
        <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {messages.map(msg => (
            <div key={msg.id} style={{
              padding: '10px 16px', borderRadius: 'var(--radius-md)', fontSize: '13px',
              display: 'flex', alignItems: 'center', gap: '8px',
              background: msg.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
              color: msg.type === 'success' ? 'var(--success)' : 'var(--danger)',
              border: `1px solid ${msg.type === 'success' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
            }}>
              {msg.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
              {msg.text}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
