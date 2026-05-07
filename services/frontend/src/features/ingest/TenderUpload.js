import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, AlertCircle, FolderOpen, Users, Trash2, Play, Zap, BarChart3 } from 'lucide-react';
import { createTender, uploadDocuments, analyseTender, triggerEvaluation, getBiddersByTender } from '../../api';

export default function TenderUpload() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Create, 2: Upload tender PDF, 3: Upload bidders
  const [tenderTitle, setTenderTitle] = useState('');
  const [tenderDesc, setTenderDesc] = useState('');
  const [tenderId, setTenderId] = useState(null);
  const [tenderFiles, setTenderFiles] = useState([]);
  const [bidderName, setBidderName] = useState('');
  const [bidderFiles, setBidderFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [evalStage, setEvalStage] = useState('');
  const [uploadStage, setUploadStage] = useState('');
  const [messages, setMessages] = useState([]);
  const [uploadedBidders, setUploadedBidders] = useState([]);

  useEffect(() => {
    if (tenderId && step === 3) fetchBidders();
  }, [tenderId, step]);

  const fetchBidders = async () => {
    try {
      const res = await getBiddersByTender(tenderId);
      if (res.data && res.data.bidders) setUploadedBidders(res.data.bidders);
    } catch (err) {
      console.warn('Could not fetch bidders:', err.message);
    }
  };

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
      const file = tenderFiles.length > 0 ? tenderFiles[0] : null;
      const res = await analyseTender(tenderId, file);
      addMessage('success', `Extracted ${res.data.criteria_count} criteria from tender PDF`);
      setStep(3);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      addMessage('error', `Analysis failed: ${detail}`);
    } finally {
      setUploading(false);
    }
  };

  const handleBidderUpload = async () => {
    if (!bidderName.trim() || bidderFiles.length === 0) return;
    try {
      setUploading(true);
      setUploadStage('Validating documents...');
      await new Promise(r => setTimeout(r, 400));

      setUploadStage(`Uploading ${bidderFiles.length} file(s) to secure storage...`);
      const formData = new FormData();
      formData.append('tender_id', tenderId);
      formData.append('bidder_name', bidderName);
      bidderFiles.forEach(f => formData.append('files', f));
      const res = await uploadDocuments(formData);

      setUploadStage('Computing SHA-256 hashes...');
      await new Promise(r => setTimeout(r, 300));
      setUploadStage('Done!');
      await new Promise(r => setTimeout(r, 400));

      addMessage('success', `Uploaded ${res.data.files.length} files for "${bidderName}"`);

      setUploadedBidders(prev => [...prev, {
        id: res.data.bidder_id,
        name: bidderName,
        files_count: res.data.files.length,
        status: 'pending',
      }]);

      setBidderName('');
      setBidderFiles([]);
      const fileInput = document.getElementById('bidder-files');
      const folderInput = document.getElementById('bidder-folder');
      if (fileInput) fileInput.value = '';
      if (folderInput) folderInput.value = '';
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      addMessage('error', `Upload failed: ${detail}`);
    } finally {
      setUploading(false);
      setUploadStage('');
    }
  };

  const handleEvaluateAll = async () => {
    if (!tenderId || uploadedBidders.length === 0) return;
    try {
      setEvaluating(true);
      setEvalStage('Parsing bidder documents...');
      await new Promise(r => setTimeout(r, 800));
      setEvalStage('Running criterion matching...');
      await new Promise(r => setTimeout(r, 600));
      setEvalStage('Scoring & ranking bidders...');

      const res = await triggerEvaluation(tenderId);

      setEvalStage('Generating rationales...');
      await new Promise(r => setTimeout(r, 600));
      setEvalStage('Done!');
      await new Promise(r => setTimeout(r, 500));

      addMessage('success', `Evaluation complete — ${res.data.eligible_count} eligible, ${res.data.disqualified_count} disqualified.`);

      // Redirect to the ranking page
      navigate(`/ranking?tender_id=${tenderId}`);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      addMessage('error', `Evaluation failed: ${detail}`);
    } finally {
      setEvaluating(false);
      setEvalStage('');
    }
  };

  const addMessage = (type, text) => {
    setMessages(prev => [{ type, text, id: Date.now() }, ...prev].slice(0, 8));
  };

  const onDrop = useCallback((e, setter) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer?.files || e.target?.files || []);
    setter(prev => {
      const existingKeys = new Set(prev.map(f => `${f.name}_${f.size}`));
      return [...prev, ...files.filter(f => !existingKeys.has(`${f.name}_${f.size}`))];
    });
  }, []);

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    setBidderFiles(prev => {
      const existingKeys = new Set(prev.map(f => `${f.name}_${f.size}`));
      return [...prev, ...files.filter(f => !existingKeys.has(`${f.name}_${f.size}`))];
    });
  };

  const handleFolderSelect = (e) => {
    const files = Array.from(e.target.files || []);
    setBidderFiles(prev => {
      const existingKeys = new Set(prev.map(f => `${f.name}_${f.size}`));
      return [...prev, ...files.filter(f => !existingKeys.has(`${f.name}_${f.size}`))];
    });
  };

  const removeFile = (index) => setBidderFiles(prev => prev.filter((_, i) => i !== index));

  const UPLOAD_STAGES = [
    'Validating documents...',
    `Uploading ${bidderFiles.length} file(s) to secure storage...`,
    'Computing SHA-256 hashes...',
    'Done!',
  ];

  const EVAL_STAGES = [
    'Parsing bidder documents...',
    'Running criterion matching...',
    'Scoring & ranking bidders...',
    'Generating rationales...',
    'Done!',
  ];

  return (
    <div>
      {/* ── Full-Screen Upload Overlay ── */}
      {uploading && uploadStage && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: 'rgba(10, 14, 26, 0.96)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: '32px',
        }}>
          <div style={{ position: 'relative', width: '80px', height: '80px' }}>
            <div style={{
              position: 'absolute', inset: 0,
              border: '3px solid transparent',
              borderTopColor: '#22c55e',
              borderRightColor: 'rgba(34,197,94,0.3)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }} />
            <div style={{
              position: 'absolute', inset: '12px',
              border: '3px solid transparent',
              borderTopColor: '#4ade80',
              borderLeftColor: 'rgba(74,222,128,0.3)',
              borderRadius: '50%',
              animation: 'spin 0.6s linear infinite reverse',
            }} />
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Upload size={24} color="#22c55e" />
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px' }}>
              Uploading Bidder Documents
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
              Securely storing files in encrypted object storage...
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start', minWidth: '300px' }}>
              {UPLOAD_STAGES.map((stage, i) => {
                const currentIdx = UPLOAD_STAGES.indexOf(uploadStage);
                const isDone = i < currentIdx;
                const isActive = i === currentIdx;
                return (
                  <div key={stage} style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    opacity: i > currentIdx ? 0.3 : 1,
                    transition: 'opacity 0.4s ease',
                  }}>
                    <div style={{
                      width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0,
                      background: isDone ? 'var(--success)' : isActive ? '#22c55e' : 'var(--bg-elevated)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'background 0.4s ease',
                      boxShadow: isActive ? '0 0 12px rgba(34,197,94,0.4)' : 'none',
                    }}>
                      {isDone
                        ? <CheckCircle size={12} color="white" />
                        : isActive
                          ? <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'white' }} />
                          : null}
                    </div>
                    <span style={{
                      fontSize: '13px', fontWeight: isActive ? 600 : 400,
                      color: isDone ? 'var(--success)' : isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                    }}>
                      {stage}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Files are deduplicated by SHA-256 hash
          </p>
        </div>
      )}

      {/* ── Full-Screen Evaluating Overlay ── */}
      {evaluating && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: 'rgba(10, 14, 26, 0.96)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: '32px',
        }}>
          <div style={{ position: 'relative', width: '80px', height: '80px' }}>
            <div style={{
              position: 'absolute', inset: 0,
              border: '3px solid transparent',
              borderTopColor: 'var(--accent-primary)',
              borderRightColor: 'rgba(99,102,241,0.3)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }} />
            <div style={{
              position: 'absolute', inset: '12px',
              border: '3px solid transparent',
              borderTopColor: '#8b5cf6',
              borderLeftColor: 'rgba(139,92,246,0.3)',
              borderRadius: '50%',
              animation: 'spin 0.6s linear infinite reverse',
            }} />
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <BarChart3 size={24} color="var(--accent-primary)" />
            </div>
          </div>

          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px' }}>
              Analysing Bidders
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
              Running the TenderLens evaluation pipeline...
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start', minWidth: '280px' }}>
              {EVAL_STAGES.map((stage, i) => {
                const currentIdx = EVAL_STAGES.indexOf(evalStage);
                const isDone = i < currentIdx;
                const isActive = i === currentIdx;
                return (
                  <div key={stage} style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    opacity: i > currentIdx ? 0.3 : 1,
                    transition: 'opacity 0.4s ease',
                  }}>
                    <div style={{
                      width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0,
                      background: isDone ? 'var(--success)' : isActive ? 'var(--accent-primary)' : 'var(--bg-elevated)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'background 0.4s ease',
                      boxShadow: isActive ? '0 0 12px var(--accent-glow)' : 'none',
                    }}>
                      {isDone
                        ? <CheckCircle size={12} color="white" />
                        : isActive
                          ? <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'white' }} />
                          : null}
                    </div>
                    <span style={{
                      fontSize: '13px', fontWeight: isActive ? 600 : 400,
                      color: isDone ? 'var(--success)' : isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                    }}>
                      {stage}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            This may take 1–3 minutes depending on document size
          </p>
        </div>
      )}

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
            border: `1px solid ${step === i + 1 ? 'var(--accent-primary)' : step > i + 1 ? 'rgba(34,197,94,0.2)' : 'var(--border)'}`,
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
              value={tenderTitle} onChange={e => setTenderTitle(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreateTender()} />
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
          {tenderFiles.length === 0 && (
            <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--danger)', fontStyle: 'italic' }}>
              ⚠ Please select a tender PDF document before proceeding
            </div>
          )}
          <button className="btn btn-primary" style={{ marginTop: '20px' }}
            onClick={handleAnalyse} disabled={uploading || tenderFiles.length === 0}>
            {uploading ? 'Analysing...' : 'Upload & Extract Criteria'}
          </button>
        </div>
      )}

      {/* Step 3: Upload Bidder Documents */}
      {step === 3 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', alignItems: 'start' }}>
          {/* Left: Upload Form */}
          <div className="card">
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '20px' }}>Add Bidder Documents</h3>
            <div className="form-group">
              <label className="form-label">Bidder / Company Name *</label>
              <input className="form-input" placeholder="e.g. M/s Sharma Construction Pvt Ltd"
                value={bidderName} onChange={e => setBidderName(e.target.value)} />
            </div>

            <div className="upload-zone" onDrop={e => { e.preventDefault(); handleFileSelect(e); }}
              onDragOver={e => e.preventDefault()} onClick={() => document.getElementById('bidder-files').click()}>
              <div className="upload-icon">📁</div>
              <p><strong>Drop bidder documents here</strong> or click to browse</p>
              <p style={{ fontSize: '12px', marginTop: '8px' }}>PDF, JPEG, PNG, DOCX — up to 50 files</p>
              <input id="bidder-files" type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.docx"
                style={{ display: 'none' }} onChange={handleFileSelect} />
            </div>

            <div style={{ marginTop: '12px', display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button className="btn btn-secondary" onClick={() => document.getElementById('bidder-folder').click()}
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FolderOpen size={16} /> Upload Entire Folder
              </button>
              <input id="bidder-folder" type="file" webkitdirectory="true" directory=""
                style={{ display: 'none' }} onChange={handleFolderSelect} />
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Uploads all files from a folder
              </span>
            </div>

            {bidderFiles.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-secondary)' }}>
                  {bidderFiles.length} file(s) selected:
                </div>
                <div style={{ maxHeight: '160px', overflowY: 'auto', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)', background: 'var(--bg-elevated)' }}>
                  {bidderFiles.map((f, i) => (
                    <div key={`${f.name}_${i}`} style={{
                      padding: '6px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      borderBottom: i < bidderFiles.length - 1 ? '1px solid var(--border)' : 'none',
                      fontSize: '12px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                        <FileText size={12} color="var(--text-muted)" />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
                        <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>({(f.size / 1024).toFixed(0)} KB)</span>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', color: 'var(--danger)' }}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', marginTop: '20px', alignItems: 'center' }}>
              <button className="btn btn-primary" onClick={handleBidderUpload}
                disabled={uploading || !bidderName.trim() || bidderFiles.length === 0}>
                {uploading ? 'Uploading...' : 'Upload Bidder Bundle'}
              </button>
              {!bidderName.trim() && bidderFiles.length > 0 && (
                <span style={{ fontSize: '12px', color: 'var(--danger)', fontStyle: 'italic' }}>
                  ⚠ Enter a bidder name above to enable upload
                </span>
              )}
            </div>
          </div>

          {/* Right: Uploaded Bidders List */}
          <div>
            <div className="card" style={{ marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Users size={18} color="var(--accent-primary)" />
                Uploaded Bidders ({uploadedBidders.length})
              </h3>

              {uploadedBidders.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>
                  <Users size={32} style={{ opacity: 0.3, marginBottom: '12px' }} />
                  <p style={{ fontSize: '13px' }}>No bidders uploaded yet.</p>
                  <p style={{ fontSize: '12px', marginTop: '4px' }}>Use the form on the left to add bidder documents.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {uploadedBidders.map((bidder, i) => (
                    <div key={bidder.id || i} style={{
                      padding: '12px 16px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-elevated)',
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    }}>
                      <div>
                        <div style={{ fontSize: '14px', fontWeight: 600 }}>{bidder.name}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {bidder.files_count} file(s) • ID: {bidder.id?.substring(0, 8)}...
                        </div>
                      </div>
                      <span className={`badge ${bidder.status === 'parsed' ? 'pass' : bidder.status === 'parsing' ? 'review' : 'draft'}`}
                        style={{ fontSize: '10px' }}>
                        {bidder.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Evaluate Button */}
            {uploadedBidders.length >= 1 && (
              <div className="card" style={{
                background: 'var(--accent-glow)', border: '1px solid var(--border-accent)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <Zap size={18} color="var(--accent-primary)" />
                  <h4 style={{ fontSize: '14px', fontWeight: 700 }}>Ready to Evaluate?</h4>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                  {uploadedBidders.length} bidder(s) uploaded. Click below to compare all bidders
                  against the tender criteria and generate an auditable ranking report.
                </p>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button
                    id="evaluate-all-btn"
                    className="btn btn-primary"
                    onClick={handleEvaluateAll}
                    disabled={evaluating || uploading}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Play size={16} />
                    {evaluating ? 'Evaluating…' : 'Evaluate All Bidders'}
                  </button>
                  <button className="btn btn-secondary"
                    onClick={() => navigate(`/ranking?tender_id=${tenderId}`)}>
                    View Rankings →
                  </button>
                </div>
              </div>
            )}
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
