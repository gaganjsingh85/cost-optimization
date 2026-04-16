/**
 * API client for the Azure Cost Optimizer backend.
 *
 * Key features to prevent request storms:
 * 1. In-flight dedup: if a GET for the same URL is already pending,
 *    subsequent callers get the same Promise instead of firing a new request.
 *    This defeats React StrictMode's double-mount, useEffect double-fire, and
 *    multi-page simultaneous fetches.
 * 2. Short-lived response cache (default 30s for GETs). Navigating between
 *    pages that share data reuses the cached response instead of refetching.
 * 3. Cache can be bypassed with { forceRefresh: true } - used by refresh
 *    buttons.
 */

const API_BASE =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE) ||
  (typeof process !== 'undefined' && process.env?.REACT_APP_API_BASE) ||
  'http://localhost:8000';

const DEFAULT_CACHE_TTL_MS = 30_000; // 30s

class ApiError extends Error {
  constructor(message, { status = 0, isNetworkError = false } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.isNetworkError = isNetworkError;
  }
}

// In-flight requests keyed by "METHOD URL"
const inFlight = new Map();
// Cached responses keyed by "METHOD URL", value = { expiresAt, data }
const responseCache = new Map();

function cacheKey(method, path) {
  return `${method} ${path}`;
}

function readCache(key) {
  const entry = responseCache.get(key);
  if (!entry) return null;
  if (Date.now() >= entry.expiresAt) {
    responseCache.delete(key);
    return null;
  }
  return entry.data;
}

function writeCache(key, data, ttlMs) {
  responseCache.set(key, { expiresAt: Date.now() + ttlMs, data });
}

export function clearApiCache(prefix) {
  if (!prefix) {
    responseCache.clear();
    return;
  }
  for (const k of Array.from(responseCache.keys())) {
    if (k.includes(prefix)) responseCache.delete(k);
  }
}

async function rawRequest(method, path, body, signal) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    throw new ApiError(`Unable to reach the backend at ${API_BASE}. Is it running?`, {
      isNetworkError: true,
    });
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

/**
 * Core request function with dedup + cache.
 *
 * Options:
 *   method: 'GET' | 'POST' | 'DELETE'
 *   body: payload for POST
 *   signal: AbortSignal
 *   forceRefresh: skip cache + in-flight dedup (used by refresh buttons)
 *   cacheTtlMs: override cache TTL (GETs only, default 30s; 0 = don't cache)
 */
async function request(path, opts = {}) {
  const {
    method = 'GET',
    body,
    signal,
    forceRefresh = false,
    cacheTtlMs = DEFAULT_CACHE_TTL_MS,
  } = opts;

  // Only GETs get cache+dedup; POST/DELETE are side-effectful
  const useCache = method === 'GET' && !forceRefresh && cacheTtlMs > 0;
  const key = cacheKey(method, path);

  if (useCache) {
    const cached = readCache(key);
    if (cached !== null) {
      return cached;
    }
    const pending = inFlight.get(key);
    if (pending) {
      // Someone else is already fetching this - join them
      return pending;
    }
  }

  const promise = rawRequest(method, path, body, signal)
    .then((data) => {
      if (useCache && data !== null) {
        writeCache(key, data, cacheTtlMs);
      }
      return data;
    })
    .finally(() => {
      inFlight.delete(key);
    });

  if (method === 'GET') {
    inFlight.set(key, promise);
  }

  return promise;
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
export const getConfig = (opts) => request('/api/config/', opts);
export const getConfigStatus = (opts) => request('/api/config/status', opts);
export const saveConfig = (payload) => {
  const result = request('/api/config/', { method: 'POST', body: payload });
  // Invalidate everything on config change
  clearApiCache('');
  return result;
};
export const deleteConfig = () => {
  const result = request('/api/config/', { method: 'DELETE' });
  clearApiCache('');
  return result;
};

// ---------------------------------------------------------------------------
// Azure
// ---------------------------------------------------------------------------
export const getSubscriptionInfo = (opts) => request('/api/azure/subscription', opts);
export const getCostSummary = (days = 30, opts) =>
  request(`/api/costs/summary?days=${days}`, opts);
export const getCostBreakdown = (days = 30, opts) =>
  request(`/api/costs/breakdown?days=${days}`, opts);
export const getAdvisorRecommendations = (category, opts) =>
  request('/api/advisor/recommendations' + (category ? `?category=${category}` : ''), opts);
export const getAdvisorSummary = (opts) => request('/api/advisor/summary', opts);

// ---------------------------------------------------------------------------
// M365
// ---------------------------------------------------------------------------
export const getM365Licenses = (opts) => request('/api/m365/licenses', opts);
export const getM365Usage = (opts) => request('/api/m365/usage', opts);
export const getM365Summary = (opts) => request('/api/m365/summary', opts);

// ---------------------------------------------------------------------------
// AI Analysis (POST - never cached)
// ---------------------------------------------------------------------------
export const analyzeAzure = () => request('/api/analyze/azure', { method: 'POST', body: {} });
export const analyzeM365 = () => request('/api/analyze/m365', { method: 'POST', body: {} });
export const analyzeAll = () => request('/api/analyze/full', { method: 'POST', body: {} });

// ---------------------------------------------------------------------------
// Chat (POST - never cached)
// ---------------------------------------------------------------------------
export const sendChatMessage = (message, history = []) =>
  request('/api/chat/', { method: 'POST', body: { message, history } });

export { ApiError };