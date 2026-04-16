import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// Response interceptor - catch network errors and transform to user-friendly messages
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      // Network error - backend not reachable
      const networkError = new Error(
        'Unable to connect to the backend server. Please ensure the API server is running on http://localhost:8000'
      );
      networkError.isNetworkError = true;
      return Promise.reject(networkError);
    }

    const { status, data } = error.response;

    switch (status) {
      case 400:
        return Promise.reject(new Error(data?.detail || 'Invalid request. Please check your input.'));
      case 401:
        return Promise.reject(new Error('Authentication failed. Please check your credentials in Settings.'));
      case 403:
        return Promise.reject(new Error('Access denied. Insufficient permissions to perform this action.'));
      case 404:
        return Promise.reject(new Error('The requested resource was not found.'));
      case 422:
        return Promise.reject(new Error(data?.detail || 'Validation error. Please check your configuration.'));
      case 500:
        return Promise.reject(new Error(data?.detail || 'Internal server error. Please try again later.'));
      case 503:
        return Promise.reject(new Error('Service unavailable. The backend service is temporarily down.'));
      default:
        return Promise.reject(new Error(data?.detail || `Request failed with status ${status}.`));
    }
  }
);

// Configuration endpoints
export const getConfig = () =>
  apiClient.get('/api/config').then((res) => res.data);

export const saveConfig = (data) =>
  apiClient.post('/api/config', data).then((res) => res.data);

export const deleteConfig = () =>
  apiClient.delete('/api/config').then((res) => res.data);

// Azure Advisor endpoints
export const getAdvisorRecommendations = (category = null) => {
  const params = category && category !== 'All' ? { category } : {};
  return apiClient.get('/api/advisor/recommendations', { params }).then((res) => res.data);
};

export const getAdvisorSummary = () =>
  apiClient.get('/api/advisor/summary').then((res) => res.data);

// Cost Analysis endpoints
export const getCostSummary = (days = 30) =>
  apiClient.get('/api/costs/summary', { params: { days } }).then((res) => res.data);

export const getCostBreakdown = () =>
  apiClient.get('/api/costs/breakdown').then((res) => res.data);

// M365 Licensing endpoints
export const getM365Licenses = () =>
  apiClient.get('/api/m365/licenses').then((res) => res.data);

export const getM365Usage = () =>
  apiClient.get('/api/m365/usage').then((res) => res.data);

export const getM365Summary = () =>
  apiClient.get('/api/m365/summary').then((res) => res.data);

// AI Analysis endpoints
export const analyzeAzure = () =>
  apiClient.post('/api/analyze/azure').then((res) => res.data);

export const analyzeM365 = () =>
  apiClient.post('/api/analyze/m365').then((res) => res.data);

export const analyzeAll = () =>
  apiClient.post('/api/analyze/full').then((res) => res.data);

// Health check
export const healthCheck = () =>
  apiClient.get('/health').then((res) => res.data);

export default apiClient;
