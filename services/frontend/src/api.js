import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
});

// ── Tender endpoints ──
export const createTender = (data) => api.post('/tender/create', data);
export const getTenders = () => api.get('/tender/');
export const getTender = (id) => api.get(`/tender/${id}`);
export const analyseTender = (id, file) => {
  const formData = new FormData();
  if (file) formData.append('file', file);
  return api.post(`/tender/${id}/analyse`, formData, {
    headers: { 'Content-Type': undefined },
    timeout: 600000, // 10 minutes — Gemini extraction can be slow for large tenders
  });
};
export const lockTender = (id) => api.post(`/tender/${id}/lock`);
export const updateCriterion = (tenderId, criterionId, data) =>
  api.put(`/tender/${tenderId}/criteria/${criterionId}`, data);

// ── Ingest endpoints ──
export const uploadDocuments = (formData) =>
  api.post('/ingest/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

// ── Scoring endpoints ──
export const getTenderRanking = (id) => api.get(`/tender/${id}/ranking`);
export const triggerEvaluation = (id) => api.post(`/tender/${id}/evaluate`, {}, {
  timeout: 600000, // 10 minutes — full pipeline can be slow
});

// ── Bidder endpoints ──
export const triggerBidderParsing = (bidderId) => api.post(`/bidder/${bidderId}/parse`);
export const getBidderBlocks = (bidderId) => api.get(`/bidder/${bidderId}/blocks`);
export const getBiddersByTender = (tenderId) => api.get(`/tender/${tenderId}/bidders`);

// ── Reviewer endpoints ──
export const getReviewerQueue = (status) => api.get(`/reviewer/queue?status=${status || 'pending'}`);
export const decideQueueItem = (id, decision) => api.post(`/reviewer/${id}/decide`, decision);
export const getQueueItemDetail = (id) => api.get(`/reviewer/${id}`);

// ── Audit endpoints ──
export const getAuditLog = (tenderId) => api.get(`/audit/${tenderId}`);
export const verifyAuditChain = (tenderId) => api.get(`/audit/${tenderId}/verify`);
export const exportAuditPdf = (tenderId) => api.post(`/audit/${tenderId}/export`);

// ── Feedback endpoints ──
export const getFeedbackStats = () => api.get('/feedback/stats');

export default api;
