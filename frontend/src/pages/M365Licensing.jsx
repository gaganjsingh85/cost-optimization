import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  Users,
  DollarSign,
  UserX,
  UserCheck,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  TrendingDown,
} from 'lucide-react';
import SavingsCard from '../components/SavingsCard';
import LoadingSpinner from '../components/LoadingSpinner';
import { getM365Licenses, getM365Summary } from '../api/client';

const PIE_COLORS = [
  '#3b82f6', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444',
  '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#a78bfa',
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

function UtilizationBar({ used, total }) {
  const pct = total > 0 ? (used / total) * 100 : 0;
  const color =
    pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-700 rounded-full h-2 min-w-16">
        <div
          className={`${color} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-12 text-right flex-shrink-0">
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

const CustomPieTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
        <p className="text-white text-xs font-medium mb-1">{payload[0].name}</p>
        <p className="text-blue-400 font-semibold text-sm">
          {formatCurrency(payload[0].value)}/mo
        </p>
      </div>
    );
  }
  return null;
};

function M365Licensing() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [licenses, setLicenses] = useState([]);
  const [summary, setSummary] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [licRes, sumRes] = await Promise.allSettled([
        getM365Licenses(),
        getM365Summary(),
      ]);

      if (licRes.status === 'fulfilled') {
        setLicenses(licRes.value?.licenses || licRes.value || []);
      } else {
        throw licRes.reason;
      }

      if (sumRes.status === 'fulfilled') {
        setSummary(sumRes.value);
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

  const stats = useMemo(() => {
    const totalMonthly = licenses.reduce((s, l) => s + (l.monthly_cost || 0), 0);
    const unusedCost = licenses.reduce(
      (s, l) => s + ((l.unused_count || Math.max(0, (l.purchased_count || 0) - (l.active_count || 0))) * (l.unit_price || 0)),
      0
    );
    const activeUsers = licenses.reduce((s, l) => s + (l.active_count || l.used || 0), 0);
    const inactiveUsers = licenses.reduce(
      (s, l) =>
        s +
        Math.max(
          0,
          (l.purchased_count || l.total || 0) - (l.active_count || l.used || 0)
        ),
      0
    );
    return { totalMonthly, unusedCost, activeUsers, inactiveUsers };
  }, [licenses]);

  const pieData = useMemo(() => {
    return licenses
      .filter((l) => (l.monthly_cost || 0) > 0)
      .map((l) => ({
        name: (l.sku_name || l.license_name || l.name || 'Unknown').replace('Microsoft 365', 'M365'),
        value: parseFloat(l.monthly_cost || 0),
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [licenses]);

  const recommendations =
    summary?.recommendations ||
    summary?.optimization_recommendations ||
    summary?.insights ||
    [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">M365 License Optimization</h1>
          <p className="text-gray-400 text-sm mt-1">
            Microsoft 365 license utilization and cost reduction opportunities
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded-lg text-sm font-medium"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 bg-red-900/30 border border-red-700 rounded-xl px-4 py-3 text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <SavingsCard
          title="Total Monthly Spend"
          value={loading ? null : formatCurrency(stats.totalMonthly)}
          subtitle="All M365 licenses"
          icon={DollarSign}
          color="blue"
          loading={loading}
        />
        <SavingsCard
          title="Unused License Cost"
          value={loading ? null : formatCurrency(stats.unusedCost)}
          subtitle="Potential monthly savings"
          icon={TrendingDown}
          color="green"
          loading={loading}
        />
        <SavingsCard
          title="Active Users"
          value={loading ? null : stats.activeUsers.toLocaleString()}
          subtitle="Assigned licenses"
          icon={UserCheck}
          color="gray"
          loading={loading}
        />
        <SavingsCard
          title="Inactive Users"
          value={loading ? null : stats.inactiveUsers.toLocaleString()}
          subtitle="Unassigned licenses"
          icon={UserX}
          color="red"
          loading={loading}
        />
      </div>

      {/* License Table + Pie Chart */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* License Table */}
        <div className="xl:col-span-2 bg-gray-800 border border-gray-700 rounded-xl">
          <div className="px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold">License Utilization</h2>
          </div>
          {loading ? (
            <div className="p-8">
              <LoadingSpinner message="Loading licenses..." fullPage />
            </div>
          ) : licenses.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Users className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No license data available</p>
              <p className="text-xs mt-1">Configure M365 credentials in Settings</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left text-gray-400 font-medium px-5 py-3">License</th>
                    <th className="text-right text-gray-400 font-medium px-3 py-3">Purchased</th>
                    <th className="text-right text-gray-400 font-medium px-3 py-3">Active</th>
                    <th className="text-right text-gray-400 font-medium px-3 py-3">Inactive</th>
                    <th className="text-gray-400 font-medium px-3 py-3 min-w-32">Usage</th>
                    <th className="text-right text-gray-400 font-medium px-3 py-3">Monthly</th>
                    <th className="text-right text-gray-400 font-medium px-5 py-3">Unused Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {licenses.map((lic, idx) => {
                    const purchased = lic.purchased_count || lic.total || 0;
                    const active = lic.active_count || lic.used || 0;
                    const inactive = Math.max(0, purchased - active);
                    const unusedCost = inactive * (lic.unit_price || 0);
                    const utilPct = purchased > 0 ? (active / purchased) * 100 : 0;

                    return (
                      <tr key={lic.sku_id || idx} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="px-5 py-3">
                          <p className="text-white font-medium text-xs leading-tight">
                            {lic.sku_name || lic.license_name || lic.name || 'Unknown'}
                          </p>
                          {lic.sku_id && (
                            <p className="text-gray-600 text-xs font-mono mt-0.5">{lic.sku_id}</p>
                          )}
                        </td>
                        <td className="px-3 py-3 text-gray-300 text-right">{purchased.toLocaleString()}</td>
                        <td className="px-3 py-3 text-green-400 text-right font-medium">{active.toLocaleString()}</td>
                        <td className={`px-3 py-3 text-right font-medium ${inactive > 0 ? 'text-red-400' : 'text-gray-500'}`}>
                          {inactive.toLocaleString()}
                        </td>
                        <td className="px-3 py-3">
                          <UtilizationBar used={active} total={purchased} />
                        </td>
                        <td className="px-3 py-3 text-gray-300 text-right">
                          {formatCurrency(lic.monthly_cost || 0)}
                        </td>
                        <td className={`px-5 py-3 text-right font-semibold ${unusedCost > 0 ? 'text-red-400' : 'text-gray-500'}`}>
                          {unusedCost > 0 ? formatCurrency(unusedCost) : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pie Chart */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl">
          <div className="px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold">Spend Distribution</h2>
          </div>
          <div className="p-4">
            {loading ? (
              <div className="h-64 flex items-center justify-center">
                <LoadingSpinner message="Loading..." />
              </div>
            ) : pieData.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-gray-500 text-sm">
                No spend data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="45%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomPieTooltip />} />
                  <Legend
                    formatter={(value) => (
                      <span className="text-gray-300 text-xs">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl">
          <div className="px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-green-400" />
              Optimization Recommendations
            </h2>
          </div>
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.map((rec, idx) => {
              const title = rec.title || rec.recommendation || (typeof rec === 'string' ? rec : 'Recommendation');
              const description = rec.description || rec.details || '';
              const savings = rec.savings || rec.estimated_savings || rec.monthly_savings;

              return (
                <div
                  key={idx}
                  className="bg-gray-700/50 border border-gray-600 rounded-xl p-4 flex flex-col gap-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                      <p className="text-white text-sm font-medium">{title}</p>
                    </div>
                    {savings && (
                      <span className="text-green-400 font-semibold text-sm whitespace-nowrap flex-shrink-0">
                        {formatCurrency(savings)}/mo
                      </span>
                    )}
                  </div>
                  {description && (
                    <p className="text-gray-400 text-xs leading-relaxed ml-6">{description}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default M365Licensing;
