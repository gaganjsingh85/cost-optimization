import React, { useState, useCallback } from 'react';
import {
  Cloud,
  Users,
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Zap,
  Target,
  ChevronRight,
  Brain,
} from 'lucide-react';
import { analyzeAzure, analyzeM365, analyzeAll } from '../api/client';

const RESULT_TABS = [
  { id: 'summary', label: 'Executive Summary' },
  { id: 'azure', label: 'Azure Insights' },
  { id: 'm365', label: 'M365 Insights' },
  { id: 'action', label: 'Action Plan' },
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

function PriorityBadge({ priority }) {
  const styles = {
    High: 'bg-red-900/50 text-red-300 border border-red-700',
    Medium: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700',
    Low: 'bg-green-900/50 text-green-300 border border-green-700',
    Critical: 'bg-red-900 text-red-200 border border-red-600',
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[priority] || styles.Low}`}
    >
      {priority}
    </span>
  );
}

function SavingsBadge({ value }) {
  if (!value) return null;
  return (
    <span className="text-xs font-semibold text-green-300 bg-green-900/40 border border-green-700/50 px-2 py-0.5 rounded-full">
      Save {formatCurrency(value)}/mo
    </span>
  );
}

function AnalysisButton({ label, icon: Icon, color, onClick, running, disabled }) {
  const colors = {
    blue: 'bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 border-blue-500',
    purple: 'bg-purple-600 hover:bg-purple-500 disabled:bg-purple-900 border-purple-500',
    green: 'bg-green-600 hover:bg-green-500 disabled:bg-green-900 border-green-500',
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled || running}
      className={`flex flex-col items-center justify-center gap-3 p-6 rounded-xl border text-white font-medium transition-all ${colors[color]} disabled:cursor-not-allowed disabled:opacity-60 flex-1 min-h-28`}
    >
      {running ? (
        <Loader2 className="w-8 h-8 animate-spin" />
      ) : (
        <Icon className="w-8 h-8" />
      )}
      <span className="text-sm text-center">{running ? 'Analyzing...' : label}</span>
    </button>
  );
}

function AIAnalysis() {
  const [runningAnalysis, setRunningAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');

  const runAnalysis = useCallback(async (type) => {
    setRunningAnalysis(type);
    setError(null);
    try {
      let result;
      if (type === 'azure') result = await analyzeAzure();
      else if (type === 'm365') result = await analyzeM365();
      else result = await analyzeAll();
      setResults({ ...result, analysisType: type });
      setActiveTab('summary');
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningAnalysis(null);
    }
  }, []);

  const isRunning = runningAnalysis !== null;

  // Normalize fields from either single or full analysis
  const summaryText =
    results?.executive_summary ||
    results?.combined_analysis_text ||
    results?.analysis_text ||
    null;

  const totalSavings =
    results?.total_potential_monthly_savings ??
    results?.total_potential_savings ??
    null;

  const quickWins = results?.azure?.quick_wins || results?.quick_wins || [];

  const azureOpportunities =
    results?.azure?.top_savings_opportunities || results?.top_savings_opportunities || [];

  const m365Recommendations =
    results?.m365?.license_recommendations || results?.license_recommendations || [];

  const highPriorityCount =
    (azureOpportunities.filter(
      (r) => r.priority === 'High' || r.priority === 'Critical'
    ).length || 0) +
    (m365Recommendations.filter(
      (r) => r.priority === 'High' || r.priority === 'Critical'
    ).length || 0);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Brain className="w-6 h-6 text-blue-400" />
          AI-Powered Cost Analysis
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Claude AI analyzes your Azure and M365 usage to identify cost optimization opportunities
        </p>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-white font-semibold mb-4">Run Analysis</h2>
        <div className="flex flex-col sm:flex-row gap-4">
          <AnalysisButton
            label="Analyze Azure Costs"
            icon={Cloud}
            color="blue"
            onClick={() => runAnalysis('azure')}
            running={runningAnalysis === 'azure'}
            disabled={isRunning}
          />
          <AnalysisButton
            label="Analyze M365 Licensing"
            icon={Users}
            color="purple"
            onClick={() => runAnalysis('m365')}
            running={runningAnalysis === 'm365'}
            disabled={isRunning}
          />
          <AnalysisButton
            label="Full Combined Analysis"
            icon={Sparkles}
            color="green"
            onClick={() => runAnalysis('full')}
            running={runningAnalysis === 'full'}
            disabled={isRunning}
          />
        </div>

        {isRunning && (
          <div className="mt-4 flex items-center gap-3 bg-blue-900/30 border border-blue-700/50 rounded-xl px-4 py-3">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin flex-shrink-0" />
            <div>
              <p className="text-blue-300 font-medium text-sm">
                {runningAnalysis === 'azure' && 'Analyzing Azure costs and infrastructure...'}
                {runningAnalysis === 'm365' && 'Analyzing M365 license utilization...'}
                {runningAnalysis === 'full' &&
                  'Running comprehensive Azure + M365 analysis...'}
              </p>
              <p className="text-blue-400/60 text-xs mt-0.5">
                Claude is reviewing your data. This may take 30-60 seconds.
              </p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 bg-red-900/30 border border-red-700 rounded-xl px-4 py-3 text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Analysis failed</p>
            <p className="text-red-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {results && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl">
          <div className="flex border-b border-gray-700 overflow-x-auto px-2 pt-2">
            {RESULT_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-6">
            {activeTab === 'summary' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-green-900/20 border border-green-800/50 rounded-xl p-4">
                    <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">
                      Total Potential Savings
                    </p>
                    <p className="text-2xl font-bold text-green-400">
                      {formatCurrency(totalSavings)}
                      <span className="text-sm font-normal text-green-600">/mo</span>
                    </p>
                  </div>
                  <div className="bg-blue-900/20 border border-blue-800/50 rounded-xl p-4">
                    <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">
                      Quick Wins
                    </p>
                    <p className="text-2xl font-bold text-blue-400">{quickWins.length}</p>
                  </div>
                  <div className="bg-red-900/20 border border-red-800/50 rounded-xl p-4">
                    <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">
                      High Priority Actions
                    </p>
                    <p className="text-2xl font-bold text-red-400">{highPriorityCount}</p>
                  </div>
                </div>

                {summaryText && (
                  <div className="bg-gray-700/30 border border-gray-600 rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-4 h-4 text-blue-400" />
                      <h3 className="text-white font-semibold">AI Summary</h3>
                    </div>
                    <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                      {typeof summaryText === 'object'
                        ? JSON.stringify(summaryText, null, 2)
                        : summaryText}
                    </div>
                  </div>
                )}

                {quickWins.length > 0 && (
                  <div>
                    <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                      <Zap className="w-4 h-4 text-yellow-400" />
                      Quick Wins
                    </h3>
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
                )}
              </div>
            )}

            {activeTab === 'azure' && (
              <div className="space-y-4">
                <h3 className="text-white font-semibold">Top Azure Savings Opportunities</h3>
                {azureOpportunities.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Cloud className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">
                      No Azure insights available. Run an Azure or full analysis.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {azureOpportunities.map((opp, idx) => (
                      <div
                        key={idx}
                        className="bg-gray-700/40 border border-gray-600 rounded-xl p-5"
                      >
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="text-white font-medium text-sm">{opp.title}</h4>
                            {opp.priority && <PriorityBadge priority={opp.priority} />}
                          </div>
                          {opp.estimated_monthly_savings && (
                            <SavingsBadge value={opp.estimated_monthly_savings} />
                          )}
                        </div>
                        {opp.description && (
                          <p className="text-gray-400 text-sm leading-relaxed mb-2">
                            {opp.description}
                          </p>
                        )}
                        {opp.action_required && (
                          <div className="flex items-start gap-2 mt-3 bg-blue-900/20 border border-blue-800/40 rounded-lg px-3 py-2">
                            <ChevronRight className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
                            <p className="text-blue-300 text-xs">{opp.action_required}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'm365' && (
              <div className="space-y-4">
                <h3 className="text-white font-semibold">M365 License Recommendations</h3>
                {m365Recommendations.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Users className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">
                      No M365 insights available. Run an M365 or full analysis.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-700">
                          <th className="text-left text-gray-400 font-medium px-4 py-3">
                            License
                          </th>
                          <th className="text-right text-gray-400 font-medium px-4 py-3">
                            Current
                          </th>
                          <th className="text-right text-gray-400 font-medium px-4 py-3">
                            Recommended
                          </th>
                          <th className="text-right text-gray-400 font-medium px-4 py-3">
                            Monthly Savings
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {m365Recommendations.map((rec, idx) => (
                          <tr
                            key={idx}
                            className="border-b border-gray-700/50 hover:bg-gray-700/30"
                          >
                            <td className="px-4 py-3 text-white font-medium">
                              {rec.license_name || rec.title}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-300">
                              {rec.current_count ?? '—'}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-300">
                              {rec.recommended_count ?? '—'}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className="text-green-400 font-semibold">
                                {formatCurrency(rec.monthly_savings)}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'action' && (
              <div className="space-y-4">
                <h3 className="text-white font-semibold flex items-center gap-2">
                  <Target className="w-4 h-4 text-blue-400" />
                  Recommended Actions
                </h3>
                <div className="bg-gray-700/30 border border-gray-600 rounded-xl p-5 text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">
                  {results?.combined_analysis_text ||
                    results?.azure?.analysis_text ||
                    results?.analysis_text ||
                    'No detailed analysis available.'}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {!results && !isRunning && !error && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center">
          <Brain className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-gray-300 font-semibold text-lg mb-2">No Analysis Results Yet</h3>
          <p className="text-gray-500 text-sm max-w-md mx-auto">
            Click one of the analysis buttons above to have Claude AI analyze your Azure costs and
            M365 licensing data.
          </p>
        </div>
      )}
    </div>
  );
}

export default AIAnalysis;