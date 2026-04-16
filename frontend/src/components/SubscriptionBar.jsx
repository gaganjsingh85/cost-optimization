import React, { useEffect, useState } from 'react';
import { Cloud, Copy, Check, AlertTriangle } from 'lucide-react';
import { getSubscriptionInfo } from '../api/client';

function SubscriptionBar() {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const data = await getSubscriptionInfo();
        if (!cancelled) setInfo(data);
      } catch {
        if (!cancelled) setInfo(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleCopy = async () => {
    if (!info?.subscription_id) return;
    try {
      await navigator.clipboard.writeText(info.subscription_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div className="h-12 bg-gray-850 bg-gray-800/70 border-b border-gray-700 px-4 flex items-center">
        <div className="h-4 w-64 bg-gray-700 rounded animate-pulse" />
      </div>
    );
  }

  if (!info) {
    return (
      <div className="h-12 bg-gray-800/70 border-b border-gray-700 px-4 flex items-center gap-2 text-xs text-gray-500">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
        Subscription info unavailable
      </div>
    );
  }

  const {
    display_name,
    subscription_id,
    state,
    tenant_id,
    sample_data,
  } = info;

  return (
    <div className="h-12 bg-gray-800/70 backdrop-blur-sm border-b border-gray-700 px-4 flex items-center gap-3 flex-shrink-0">
      <div className="flex items-center gap-2">
        <Cloud className="w-4 h-4 text-blue-400 flex-shrink-0" />
        <span className="text-gray-400 text-xs uppercase tracking-wide">Subscription</span>
      </div>

      <div className="flex items-center gap-2 min-w-0">
        <span className="text-white font-semibold text-sm truncate max-w-xs">
          {display_name}
        </span>

        {state && (
          <span
            className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded-full border ${
              state === 'Enabled'
                ? 'bg-green-900/30 text-green-300 border-green-700/50'
                : 'bg-gray-700 text-gray-300 border-gray-600'
            }`}
          >
            {state}
          </span>
        )}

        {sample_data && (
          <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-amber-900/30 text-amber-300 border border-amber-700/50">
            Demo Data
          </span>
        )}
      </div>

      <div className="flex items-center gap-1.5 ml-2 min-w-0">
        <span className="text-gray-500 text-xs hidden sm:inline">ID:</span>
        <code className="text-gray-400 text-xs font-mono truncate max-w-[240px]">
          {subscription_id}
        </code>
        <button
          onClick={handleCopy}
          className="p-1 text-gray-500 hover:text-gray-200 rounded"
          title="Copy subscription ID"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>

      {tenant_id && (
        <div className="hidden lg:flex items-center gap-1.5 ml-auto">
          <span className="text-gray-500 text-xs">Tenant:</span>
          <code className="text-gray-500 text-xs font-mono truncate max-w-[200px]">
            {tenant_id}
          </code>
        </div>
      )}
    </div>
  );
}

export default SubscriptionBar;