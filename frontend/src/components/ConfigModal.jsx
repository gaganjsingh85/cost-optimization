import React, { useState, useEffect } from 'react';
import { X, Eye, EyeOff, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { saveConfig, getConfig } from '../api/client';

const TABS = ['Azure', 'M365'];

function InputField({ label, id, value, onChange, type = 'text', placeholder = '', required = false }) {
  const [show, setShow] = useState(false);
  const isPassword = type === 'password';

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-300 mb-1">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      <div className="relative">
        <input
          id={id}
          type={isPassword && !show ? 'password' : 'text'}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm pr-10"
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow(!show)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
          >
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  );
}

function ConfigModal({ isOpen, onClose, onSaved }) {
  const [activeTab, setActiveTab] = useState('Azure');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [formData, setFormData] = useState({
    azure_tenant_id: '',
    azure_client_id: '',
    azure_client_secret: '',
    azure_subscription_id: '',
    m365_tenant_id: '',
    m365_client_id: '',
    m365_client_secret: '',
    anthropic_api_key: '',
  });

  useEffect(() => {
    if (isOpen) {
      loadConfig();
    }
  }, [isOpen]);

  const loadConfig = async () => {
    try {
      const config = await getConfig();
      setFormData({
        azure_tenant_id: config.azure_tenant_id || '',
        azure_client_id: config.azure_client_id || '',
        azure_client_secret: config.azure_client_secret || '',
        azure_subscription_id: config.azure_subscription_id || '',
        m365_tenant_id: config.m365_tenant_id || '',
        m365_client_id: config.m365_client_id || '',
        m365_client_secret: config.m365_client_secret || '',
        anthropic_api_key: config.anthropic_api_key || '',
      });
    } catch (err) {
      // No existing config
    }
  };

  const handleChange = (field) => (e) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      await saveConfig(formData);
      setMessage({ type: 'success', text: 'Configuration saved successfully!' });
      if (onSaved) onSaved();
      setTimeout(() => {
        setMessage(null);
        onClose();
      }, 1500);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-800 rounded-xl border border-gray-700 shadow-2xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Configure Credentials</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white rounded-lg p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700 px-6">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-3 px-4 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <form onSubmit={handleSave}>
          <div className="px-6 py-5 space-y-4 max-h-96 overflow-y-auto">
            {activeTab === 'Azure' && (
              <>
                <InputField
                  label="Tenant ID"
                  id="azure_tenant_id"
                  value={formData.azure_tenant_id}
                  onChange={handleChange('azure_tenant_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  required
                />
                <InputField
                  label="Client ID (App ID)"
                  id="azure_client_id"
                  value={formData.azure_client_id}
                  onChange={handleChange('azure_client_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  required
                />
                <InputField
                  label="Client Secret"
                  id="azure_client_secret"
                  type="password"
                  value={formData.azure_client_secret}
                  onChange={handleChange('azure_client_secret')}
                  placeholder="Your app registration secret"
                  required
                />
                <InputField
                  label="Subscription ID"
                  id="azure_subscription_id"
                  value={formData.azure_subscription_id}
                  onChange={handleChange('azure_subscription_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  required
                />

                {/* Anthropic API Key */}
                <div className="pt-2 border-t border-gray-700">
                  <p className="text-xs text-gray-500 mb-3">AI Analysis (Claude)</p>
                  <InputField
                    label="Anthropic API Key"
                    id="anthropic_api_key"
                    type="password"
                    value={formData.anthropic_api_key}
                    onChange={handleChange('anthropic_api_key')}
                    placeholder="sk-ant-..."
                  />
                </div>
              </>
            )}

            {activeTab === 'M365' && (
              <>
                <p className="text-xs text-gray-400 bg-gray-750 rounded-lg p-3 border border-gray-600">
                  M365 credentials can use the same Tenant ID as Azure, or a separate app registration
                  with Microsoft Graph API permissions.
                </p>
                <InputField
                  label="Tenant ID"
                  id="m365_tenant_id"
                  value={formData.m365_tenant_id}
                  onChange={handleChange('m365_tenant_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  required
                />
                <InputField
                  label="Client ID (App ID)"
                  id="m365_client_id"
                  value={formData.m365_client_id}
                  onChange={handleChange('m365_client_id')}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  required
                />
                <InputField
                  label="Client Secret"
                  id="m365_client_secret"
                  type="password"
                  value={formData.m365_client_secret}
                  onChange={handleChange('m365_client_secret')}
                  placeholder="Your M365 app registration secret"
                  required
                />
              </>
            )}
          </div>

          {/* Message */}
          {message && (
            <div
              className={`mx-6 mb-4 flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                message.type === 'success'
                  ? 'bg-green-900/50 text-green-300 border border-green-700'
                  : 'bg-red-900/50 text-red-300 border border-red-700'
              }`}
            >
              {message.type === 'success' ? (
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
              )}
              {message.text}
            </div>
          )}

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-700 flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed rounded-lg flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Configuration
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ConfigModal;
