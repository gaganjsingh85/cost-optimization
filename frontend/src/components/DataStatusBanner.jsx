import React from 'react';
import { AlertCircle, Info, Clock } from 'lucide-react';

function DataStatusBanner({ dataStatus, error, errorClass, source = 'azure' }) {
  if (!dataStatus || dataStatus === 'live') return null;

  const sourceLabel = source === 'm365' ? 'Microsoft 365' : 'Azure';

  const configs = {
    sample: {
      color: 'amber',
      icon: Info,
      title: 'Showing demo data',
      body: `No ${sourceLabel} credentials are configured. Add them in Settings to see your real data.`,
    },
    auth_error: {
      color: 'red',
      icon: AlertCircle,
      title: 'Authentication failed',
      body: error || `Could not authenticate with ${sourceLabel}.`,
    },
    authz_forbidden: {
      color: 'red',
      icon: AlertCircle,
      title: 'Permission denied',
      body: error || `The service principal lacks permission on this ${sourceLabel} resource.`,
    },
    api_error: {
      color: 'red',
      icon: AlertCircle,
      title: 'API call failed',
      body: error || 'The API call failed.',
    },
    sdk_error: {
      color: 'red',
      icon: AlertCircle,
      title: 'SDK error',
      body: error || 'A Python SDK error occurred on the server.',
    },
    rate_limited: {
      color: 'amber',
      icon: Clock,
      title: 'Rate limited',
      body: error || 'Azure Cost Management is throttling this subscription. Data will refresh in ~60 seconds.',
    },
    empty: {
      color: 'blue',
      icon: Info,
      title: 'No data returned',
      body: `Connected successfully but ${sourceLabel} returned an empty result.`,
    },
  };

  const cfg = configs[dataStatus] || configs.api_error;
  const Icon = cfg.icon;

  const colorClasses = {
    amber: 'bg-amber-900/30 border-amber-700 text-amber-200',
    red: 'bg-red-900/30 border-red-700 text-red-200',
    blue: 'bg-blue-900/30 border-blue-700 text-blue-200',
  };

  const hints = {
    auth_app_not_in_tenant: (
      <p className="text-xs mt-2 opacity-90">
        <strong>Fix:</strong> The Client ID is not registered in this Tenant. In Azure Portal, go to
        Microsoft Entra ID → App registrations → your app → Overview. Copy the{' '}
        <em>Application (client) ID</em> (not Object ID) and <em>Directory (tenant) ID</em>.
        Re-save both in Settings.
      </p>
    ),
    auth_invalid_secret: (
      <p className="text-xs mt-2 opacity-90">
        <strong>Fix:</strong> The client secret is invalid or expired. Create a new one in
        Azure Portal → your app → Certificates & secrets. Copy the <em>Value</em> column
        (not Secret ID) immediately — it's only shown once.
      </p>
    ),
    auth_tenant_not_found: (
      <p className="text-xs mt-2 opacity-90">
        <strong>Fix:</strong> The Tenant ID is not recognized. Check Azure Portal →
        Microsoft Entra ID → Overview → Directory ID.
      </p>
    ),
    auth_consent_required: (
      <p className="text-xs mt-2 opacity-90">
        <strong>Fix:</strong> Admin consent is required. Go to Azure Portal → your app →
        API permissions → Grant admin consent for your tenant.
      </p>
    ),
    authz_forbidden: source === 'azure' ? (
      <p className="text-xs mt-2 opacity-90">
        <strong>Fix:</strong> The service principal needs <code>Reader</code> and{' '}
        <code>Cost Management Reader</code> on the subscription. Go to Subscriptions →
        your subscription → Access control (IAM) → Add role assignment.
      </p>
    ) : null,
    rate_limited: (
      <p className="text-xs mt-2 opacity-90">
        Azure Cost Management allows only ~4 calls per minute per subscription.
        The app caches results to stay under the limit, but heavy use or multiple
        clients can trigger throttling briefly.
      </p>
    ),
  };

  return (
    <div className={`flex items-start gap-3 border rounded-xl px-4 py-3 ${colorClasses[cfg.color]}`}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm">{cfg.title}</p>
        <p className="text-xs mt-0.5 opacity-90 break-words">{cfg.body}</p>
        {errorClass && hints[errorClass]}
      </div>
    </div>
  );
}

export default DataStatusBanner;