/**
 * API client for the Azure Cost Optimizer backend.
 *
 * If you already have an api/client.js, ADD the new helpers at the bottom
 * (getSubscriptionInfo, sendChatMessage) and make sure getConfig now expects
 * the plaintext-non-secret response shape.
 */

const API_BASE =
  import.meta.env?.VITE_API_BASE || process.env.REACT_APP_API_BASE || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, { status = 0, isNetworkError = false } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.isNetworkError = isNetworkError;
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    throw new ApiError(
      'Unable to reach the backend. Is it running on ' + API_BASE + '?',
      { isNetworkError: true }
    );
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const data = await response.json();
      detail = data.detail || data.message || detail;
    } catch {
      // ignore
    }
    throw new ApiError(detail, { status: response.status });
  }

  if (response.status === 204) return null;
  return response.json();
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
export const getConfig = () => request('/api/config/');
export const getConfigStatus = () => request('/api/config/status');
export const saveConfig = (payload) => request('/api/config/', { method: 'POST', body: payload });
export const deleteConfig = () => request('/api/config/', { method: 'DELETE' });

// ---------------------------------------------------------------------------
// Azure
// ---------------------------------------------------------------------------
export const getSubscriptionInfo = () => request('/api/azure/subscription');
export const getCostSummary = (days = 30) => request(`/api/costs/summary?days=${days}`);
export const getCostBreakdown = (days = 30) => request(`/api/costs/breakdown?days=${days}`);
export const getAdvisorRecommendations = (category) =>
  request('/api/advisor/recommendations' + (category ? `?category=${category}` : ''));
export const getAdvisorSummary = () => request('/api/advisor/summary');

// ---------------------------------------------------------------------------
// M365
// ---------------------------------------------------------------------------
export const getM365Licenses = () => request('/api/m365/licenses');
export const getM365Usage = () => request('/api/m365/usage');
export const getM365Summary = () => request('/api/m365/summary');

// ---------------------------------------------------------------------------
// AI Analysis
// ---------------------------------------------------------------------------
export const analyzeAzure = () => request('/api/analyze/azure', { method: 'POST', body: {} });
export const analyzeM365 = () => request('/api/analyze/m365', { method: 'POST', body: {} });
export const analyzeAll = () => request('/api/analyze/full', { method: 'POST', body: {} });

// ---------------------------------------------------------------------------
// Chat agent
// ---------------------------------------------------------------------------
export const sendChatMessage = (message, history = []) =>
  request('/api/chat/', { method: 'POST', body: { message, history } });

export { ApiError };