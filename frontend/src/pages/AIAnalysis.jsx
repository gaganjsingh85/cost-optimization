import React, { useState, useCallback } from 'react';
import {
  Cloud,
  Users,
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  DollarSign,
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
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[priority] || styles.Low}`}>
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

  // Extract data from results in a flexible way
  const summaryText =
    results?.summary ||
    results?.executive_summary?.summary ||
    results?.executive_summary ||
    (typeof results?.analysis === 'string' ? results.analysis : null) ||
    null;

  const totalSavings =
    results?.total_potential_savings ||
    results?.executive_summary?.total_potential_savings ||
    results?.savings?.total ||
    null;

  const quickWinCount =
    results?.quick_wins?.length ||
    results?.executive_summary?.quick_win_count ||
    results?.insights?.quick_wins?.length ||
    0;

  const highPriorityCount =
    results?.high_priority_count ||
    results?.executive_summary?.high_priority_count ||
    (results?.azure_analysis?.recommendations || []).filter((r) => r.priority === 'High').length ||
    0;

  const azureOpportunities =
    results?.azure_analysis?.top_opportunities ||
    results?.azure_opportunities ||
    results?.azure_analysis?.recommendations ||
    results?.recommendations ||
    [];

  const m365Recommendations =
    results?.m365_analysis?.recommendations ||
    results?.m365_recommendations ||
    results?.m365_analysis?.optimization_opportunities ||
    [];

  const quickWins = results?.quick_wins || results?.azure_analysis?.quick_wins || [];

  // Action plan
  const actionPlan30 =
    results?.action_plan?.['30_days'] ||
    results?.roadmap?.['30_days'] ||
    results?.action_plan?.immediate ||
    [];
  const actionPlan60 =
    results?.action_plan?.['60_days'] ||
    results?.roadmap?.['60_days'] ||
    results?.action_plan?.short_term ||
    [];
  const actionPlan90 =
    results?.action_plan?.['90_days'] ||
    results?.roadmap?.['90_days'] ||
    results?.action_plan?.long_term ||
    [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Brain className="w-6 h-6 text-blue-400" />
          AI-Powered Cost Analysis
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Claude AI analyzes your Azure and M365 usage to identify cost optimization opportunities
        </p>
      </div>

      {/* Analysis Buttons */}
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

        {/* Status Indicator */}
        {isRunning && (
          <div className="mt-4 flex items-center gap-3 bg-blue-900/30 border border-blue-700/50 rounded-xl px-4 py-3">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin flex-shrink-0" />
            <div>
              <p className="text-blue-300 font-medium text-sm">
                {runningAnalysis === 'azure' && 'Analyzing Azure costs and infrastructure...'}
                {runningAnalysis === 'm365' && 'Analyzing M365 license utilization...'}
                {runningAnalysis === 'full' && 'Running comprehensive Azure + M365 analysis...'}
              </p>
              <p className="text-blue-400/60 text-xs mt-0.5">
                Claude is reviewing your data. This may take 30-60 seconds.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 bg-red-900/30 border border-red-700 rounded-xl px-4 py-3 text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Analysis failed</p>
            <p className="text-red-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl">
          {/* Result Tabs */}
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
            {/* Executive Summary Tab */}
            {activeTab === 'summary' && (
              <div className="space-y-6">
                {/* KPI Row */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-green-900/20 border border-green-800/50 rounded-xl p-4">
                    <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Total Potential Savings</p>
                    <p className="text-2xl font-bold text-green-400">
                      {formatCurrency(totalSavings)}
                      <span className="text-sm font-normal text-green-600">/mo</span>
                    </p>
                  </div>
                  <div className="bg-blue-900/20 border border-blue-800/50 rounded-xl p-4">
                    <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Quick Wins</p>
                    <p className="text-2xl font-bold text-blue-400">{quickWinCount}</p>
                  </div>
                  <div className="bg-red-900/20 border border-red-800/50 rounded-xl p-4">
                    <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">High Priority Actions</p>
                    <p className="text-2xl font-bold text-red-400">{highPriorityCount}</p>
                  </div>
                </div>

                {/* Summary Text */}
                {summaryText && (
                  <div className="bg-gray-700/30 border border-gray-600 rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-4 h-4 text-blue-400" />
                      <h3 className="text-white font-semibold">AI Summary</h3>
                    </div>
                    <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                      {typeof summaryText === 'object' ? JSON.stringify(summaryText, null, 2) : summaryText}
                    </div>
                  </div>
                )}

                {/* Quick Wins */}
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
                          <span className="text-gray-300 text-sm">{typeof win === 'string' ? win : win.title || win.description || JSON.stringify(win)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Azure Insights Tab */}
            {activeTab === 'azure' && (
              <div className="space-y-4">
                <h3 className="text-white font-semibold">Top Azure Savings Opportunities</h3>
                {azureOpportunities.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Cloud className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">No Azure insights available. Run an Azure or full analysis.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {azureOpportunities.map((opp, idx) => {
                      const title = opp.title || opp.opportunity || opp.name || `Opportunity ${idx + 1}`;
                      const description = opp.description || opp.details || opp.action || '';
                      const savings = opp.estimated_savings || opp.monthly_savings || opp.savings;
                      const priority = opp.priority || opp.impact;
                      const action = opp.required_action || opp.action_steps || '';

                      return (
                        <div key={idx} className="bg-gray-700/40 border border-gray-600 rounded-xl p-5">
                          <div className="flex items-start justify-between gap-3 mb-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4 className="text-white font-medium text-sm">{title}</h4>
                              {priority && <PriorityBadge priority={priority} />}
                            </div>
                            {savings && <SavingsBadge value={savings} />}
                          </div>
                          {description && (
                            <p className="text-gray-400 text-sm leading-relaxed mb-2">{description}</p>
                          )}
                          {action && (
                            <div className="flex items-start gap-2 mt-3 bg-blue-900/20 border border-blue-800/40 rounded-lg px-3 py-2">
                              <ChevronRight className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
                              <p className="text-blue-300 text-xs">{action}</p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* M365 Insights Tab */}
            {activeTab === 'm365' && (
              <div className="space-y-4">
                <h3 className="text-white font-semibold">M365 License Recommendations</h3>
                {m365Recommendations.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Users className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">No M365 insights available. Run an M365 or full analysis.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-700">
                          <th className="text-left text-gray-400 font-medium px-4 py-3">Recommendation</th>
                          <th className="text-left text-gray-400 font-medium px-4 py-3">Details</th>
                          <th className="text-right text-gray-400 font-medium px-4 py-3">Monthly Savings</th>
                          <th className="text-left text-gray-400 font-medium px-4 py-3">Priority</th>
                        </tr>
                      </thead>
                      <tbody>
                        {m365Recommendations.map((rec, idx) => {
                          const title = rec.title || rec.recommendation || (typeof rec === 'string' ? rec : `Recommendation ${idx + 1}`);
                          const description = rec.description || rec.details || '';
                          const savings = rec.savings || rec.estimated_savings || rec.monthly_savings;
                          const priority = rec.priority || rec.impact || 'Medium';

                          return (
                            <tr key={idx} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                              <td className="px-4 py-3 text-white font-medium">{title}</td>
                              <td className="px-4 py-3 text-gray-400 max-w-xs">
                                <p className="line-clamp-2">{description}</p>
                              </td>
                              <td className="px-4 py-3 text-right">
                                {savings ? (
                                  <span className="text-green-400 font-semibold">{formatCurrency(savings)}</span>
                                ) : (
                                  <span className="text-gray-500">—</span>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                <PriorityBadge priority={priority} />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Action Plan Tab */}
            {activeTab === 'action' && (
              <div className="space-y-4">
                <h3 className="text-white font-semibold flex items-center gap-2">
                  <Target className="w-4 h-4 text-blue-400" />
                  90-Day Optimization Roadmap
                </h3>

                {actionPlan30.length === 0 && actionPlan60.length === 0 && actionPlan90.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Target className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">No action plan available. Run a full analysis to generate a roadmap.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* 30 Days */}
                    <div className="bg-blue-900/20 border border-blue-800/50 rounded-xl p-5">
                      <div className="flex items-center gap-2 mb-4">
                        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                          30
                        </div>
                        <div>
                          <p className="text-blue-300 font-semibold text-sm">Days 1-30</p>
                          <p className="text-gray-500 text-xs">Quick Wins</p>
                        </div>
                      </div>
                      <ul className="space-y-2.5">
                        {(actionPlan30.length > 0 ? actionPlan30 : ['No immediate actions identified']).map((item, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0 mt-1.5" />
                            <span className="text-gray-300 text-xs leading-relaxed">
                              {typeof item === 'string' ? item : item.action || item.title || JSON.stringify(item)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* 60 Days */}
                    <div className="bg-purple-900/20 border border-purple-800/50 rounded-xl p-5">
                      <div className="flex items-center gap-2 mb-4">
                        <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                          60
                        </div>
                        <div>
                          <p className="text-purple-300 font-semibold text-sm">Days 31-60</p>
                          <p className="text-gray-500 text-xs">Medium Term</p>
                        </div>
                      </div>
                      <ul className="space-y-2.5">
                        {(actionPlan60.length > 0 ? actionPlan60 : ['No medium-term actions identified']).map((item, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0 mt-1.5" />
                            <span className="text-gray-300 text-xs leading-relaxed">
                              {typeof item === 'string' ? item : item.action || item.title || JSON.stringify(item)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* 90 Days */}
                    <div className="bg-green-900/20 border border-green-800/50 rounded-xl p-5">
                      <div className="flex items-center gap-2 mb-4">
                        <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                          90
                        </div>
                        <div>
                          <p className="text-green-300 font-semibold text-sm">Days 61-90</p>
                          <p className="text-gray-500 text-xs">Strategic</p>
                        </div>
                      </div>
                      <ul className="space-y-2.5">
                        {(actionPlan90.length > 0 ? actionPlan90 : ['No long-term actions identified']).map((item, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0 mt-1.5" />
                            <span className="text-gray-300 text-xs leading-relaxed">
                              {typeof item === 'string' ? item : item.action || item.title || JSON.stringify(item)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty State (no results yet) */}
      {!results && !isRunning && !error && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center">
          <Brain className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-gray-300 font-semibold text-lg mb-2">No Analysis Results Yet</h3>
          <p className="text-gray-500 text-sm max-w-md mx-auto">
            Click one of the analysis buttons above to have Claude AI analyze your Azure costs
            and M365 licensing data and generate actionable recommendations.
          </p>
        </div>
      )}
    </div>
  );
}

export default AIAnalysis;
