import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  defs,
  linearGradient,
} from 'recharts';
import {
  DollarSign,
  Server,
  Layers,
  AlertCircle,
  RefreshCw,
  ArrowUpDown,
} from 'lucide-react';
import SavingsCard from '../components/SavingsCard';
import LoadingSpinner from '../components/LoadingSpinner';
import { getCostSummary } from '../api/client';

const PERIODS = [
  { label: '7 Days', value: 7 },
  { label: '30 Days', value: 30 },
  { label: '90 Days', value: 90 },
];

function formatCurrency(value) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatCurrencyFull(value) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
        <p className="text-gray-400 text-xs mb-1">{label}</p>
        <p className="text-blue-400 font-semibold text-sm">
          {formatCurrency(payload[0]?.value)}
        </p>
      </div>
    );
  }
  return null;
};

const GreenTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
        <p className="text-gray-400 text-xs mb-1">{label}</p>
        <p className="text-green-400 font-semibold text-sm">
          {formatCurrency(payload[0]?.value)}
        </p>
      </div>
    );
  }
  return null;
};

function CostAnalysis() {
  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [costData, setCostData] = useState(null);
  const [sortField, setSortField] = useState('cost');
  const [sortDir, setSortDir] = useState('desc');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCostSummary(selectedPeriod);
      setCostData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedPeriod]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const dailyTrend = useMemo(() => {
    const trend = costData?.daily_costs || costData?.trend || [];
    return trend.map((item) => ({
      date: item.date || item.day || '',
      cost: parseFloat(item.cost || item.total_cost || 0),
    }));
  }, [costData]);

  const serviceData = useMemo(() => {
    const services = costData?.by_service || costData?.services || [];
    return [...services]
      .map((s) => ({
        name: (s.service_name || s.name || s.service || 'Unknown').replace('Microsoft.', '').replace('microsoft.', ''),
        cost: parseFloat(s.cost || s.total_cost || 0),
        pct: 0,
      }))
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 10);
  }, [costData]);

  const serviceDataWithPct = useMemo(() => {
    const total = serviceData.reduce((s, d) => s + d.cost, 0);
    return serviceData.map((d) => ({ ...d, pct: total > 0 ? (d.cost / total) * 100 : 0 }));
  }, [serviceData]);

  const resourceGroupData = useMemo(() => {
    const groups = costData?.by_resource_group || costData?.resource_groups || [];
    return [...groups]
      .map((g) => ({
        name: g.resource_group || g.name || g.group || 'Unknown',
        cost: parseFloat(g.cost || g.total_cost || 0),
      }))
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 10);
  }, [costData]);

  const totalCost = costData?.total_cost ?? costData?.total ?? null;
  const topService = serviceData[0]?.name || null;
  const topResourceGroup = resourceGroupData[0]?.name || null;

  const sortedTableData = useMemo(() => {
    return [...serviceDataWithPct].sort((a, b) => {
      const mult = sortDir === 'desc' ? -1 : 1;
      if (sortField === 'name') return mult * a.name.localeCompare(b.name);
      return mult * (a[sortField] - b[sortField]);
    });
  }, [serviceDataWithPct, sortField, sortDir]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Azure Cost Analysis</h1>
          <p className="text-gray-400 text-sm mt-1">
            Detailed cost breakdown and trend analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Period Selector */}
          <div className="flex bg-gray-800 border border-gray-700 rounded-lg p-1">
            {PERIODS.map(({ label, value }) => (
              <button
                key={value}
                onClick={() => setSelectedPeriod(value)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  selectedPeriod === value
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded-lg"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 bg-red-900/30 border border-red-700 rounded-xl px-4 py-3 text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SavingsCard
          title={`Total Spend (${selectedPeriod} Days)`}
          value={loading ? null : formatCurrency(totalCost)}
          icon={DollarSign}
          color="blue"
          loading={loading}
        />
        <SavingsCard
          title="Top Azure Service"
          value={loading ? null : topService || 'N/A'}
          subtitle="By spend"
          icon={Server}
          color="gray"
          loading={loading}
        />
        <SavingsCard
          title="Top Resource Group"
          value={loading ? null : topResourceGroup || 'N/A'}
          subtitle="By spend"
          icon={Layers}
          color="gray"
          loading={loading}
        />
      </div>

      {/* Daily Cost Trend */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl">
        <div className="px-5 py-4 border-b border-gray-700">
          <h2 className="text-white font-semibold">Daily Cost Trend</h2>
        </div>
        <div className="p-5">
          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <LoadingSpinner message="Loading trend data..." />
            </div>
          ) : dailyTrend.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-gray-500 text-sm">
              No daily trend data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={dailyTrend} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <defs>
                  <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="cost"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#costGradient)"
                  dot={false}
                  activeDot={{ r: 5, fill: '#3b82f6', strokeWidth: 2, stroke: '#1d4ed8' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Side-by-side charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Cost by Service */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl">
          <div className="px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold">Cost by Azure Service</h2>
          </div>
          <div className="p-5">
            {loading ? (
              <div className="h-72 flex items-center justify-center">
                <LoadingSpinner message="Loading..." />
              </div>
            ) : serviceData.length === 0 ? (
              <div className="h-72 flex items-center justify-center text-gray-500 text-sm">
                No service data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={290}>
                <BarChart
                  data={serviceData}
                  layout="vertical"
                  margin={{ top: 5, right: 60, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fill: '#d1d5db', fontSize: 11 }}
                    width={100}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="cost" radius={[0, 4, 4, 0]}>
                    {serviceData.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? '#3b82f6' : `rgba(59, 130, 246, ${Math.max(0.3, 1 - i * 0.1)})`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Cost by Resource Group */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl">
          <div className="px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold">Cost by Resource Group</h2>
          </div>
          <div className="p-5">
            {loading ? (
              <div className="h-72 flex items-center justify-center">
                <LoadingSpinner message="Loading..." />
              </div>
            ) : resourceGroupData.length === 0 ? (
              <div className="h-72 flex items-center justify-center text-gray-500 text-sm">
                No resource group data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={290}>
                <BarChart
                  data={resourceGroupData}
                  layout="vertical"
                  margin={{ top: 5, right: 60, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fill: '#d1d5db', fontSize: 11 }}
                    width={120}
                    tickLine={false}
                  />
                  <Tooltip content={<GreenTooltip />} />
                  <Bar dataKey="cost" radius={[0, 4, 4, 0]}>
                    {resourceGroupData.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? '#22c55e' : `rgba(34, 197, 94, ${Math.max(0.3, 1 - i * 0.1)})`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl">
        <div className="px-5 py-4 border-b border-gray-700">
          <h2 className="text-white font-semibold">Cost Breakdown by Service</h2>
        </div>
        {loading ? (
          <div className="p-8">
            <LoadingSpinner message="Loading breakdown..." fullPage />
          </div>
        ) : sortedTableData.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">No cost data available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left px-5 py-3">
                    <button
                      onClick={() => handleSort('name')}
                      className="flex items-center gap-1 text-gray-400 font-medium hover:text-white"
                    >
                      Service
                      <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                  <th className="text-right px-4 py-3">
                    <button
                      onClick={() => handleSort('cost')}
                      className="flex items-center gap-1 text-gray-400 font-medium hover:text-white ml-auto"
                    >
                      Cost
                      <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                  <th className="text-right px-5 py-3">
                    <button
                      onClick={() => handleSort('pct')}
                      className="flex items-center gap-1 text-gray-400 font-medium hover:text-white ml-auto"
                    >
                      % of Total
                      <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedTableData.map((row, idx) => (
                  <tr key={idx} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="px-5 py-3 text-white font-medium">{row.name}</td>
                    <td className="px-4 py-3 text-right text-gray-300 font-mono">
                      {formatCurrencyFull(row.cost)}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <div className="w-24 bg-gray-700 rounded-full h-1.5 hidden sm:block">
                          <div
                            className="bg-blue-500 h-1.5 rounded-full"
                            style={{ width: `${Math.min(100, row.pct)}%` }}
                          />
                        </div>
                        <span className="text-gray-400 font-mono text-xs w-12 text-right">
                          {row.pct.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default CostAnalysis;
