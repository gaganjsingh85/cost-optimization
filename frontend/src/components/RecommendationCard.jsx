import React, { useState } from 'react';
import { ChevronDown, ChevronUp, DollarSign, Server } from 'lucide-react';

const IMPACT_STYLES = {
  High: 'bg-red-900/50 text-red-300 border border-red-700',
  Medium: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700',
  Low: 'bg-green-900/50 text-green-300 border border-green-700',
};

const CATEGORY_STYLES = {
  Cost: 'bg-blue-900/50 text-blue-300 border border-blue-700',
  Security: 'bg-purple-900/50 text-purple-300 border border-purple-700',
  HighAvailability: 'bg-orange-900/50 text-orange-300 border border-orange-700',
  Performance: 'bg-cyan-900/50 text-cyan-300 border border-cyan-700',
  OperationalExcellence: 'bg-teal-900/50 text-teal-300 border border-teal-700',
  default: 'bg-gray-700/50 text-gray-300 border border-gray-600',
};

const CATEGORY_LABELS = {
  HighAvailability: 'High Availability',
  OperationalExcellence: 'Operational Excellence',
};

function formatCurrency(value) {
  if (!value && value !== 0) return null;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function RecommendationCard({ recommendation, compact = false }) {
  const [expanded, setExpanded] = useState(false);
  if (!recommendation) return null;

  const {
    impact,
    category,
    short_description,
    extended_properties,
    impacted_value,
    resource_group,
    potential_annual_savings,
  } = recommendation;

  const impactStyle = IMPACT_STYLES[impact] || IMPACT_STYLES.Low;
  const categoryStyle = CATEGORY_STYLES[category] || CATEGORY_STYLES.default;
  const categoryLabel = CATEGORY_LABELS[category] || category;

  // Handle both short_description as object (new) or as string (from backend)
  const problemText =
    (short_description && typeof short_description === 'object'
      ? short_description.problem
      : short_description) || 'No description available';

  const solutionText =
    (short_description && typeof short_description === 'object'
      ? short_description.solution
      : '') || '';

  const monthlySavings = potential_annual_savings ? potential_annual_savings / 12 : null;

  const resourceName = impacted_value || '';

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${impactStyle}`}>
            {impact || 'Low'} Impact
          </span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${categoryStyle}`}>
            {categoryLabel}
          </span>
        </div>
        {monthlySavings && (
          <div className="flex items-center gap-1 text-green-400 font-semibold text-sm whitespace-nowrap flex-shrink-0">
            <DollarSign className="w-3.5 h-3.5" />
            {formatCurrency(monthlySavings)}/mo
          </div>
        )}
      </div>

      <p className="text-white text-sm font-medium leading-snug mb-2">{problemText}</p>

      {(resourceName || resource_group) && (
        <div className="flex items-center gap-1.5 text-gray-400 text-xs mb-3">
          <Server className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="truncate font-mono">
            {resourceName}
            {resource_group ? ` (${resource_group})` : ''}
          </span>
        </div>
      )}

      {solutionText && !compact && (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" />
                Show details
              </>
            )}
          </button>
          {expanded && (
            <div className="mt-3 pt-3 border-t border-gray-700">
              <p className="text-xs text-gray-400 font-medium mb-1">Recommended Action:</p>
              <p className="text-sm text-gray-300 leading-relaxed">{solutionText}</p>
              {extended_properties?.currentSku && (
                <p className="text-xs text-gray-500 mt-2">
                  Current SKU:{' '}
                  <span className="text-gray-400">{extended_properties.currentSku}</span>
                  {extended_properties.targetSku && (
                    <>
                      {' '}
                      → Recommended:{' '}
                      <span className="text-gray-400">{extended_properties.targetSku}</span>
                    </>
                  )}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default RecommendationCard;