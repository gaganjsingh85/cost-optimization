import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  DollarSign,
  TrendingDown,
  Users,
  Sparkles,
  Play,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import SavingsCard from '../components/SavingsCard';
import RecommendationCard from '../components/RecommendationCard';
import LoadingSpinner from '../components/LoadingSpinner';
import DataStatusBanner from '../components/DataStatusBanner';
import {
  getCostSummary,
  getAdvisorRecommendations,
  getM365Summary,
  analyzeAll,
} from '../api/client';

function formatCurrency(value) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
        <p className="text-gray-300 text-xs mb-1">{label}</p>
        <p className="text-blue-400 font-semibold text-sm">
          {formatCurrency(payload[0]?.value)}
        </p>
      </div>
    );
  }
  return null;
};

function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);

  const [costData, setCostData] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [advisorAll, setAdvisorAll] = useState([]);
  const [advisorMeta, setAdvisorMeta] = useState(null);
  const [m365Summary, setM365Summary] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);

  const loadData = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    setError(null);

    try {
      const opts = forceRefresh ? { forceRefresh: true } : undefined;
      const [costRes, advisorRes, m365Res] = await Promise.allSettled([
        getCostSummary(30, opts),
        getAdvisorRecommendations(undefined, opts),
        getM365Summary(opts),
      ]);

      if (costRes.status === 'fulfilled') setCostData(costRes.value);

      if (advisorRes.status === 'fulfilled') {
        const payload = advisorRes.value || {};
        const recs = payload.recommendations || [];
        setAdvisorAll(recs);
        setAdvisorMeta({
          data_status: payload.data_status,
          error: payload.error,
          error_class: payload.error_class,
        });
        const sorted = [...recs].sort((a, b) => {
          const order = { High: 0, Medium: 1, Low: 2 };
          return (order[a.impact] ?? 3) - (order[b.impact] ?? 3);
        });
        setRecommendations(sorted.slice(0, 5));
      }

      if (m365Res.status === 'fulfilled') setM365Summary(m365Res.value);

      const anyNetworkFailed = [costRes, advisorRes, m365Res].some(
        (r) => r.status === 'rejected' && r.reason?.isNetworkError
      );
      if (anyNetworkFailed) {
        setError('Some data could not be loaded. Is the backend running?');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunAnalysis = async () => {
    setAnalyzing(true);
    try {
      const result = await analyzeAll();
      setAnalysisResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // KPIs
  const totalAzureSpend = costData?.total_cost ?? null;

  // Azure savings = annual savings from Advisor / 12
  const potentialAzureSavings = useMemo(() => {
    if (!advisorAll || advisorAll.length === 0) return null;
    const annualTotal = advisorAll.reduce(
      (sum, r) => sum + (r.potential_annual_savings || 0),
      0
    );
    return annualTotal > 0 ? annualTotal / 12 : 0;
  }, [advisorAll]);

  const m365MonthlySpend = m365Summary?.total_monthly_spend_estimate ?? null;
  const m365PotentialSavings = m365Summary?.potential_savings ?? null;

  const serviceChartData = useMemo(() => {
    const services = costData?.by_service || [];
    return services
      .slice(0, 8)
      .map((s) => ({
        name: (s.service_name || 'Unknown').replace('Microsoft.', ''),
        cost: parseFloat(s.cost || 0),
      }))
      .sort((a, b) => b.cost - a.cost);
  }, [costData]);

  const licenseRows = useMemo(() => {
    const licenses = m365Summary?.licenses || [];
    return licenses.map((lic) => {
      const purchased = lic.enabled_units ?? 0;
      const consumed = lic.consumed_units ?? 0;
      const unused = lic.unused_units ?? Math.max(0, purchased - consumed);
      const unitCost = lic.unit_cost_estimate ?? 0;
      return {
        key: lic.sku_id || lic.sku_part_number,
        name: lic.friendly_name || lic.sku_part_number || 'Unknown',
        purchased,
        active: consumed,
        unused,
        monthlyCost: consumed * unitCost,
        savingsOpp: lic.unused_cost_estimate ?? unused * unitCost,
      };
    });
  }, [m365Summary]);

  const quickWins = analysisResult?.azure?.quick_wins || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Cost Optimization Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">
            Last 30 days —{' '}
            {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={loading}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleRunAnalysis}
            disabled={analyzing || loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
          >
            {analyzing ? (
              <>
                <Sparkles className="w-4 h-4 animate-pulse" />
                Analyzing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Full Analysis
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-900/30 border border-red-700 rounded-xl px-4 py-3 text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-400 hover:text-red-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Data source banners */}
      {costData && costData.data_status && costData.data_status !== 'live' && (
        <DataStatusBanner
          dataStatus={costData.data_status}
          error={costData.error}
          errorClass={costData.error_class}
          source="azure"
        />
      )}
      {advisorMeta && advisorMeta.data_status && advisorMeta.data_status !== 'live' && (
        <DataStatusBanner
          dataStatus={advisorMeta.data_status}
          error={advisorMeta.error}
          errorClass={advisorMeta.error_class}
          source="azure"
        />
      )}
      {m365Summary && m365Summary.data_status && m365Summary.data_status !== 'live' && (
        <DataStatusBanner
          dataStatus={m365Summary.data_status}
          error={m365Summary.error}
          errorClass={m365Summary.error_class}
          source="m365"
        />
      )}

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <SavingsCard
          title="Total Azure Spend"
          value={loading ? null : formatCurrency(totalAzureSpend)}
          subtitle="Last 30 days"
          icon={DollarSign}
          color="blue"
          loading={loading}
        />
        <SavingsCard
          title="Potential Azure Savings"
          value={loading ? null : formatCurrency(potentialAzureSavings)}
          subtitle="From Advisor (monthly)"
          icon={TrendingDown}
          color="green"
          loading={loading}
        />
        <SavingsCard
          title="M365 Monthly Spend"
          value={loading ? null : formatCurrency(m365MonthlySpend)}
          subtitle="All licensed users"
          icon={Users}
          color="purple"
          loading={loading}
        />
        <SavingsCard
          title="Potential M365 Savings"
          value={loading ? null : formatCurrency(m365PotentialSavings)}
          subtitle="Unused + inactive"
          icon={TrendingDown}
          color="green"
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-xl">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold">Top Azure Advisor Recommendations</h2>
            <button
              onClick={() => navigate('/advisor')}
              className="text-blue-400 hover:text-blue-300 text-xs font-medium"
            >
              View all
            </button>
          </div>
          <div className="p-4 space-y-3">
            {loading ? (
              <LoadingSpinner message="Loading recommendations..." fullPage />
            ) : recommendations.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle2 className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No recommendations available</p>
              </div>
            ) : (
              recommendations.map((rec, idx) => (
                <RecommendationCard
                  key={rec.id || rec.name || idx}
                  recommendation={rec}
                  compact
                />
              ))
            )}
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold">Cost by Service (Last 30 Days)</h2>
            <button
              onClick={() => navigate('/costs')}
              className="text-blue-400 hover:text-blue-300 text-xs font-medium"
            >
              Full analysis
            </button>
          </div>
          <div className="p-4">
            {loading ? (
              <div className="h-64 flex items-center justify-center">
                <LoadingSpinner message="Loading cost data..." />
              </div>
            ) : serviceChartData.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <BarChart className="w-10 h-10 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No cost data available</p>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={serviceChartData}
                  margin={{ top: 5, right: 20, left: 10, bottom: 60 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    angle={-40}
                    textAnchor="end"
                    height={65}
                  />
                  <YAxis
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
                    {serviceChartData.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? '#3b82f6' : '#1d4ed8'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h2 className="text-white font-semibold">M365 License Overview</h2>
          <button
            onClick={() => navigate('/m365')}
            className="text-blue-400 hover:text-blue-300 text-xs font-medium"
          >
            Full details
          </button>
        </div>
        {loading ? (
          <div className="p-8">
            <LoadingSpinner message="Loading license data..." fullPage />
          </div>
        ) : licenseRows.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Users className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No license data available</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 font-medium px-5 py-3">License Name</th>
                  <th className="text-right text-gray-400 font-medium px-4 py-3">Purchased</th>
                  <th className="text-right text-gray-400 font-medium px-4 py-3">Used</th>
                  <th className="text-right text-gray-400 font-medium px-4 py-3">Unused</th>
                  <th className="text-right text-gray-400 font-medium px-4 py-3">Monthly Cost</th>
                  <th className="text-right text-gray-400 font-medium px-5 py-3">Savings Opp.</th>
                </tr>
              </thead>
              <tbody>
                {licenseRows.map((row, idx) => (
                  <tr
                    key={row.key || idx}
                    className="border-b border-gray-700/50 hover:bg-gray-700/30"
                  >
                    <td className="px-5 py-3 text-white font-medium">{row.name}</td>
                    <td className="px-4 py-3 text-gray-300 text-right">
                      {row.purchased.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-green-400 text-right">
                      {row.active.toLocaleString()}
                    </td>
                    <td
                      className={`px-4 py-3 text-right font-medium ${
                        row.unused > 0 ? 'text-red-400' : 'text-gray-400'
                      }`}
                    >
                      {row.unused.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-gray-300 text-right">
                      {formatCurrency(row.monthlyCost)}
                    </td>
                    <td
                      className={`px-5 py-3 text-right font-semibold ${
                        row.savingsOpp > 0 ? 'text-green-400' : 'text-gray-500'
                      }`}
                    >
                      {row.savingsOpp > 0 ? formatCurrency(row.savingsOpp) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {quickWins.length > 0 && (
        <div className="bg-gray-800 border border-green-800/50 rounded-xl">
          <div className="px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-green-400" />
              AI-Identified Quick Wins
            </h2>
          </div>
          <div className="p-5">
            <ul className="space-y-2">
              {quickWins.map((win, idx) => (
                <li key={idx} className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                  <span className="text-gray-300 text-sm">
                    {typeof win === 'string'
                      ? win
                      : win.action || win.title || JSON.stringify(win)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;