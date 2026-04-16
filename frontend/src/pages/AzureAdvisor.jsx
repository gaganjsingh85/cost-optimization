import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Search, AlertCircle, Lightbulb, RefreshCw, Filter } from 'lucide-react';
import RecommendationCard from '../components/RecommendationCard';
import LoadingSpinner from '../components/LoadingSpinner';
import DataStatusBanner from '../components/DataStatusBanner';
import { getAdvisorRecommendations } from '../api/client';

const CATEGORIES = [
  'All',
  'Cost',
  'Security',
  'HighAvailability',
  'Performance',
  'OperationalExcellence',
];
const CATEGORY_LABELS = {
  All: 'All',
  Cost: 'Cost',
  Security: 'Security',
  HighAvailability: 'High Availability',
  Performance: 'Performance',
  OperationalExcellence: 'Operational Excellence',
};
const IMPACTS = ['All', 'High', 'Medium', 'Low'];

function formatCurrency(value) {
  if (!value && value !== 0) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function AzureAdvisor() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [meta, setMeta] = useState(null);

  const [activeCategory, setActiveCategory] = useState('All');
  const [activeImpact, setActiveImpact] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const loadData = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const opts = forceRefresh ? { forceRefresh: true } : undefined;
      const payload = await getAdvisorRecommendations(undefined, opts);
      const recs = payload?.recommendations || [];
      const sorted = [...recs].sort((a, b) => {
        const order = { High: 0, Medium: 1, Low: 2 };
        return (order[a.impact] ?? 3) - (order[b.impact] ?? 3);
      });
      setRecommendations(sorted);
      setMeta({
        data_status: payload?.data_status,
        error: payload?.error,
        error_class: payload?.error_class,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredRecommendations = useMemo(() => {
    return recommendations.filter((rec) => {
      if (activeCategory !== 'All' && rec.category !== activeCategory) return false;
      if (activeImpact !== 'All' && rec.impact !== activeImpact) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const problem = (rec.short_description?.problem || rec.short_description || '')
          .toString()
          .toLowerCase();
        const resource = (rec.impacted_value || '').toLowerCase();
        if (!problem.includes(q) && !resource.includes(q)) return false;
      }
      return true;
    });
  }, [recommendations, activeCategory, activeImpact, searchQuery]);

  const stats = useMemo(() => {
    const total = recommendations.length;
    const high = recommendations.filter((r) => r.impact === 'High').length;
    const totalSavings = recommendations.reduce((sum, r) => {
      const annual = r.potential_annual_savings || 0;
      return sum + annual / 12;
    }, 0);
    return { total, high, totalSavings };
  }, [recommendations]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Azure Advisor Recommendations</h1>
          <p className="text-gray-400 text-sm mt-1">
            AI-powered best practice recommendations from Azure Advisor
          </p>
        </div>
        <button
          onClick={() => loadData(true)}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded-lg text-sm font-medium"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-900/30 border border-red-700 rounded-xl px-4 py-3 text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {meta && meta.data_status && meta.data_status !== 'live' && (
        <DataStatusBanner
          dataStatus={meta.data_status}
          error={meta.error}
          errorClass={meta.error_class}
          source="azure"
        />
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">
            Total Recommendations
          </p>
          <p className="text-3xl font-bold text-white">{loading ? '—' : stats.total}</p>
        </div>
        <div className="bg-gray-800 border border-red-800/40 rounded-xl p-4">
          <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">High Impact</p>
          <p className="text-3xl font-bold text-red-400">{loading ? '—' : stats.high}</p>
        </div>
        <div className="bg-gray-800 border border-green-800/40 rounded-xl p-4">
          <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">
            Total Monthly Savings
          </p>
          <p className="text-3xl font-bold text-green-400">
            {loading ? '—' : formatCurrency(stats.totalSavings)}
          </p>
        </div>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-4">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5" />
            Category
          </p>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  activeCategory === cat
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white'
                }`}
              >
                {CATEGORY_LABELS[cat]}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Impact</p>
            <div className="flex gap-2">
              {IMPACTS.map((imp) => {
                const selected = activeImpact === imp;
                const colors = {
                  All: selected
                    ? 'bg-gray-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
                  High: selected
                    ? 'bg-red-700 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
                  Medium: selected
                    ? 'bg-yellow-700 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
                  Low: selected
                    ? 'bg-green-700 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
                };
                return (
                  <button
                    key={imp}
                    onClick={() => setActiveImpact(imp)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${colors[imp]}`}
                  >
                    {imp}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex-1">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Search</p>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search recommendations or resources..."
                className="w-full bg-gray-700 border border-gray-600 rounded-lg pl-9 pr-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {(activeCategory !== 'All' || activeImpact !== 'All' || searchQuery) && (
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-xs">
              Showing {filteredRecommendations.length} of {recommendations.length} recommendations
            </span>
            <button
              onClick={() => {
                setActiveCategory('All');
                setActiveImpact('All');
                setSearchQuery('');
              }}
              className="text-blue-400 hover:text-blue-300 text-xs underline"
            >
              Clear filters
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingSpinner message="Loading recommendations..." fullPage />
      ) : filteredRecommendations.length === 0 ? (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center">
          <Lightbulb className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400 font-medium">No recommendations match your filters</p>
          <p className="text-gray-500 text-sm mt-1">
            {recommendations.length === 0
              ? 'No Azure Advisor recommendations available.'
              : 'Try adjusting your category, impact, or search filters.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filteredRecommendations.map((rec, idx) => (
            <RecommendationCard key={rec.id || idx} recommendation={rec} />
          ))}
        </div>
      )}
    </div>
  );
}

export default AzureAdvisor;