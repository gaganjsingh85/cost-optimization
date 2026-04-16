import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { AlertTriangle, X } from 'lucide-react';
import Sidebar from './Sidebar';
import { getConfig } from '../api/client';

function Layout() {
  const [configStatus, setConfigStatus] = useState({
    azureConfigured: false,
    m365Configured: false,
    loading: true,
  });
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    checkConfigStatus();
  }, []);

  const checkConfigStatus = async () => {
    try {
      const config = await getConfig();
      setConfigStatus({
        azureConfigured: !!(
          config.azure_tenant_id &&
          config.azure_client_id &&
          config.azure_subscription_id
        ),
        m365Configured: !!(
          config.m365_tenant_id &&
          config.m365_client_id
        ),
        loading: false,
      });
    } catch (err) {
      setConfigStatus({
        azureConfigured: false,
        m365Configured: false,
        loading: false,
      });
    }
  };

  const showBanner =
    !bannerDismissed &&
    !configStatus.loading &&
    (!configStatus.azureConfigured || !configStatus.m365Configured);

  const getMissingServices = () => {
    const missing = [];
    if (!configStatus.azureConfigured) missing.push('Azure');
    if (!configStatus.m365Configured) missing.push('M365');
    return missing.join(' and ');
  };

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />

      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Setup Banner */}
        {showBanner && (
          <div className="bg-amber-900 border-b border-amber-700 px-4 py-3 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
              <span className="text-amber-200 text-sm">
                <strong className="text-amber-100">Setup required:</strong>{' '}
                Configure your {getMissingServices()} credentials in{' '}
                <button
                  onClick={() => navigate('/settings')}
                  className="underline text-amber-100 hover:text-white font-medium"
                >
                  Settings
                </button>{' '}
                to start optimizing costs.
              </span>
            </div>
            <button
              onClick={() => setBannerDismissed(true)}
              className="text-amber-400 hover:text-amber-200 flex-shrink-0 ml-4"
              aria-label="Dismiss banner"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-gray-900">
          <Outlet context={{ configStatus, refreshConfig: checkConfigStatus }} />
        </main>
      </div>
    </div>
  );
}

export default Layout;
