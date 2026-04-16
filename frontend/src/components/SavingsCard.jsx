import React from 'react';
import { TrendingDown, TrendingUp, Minus } from 'lucide-react';

const COLOR_THEMES = {
  blue: {
    bg: 'bg-blue-900/20',
    border: 'border-blue-800/50',
    icon: 'text-blue-400 bg-blue-900/30',
    value: 'text-blue-100',
  },
  green: {
    bg: 'bg-green-900/20',
    border: 'border-green-800/50',
    icon: 'text-green-400 bg-green-900/30',
    value: 'text-green-100',
  },
  red: {
    bg: 'bg-red-900/20',
    border: 'border-red-800/50',
    icon: 'text-red-400 bg-red-900/30',
    value: 'text-red-100',
  },
  purple: {
    bg: 'bg-purple-900/20',
    border: 'border-purple-800/50',
    icon: 'text-purple-400 bg-purple-900/30',
    value: 'text-purple-100',
  },
  gray: {
    bg: 'bg-gray-800',
    border: 'border-gray-700',
    icon: 'text-gray-400 bg-gray-700',
    value: 'text-white',
  },
};

function SavingsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'gray',
  trend = null,
  trendValue = null,
  loading = false,
}) {
  const theme = COLOR_THEMES[color] || COLOR_THEMES.gray;

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor =
    trend === 'down' ? 'text-green-400' : trend === 'up' ? 'text-red-400' : 'text-gray-400';

  return (
    <div className={`rounded-xl border p-5 ${theme.bg} ${theme.border} flex flex-col gap-3`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-gray-400 text-xs font-medium uppercase tracking-wide mb-1">{title}</p>
          {loading ? (
            <div className="h-8 bg-gray-700 rounded-lg animate-pulse w-3/4" />
          ) : (
            <p className={`text-2xl font-bold truncate ${theme.value}`}>{value ?? '—'}</p>
          )}
        </div>
        {Icon && (
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${theme.icon}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {(subtitle || trendValue) && (
        <div className="flex items-center gap-2">
          {trendValue && (
            <div className={`flex items-center gap-1 text-xs font-medium ${trendColor}`}>
              <TrendIcon className="w-3 h-3" />
              {trendValue}
            </div>
          )}
          {subtitle && (
            <p className="text-gray-500 text-xs">{subtitle}</p>
          )}
        </div>
      )}
    </div>
  );
}

export default SavingsCard;
