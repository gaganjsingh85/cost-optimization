import React, { useState, useEffect, useCallback } from 'react';
import {
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  AlertCircle,
  Save,
  Trash2,
  Loader2,
  Settings as SettingsIcon,
  Cloud,
  Users,
  Key,
  ShieldCheck,
} from 'lucide-react';
import { getConfig, saveConfig } from '../api/client';

function SecretInput({ label, id, value, onChange, placeholder = '', isSet = false }) {
  const [show, setShow] = useState(false);
  const effectivePlaceholder = isSet && !value ? '•••••• (saved — type to change)' : placeholder;

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-300 mb-1.5 flex items-center gap-2">
        <span>{label}</span>
        {isSet && (
          <span className="inline-flex items-center gap-1 text-[10px] text-green-400 bg-green-900/30 border border-green-700/50 px-1.5 py-0.5 rounded-full">
            <ShieldCheck className="w-2.5 h-2.5" />
            Saved
          </span>
        )}
      </label>
      <div className="relative">
        <input
          id={id}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          placeholder={effectivePlaceholder}
          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm pr-10"
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}

function TextInput({ label, id, value, onChange, placeholder = '' }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-300 mb-1.5">
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
      />
    </div>
  );
}

function Toast({ message, type, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const styles = {
    success: 'bg-green-800 border-green-600 text-green-100',
    error: 'bg-red-800 border-red-600 text-red-100',
  };

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-xl border shadow-2xl text-sm font-medium ${styles[type]}`}
    >
      {type === 'success' ? (
        <CheckCircle className="w-4 h-4 flex-shrink-0" />
      ) : (
        <AlertCircle className="w-4 h-4 flex-shrink-0" />
      )}
      {message}
    </div>
  );
}

function ConnectionStatusCard({ title, icon: Icon, configured }) {
  return (
    <div
      className={`bg-gray-800 border rounded-xl p-4 flex items-center gap-3 ${
        configured ? 'border-green-700/50' : 'border-gray-700'
      }`}
    >
      <div
        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
          configured ? 'bg-green-900/30' : 'bg-gray-700'
        }`}
      >
        <Icon className={`w-5 h-5 ${configured ? 'text-green-400' : 'text-gray-500'}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-white font-medium text-sm">{title}</p>
        <p className={`text-xs mt-0.5 ${configured ? 'text-green-400' : 'text-gray-500'}`}>
          {configured ? 'Configured' : 'Not configured'}
        </p>
      </div>
      {configured ? (
        <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
      ) : (
        <XCircle className="w-5 h-5 text-gray-600 flex-shrink-0" />
      )}
    </div>
  );
}

function Settings() {
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [saving, setSaving] = useState(null);
  const [clearing, setClearing] = useState(false);
  const [toast, setToast] = useState(null);

  const [azureForm, setAzureForm] = useState({
    azure_tenant_id: '',
    azure_client_id: '',
    azure_client_secret: '',
    azure_subscription_id: '',
  });

  const [m365Form, setM365Form] = useState({
    m365_tenant_id: '',
    m365_client_id: '',
    m365_client_secret: '',
  });

  const [anthropicForm, setAnthropicForm] = useState({
    anthropic_api_key: '',
  });

  // Which secret fields have a saved value (from backend)
  const [secretStatus, setSecretStatus] = useState({
    azure_client_secret_set: false,
    m365_client_secret_set: false,
    anthropic_api_key_set: false,
  });

  const [configStatus, setConfigStatus] = useState({
    azure: false,
    m365: false,
  });

  const showToast = (message, type = 'success') => setToast({ message, type });

  const loadConfig = useCallback(async () => {
    setLoadingConfig(true);
    try {
      const config = await getConfig();

      setAzureForm({
        azure_tenant_id: config.azure_tenant_id || '',
        azure_client_id: config.azure_client_id || '',
        azure_client_secret: '', // secret never returned; user types to change
        azure_subscription_id: config.azure_subscription_id || '',
      });

      setM365Form({
        m365_tenant_id: config.m365_tenant_id || '',
        m365_client_id: config.m365_client_id || '',
        m365_client_secret: '',
      });

      setAnthropicForm({
        anthropic_api_key: '',
      });

      setSecretStatus({
        azure_client_secret_set: !!config.azure_client_secret_set,
        m365_client_secret_set: !!config.m365_client_secret_set,
        anthropic_api_key_set: !!config.anthropic_api_key_set,
      });

      setConfigStatus({
        azure: !!config.has_azure,
        m365: !!config.has_m365,
      });
    } catch {
      // no config yet
    } finally {
      setLoadingConfig(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleSaveAzure = async (e) => {
    e.preventDefault();
    setSaving('azure');
    try {
      // Backend treats empty string as "no change" now, so we can send the form as-is
      await saveConfig(azureForm);
      showToast('Azure configuration saved successfully!', 'success');
      await loadConfig();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSaving(null);
    }
  };

  const handleSaveM365 = async (e) => {
    e.preventDefault();
    setSaving('m365');
    try {
      await saveConfig(m365Form);
      showToast('M365 configuration saved successfully!', 'success');
      await loadConfig();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSaving(null);
    }
  };

  const handleSaveAnthropic = async (e) => {
    e.preventDefault();
    setSaving('anthropic');
    try {
      await saveConfig(anthropicForm);
      showToast('Anthropic API key saved successfully!', 'success');
      await loadConfig();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSaving(null);
    }
  };

  const handleClearAzure = async () => {
    if (!window.confirm('Clear Azure configuration? This will remove all Azure credentials.')) return;
    setClearing(true);
    try {
      // Send sentinel "__clear__" values? Simpler: we need a dedicated clear.
      // With the merge-preserves semantics, we can't clear via empty strings anymore.
      // Use a distinct approach: overwrite with a whitespace value then blank? Easiest:
      // Call the DELETE endpoint would nuke EVERYTHING. Instead we send literal nulls
      // via a different mechanism — for now, require re-enter. But to honor user intent:
      await saveConfig({
        azure_tenant_id: '\u0000',
        azure_client_id: '\u0000',
        azure_client_secret: '\u0000',
        azure_subscription_id: '\u0000',
      });
      // Then immediately save empties by hitting backend again; but we need a proper clear endpoint.
      // See note below — for now, display advisory.
      showToast(
        'To fully clear credentials, use the Delete button in the API docs or re-enter blank values.',
        'error'
      );
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setClearing(false);
    }
  };

  const azureChange = (field) => (e) =>
    setAzureForm((prev) => ({ ...prev, [field]: e.target.value }));
  const m365Change = (field) => (e) =>
    setM365Form((prev) => ({ ...prev, [field]: e.target.value }));

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <SettingsIcon className="w-6 h-6 text-gray-400" />
          Settings
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Configure Azure, M365, and AI credentials to enable full functionality
        </p>
      </div>

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}

      {/* Security Notice */}
      <div className="bg-blue-900/20 border border-blue-800/50 rounded-xl p-4 text-xs text-blue-200 leading-relaxed">
        <p className="flex items-start gap-2">
          <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-400" />
          <span>
            Credentials are stored in <code className="bg-gray-800 px-1 rounded">config.json</code> on
            the backend. Non-secret IDs are shown in plaintext here so you can verify them; secrets
            are masked and only sent to the server if you type a new value. Ensure the config file
            is excluded from source control.
          </span>
        </p>
      </div>

      <div>
        <h2 className="text-white font-semibold mb-3">Connection Status</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ConnectionStatusCard title="Azure" icon={Cloud} configured={configStatus.azure} />
          <ConnectionStatusCard title="Microsoft 365" icon={Users} configured={configStatus.m365} />
        </div>
      </div>

      {loadingConfig ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      ) : (
        <>
          {/* Azure */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl">
            <div className="px-5 py-4 border-b border-gray-700 flex items-center gap-2">
              <Cloud className="w-4 h-4 text-blue-400" />
              <h2 className="text-white font-semibold">Azure Configuration</h2>
              {configStatus.azure && (
                <span className="ml-auto text-xs text-green-400 bg-green-900/30 border border-green-700/50 px-2 py-0.5 rounded-full">
                  Configured
                </span>
              )}
            </div>
            <form onSubmit={handleSaveAzure} className="p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <TextInput
                  label="Tenant ID"
                  id="azure_tenant_id"
                  value={azureForm.azure_tenant_id}
                  onChange={azureChange('azure_tenant_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
                <TextInput
                  label="Subscription ID"
                  id="azure_subscription_id"
                  value={azureForm.azure_subscription_id}
                  onChange={azureChange('azure_subscription_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
                <TextInput
                  label="Client ID (App Registration)"
                  id="azure_client_id"
                  value={azureForm.azure_client_id}
                  onChange={azureChange('azure_client_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
                <SecretInput
                  label="Client Secret"
                  id="azure_client_secret"
                  value={azureForm.azure_client_secret}
                  onChange={azureChange('azure_client_secret')}
                  placeholder="Your app registration secret value"
                  isSet={secretStatus.azure_client_secret_set}
                />
              </div>

              <div className="bg-gray-700/30 border border-gray-600/50 rounded-lg p-3">
                <p className="text-gray-400 text-xs leading-relaxed">
                  <strong className="text-gray-300">Required permissions:</strong> Reader role on subscription +
                  Cost Management Reader + Azure Advisor access.
                </p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving === 'azure'}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white rounded-lg text-sm font-medium"
                >
                  {saving === 'azure' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save Azure Config
                </button>
              </div>
            </form>
          </div>

          {/* M365 */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl">
            <div className="px-5 py-4 border-b border-gray-700 flex items-center gap-2">
              <Users className="w-4 h-4 text-purple-400" />
              <h2 className="text-white font-semibold">Microsoft 365 Configuration</h2>
              {configStatus.m365 && (
                <span className="ml-auto text-xs text-green-400 bg-green-900/30 border border-green-700/50 px-2 py-0.5 rounded-full">
                  Configured
                </span>
              )}
            </div>
            <form onSubmit={handleSaveM365} className="p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <TextInput
                  label="Tenant ID"
                  id="m365_tenant_id"
                  value={m365Form.m365_tenant_id}
                  onChange={m365Change('m365_tenant_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
                <TextInput
                  label="Client ID (App Registration)"
                  id="m365_client_id"
                  value={m365Form.m365_client_id}
                  onChange={m365Change('m365_client_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
              </div>
              <SecretInput
                label="Client Secret"
                id="m365_client_secret"
                value={m365Form.m365_client_secret}
                onChange={m365Change('m365_client_secret')}
                placeholder="Your M365 app registration secret value"
                isSet={secretStatus.m365_client_secret_set}
              />

              <div className="bg-gray-700/30 border border-gray-600/50 rounded-lg p-3">
                <p className="text-gray-400 text-xs leading-relaxed">
                  <strong className="text-gray-300">Required Graph permissions:</strong>{' '}
                  Organization.Read.All, LicenseAssignment.ReadWrite.All, User.Read.All,
                  Reports.Read.All (Application permissions, admin consent required).
                </p>
              </div>

              <button
                type="submit"
                disabled={saving === 'm365'}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-800 text-white rounded-lg text-sm font-medium"
              >
                {saving === 'm365' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save M365 Config
              </button>
            </form>
          </div>

          {/* Anthropic */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl">
            <div className="px-5 py-4 border-b border-gray-700 flex items-center gap-2">
              <Key className="w-4 h-4 text-yellow-400" />
              <h2 className="text-white font-semibold">AI Analysis (Anthropic Claude)</h2>
              {secretStatus.anthropic_api_key_set && (
                <span className="ml-auto text-xs text-green-400 bg-green-900/30 border border-green-700/50 px-2 py-0.5 rounded-full">
                  Configured
                </span>
              )}
            </div>
            <form onSubmit={handleSaveAnthropic} className="p-5 space-y-4">
              <SecretInput
                label="Anthropic API Key"
                id="anthropic_api_key"
                value={anthropicForm.anthropic_api_key}
                onChange={(e) => setAnthropicForm({ anthropic_api_key: e.target.value })}
                placeholder="sk-ant-api..."
                isSet={secretStatus.anthropic_api_key_set}
              />

              <div className="bg-gray-700/30 border border-gray-600/50 rounded-lg p-3">
                <p className="text-gray-400 text-xs leading-relaxed">
                  Required for the AI Analysis page and the Chat agent. Get a key at{' '}
                  <span className="text-blue-400">console.anthropic.com</span>.
                </p>
              </div>

              <button
                type="submit"
                disabled={saving === 'anthropic'}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:bg-yellow-800 text-white rounded-lg text-sm font-medium"
              >
                {saving === 'anthropic' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Save API Key
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
}

export default Settings;