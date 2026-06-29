import React, { useState, useEffect } from 'react';
import {
  Save,
  Key,
  Globe,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';

interface ConfigItem {
  key: string;
  value: string;
  description: string | null;
}

interface DomainItem {
  id: number;
  domain: string;
  from_email: string;
  weight: number;
  is_active: boolean;
}

interface MasterSettingsProps {
  isDark: boolean;
}

export const MasterSettings: React.FC<MasterSettingsProps> = ({ isDark }) => {
  const [_, setConfigs] = useState<ConfigItem[]>([]);
  const [domains, setDomains] = useState<DomainItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  // Form states for API key modifications
  const [stripeKey, setStripeKey] = useState<string>('');
  const [geminiKeys, setGeminiKeys] = useState<string>('');
  const [tavilyKey, setTavilyKey] = useState<string>('');
  const [firecrawlKey, setFirecrawlKey] = useState<string>('');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      // 1. Fetch system configurations
      try {
        const configRes = await api.get('/settings');
        setConfigs(configRes.data);

        const stripe = configRes.data.find((c: any) => c.key === 'STRIPE_API_KEY');
        const gemini = configRes.data.find((c: any) => c.key === 'GEMINI_API_KEY');
        const tavily = configRes.data.find((c: any) => c.key === 'TAVILY_API_KEY');
        const firecrawl = configRes.data.find((c: any) => c.key === 'FIRECRAWL_API_KEY');

        if (stripe) setStripeKey(stripe.value);
        if (gemini) setGeminiKeys(gemini.value);
        if (tavily) setTavilyKey(tavily.value);
        if (firecrawl) setFirecrawlKey(firecrawl.value);
      } catch (configErr) {
        console.error('Failed to load credentials:', configErr);
      }

      // 2. Fetch sender domains
      try {
        const domainRes = await api.get('/settings/domains');
        if (domainRes.data) {
          setDomains(domainRes.data);
        }
      } catch (domainErr) {
        console.error('Failed to load domains:', domainErr);
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (key: string, value: string, desc: string) => {
    setSavingKey(key);
    try {
      await api.post('/settings', { key, value, description: desc });
      alert(`Configuration Parameter '${key}' encrypted and saved securely in Supabase.`);
      await fetchSettings();
    } catch (err) {
      alert('Failed to save configuration settings.');
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* View Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold font-sans">Master Settings Console</h1>
          <p className="text-xs text-google-textMuted mt-1">Configure Stripe billing keys, LLM credentials, and active email sender domain matrixes.</p>
        </div>
        <button
          onClick={fetchSettings}
          className={`p-2 rounded border transition-colors cursor-pointer ${isDark
              ? 'bg-google-cardDark border-google-borderDark hover:bg-google-borderDark text-gray-300'
              : 'bg-white border-gray-200 hover:bg-gray-50 text-gray-700'
            }`}
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">

        {/* Left Column: API Keys Forms (col-span-7) */}
        <div className={`lg:col-span-7 border rounded-lg overflow-hidden flex flex-col shadow-sm ${isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
          }`}>
          <div className="p-4 border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30 flex items-center gap-2">
            <Key size={16} className="text-google-blue" />
            <h2 className="text-xs font-semibold uppercase tracking-wider font-mono text-google-textMuted">Encrypted API Credentials Manager</h2>
          </div>

          <div className="p-6 space-y-6 font-mono text-xs max-h-[500px] overflow-y-auto">
            {/* Stripe API Key form */}
            <div className="space-y-2 border-b border-google-borderDark/10 pb-4">
              <div className="flex justify-between items-center">
                <label className="font-bold text-gray-300">Stripe Secret Key (STRIPE_API_KEY)</label>
                <button
                  onClick={() => handleSaveConfig('STRIPE_API_KEY', stripeKey, 'Stripe Secret integration key')}
                  disabled={savingKey === 'STRIPE_API_KEY'}
                  className="flex items-center gap-1 bg-google-blue hover:bg-google-blueDark text-white px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Save size={10} />
                  <span>{savingKey === 'STRIPE_API_KEY' ? 'Saving...' : 'Save'}</span>
                </button>
              </div>
              <input
                type="password"
                value={stripeKey}
                onChange={(e) => setStripeKey(e.target.value)}
                placeholder="sk_test_..."
                className={`w-full px-3 py-2 text-xs rounded border focus:outline-none focus:ring-1 focus:ring-google-blue font-mono ${isDark ? 'bg-google-sidebarDark border-google-borderDark text-gray-100' : 'bg-white border-gray-200 text-gray-800'
                  }`}
              />
            </div>

            {/* Gemini API Keys form */}
            <div className="space-y-2 border-b border-google-borderDark/10 pb-4">
              <div className="flex justify-between items-center">
                <label className="font-bold text-gray-300">Google Gemini API Keys (GEMINI_API_KEY)</label>
                <button
                  onClick={() => handleSaveConfig('GEMINI_API_KEY', geminiKeys, 'Google Gemini model keys list')}
                  disabled={savingKey === 'GEMINI_API_KEY'}
                  className="flex items-center gap-1 bg-google-blue hover:bg-google-blueDark text-white px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Save size={10} />
                  <span>{savingKey === 'GEMINI_API_KEY' ? 'Saving...' : 'Save'}</span>
                </button>
              </div>
              <textarea
                value={geminiKeys}
                onChange={(e) => setGeminiKeys(e.target.value)}
                rows={2}
                placeholder="Key1, Key2..."
                className={`w-full px-3 py-2 text-xs rounded border focus:outline-none focus:ring-1 focus:ring-google-blue font-mono ${isDark ? 'bg-google-sidebarDark border-google-borderDark text-gray-100' : 'bg-white border-gray-200 text-gray-800'
                  }`}
              />
            </div>

            {/* Tavily API Key form */}
            <div className="space-y-2 border-b border-google-borderDark/10 pb-4">
              <div className="flex justify-between items-center">
                <label className="font-bold text-gray-300">Tavily Search API Key (TAVILY_API_KEY)</label>
                <button
                  onClick={() => handleSaveConfig('TAVILY_API_KEY', tavilyKey, 'Tavily Search API key')}
                  disabled={savingKey === 'TAVILY_API_KEY'}
                  className="flex items-center gap-1 bg-google-blue hover:bg-google-blueDark text-white px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Save size={10} />
                  <span>{savingKey === 'TAVILY_API_KEY' ? 'Saving...' : 'Save'}</span>
                </button>
              </div>
              <input
                type="password"
                value={tavilyKey}
                onChange={(e) => setTavilyKey(e.target.value)}
                placeholder="tvly-..."
                className={`w-full px-3 py-2 text-xs rounded border focus:outline-none focus:ring-1 focus:ring-google-blue font-mono ${isDark ? 'bg-google-sidebarDark border-google-borderDark text-gray-100' : 'bg-white border-gray-200 text-gray-800'
                  }`}
              />
            </div>

            {/* Firecrawl API Key form */}
            <div className="space-y-2 pb-4">
              <div className="flex justify-between items-center">
                <label className="font-bold text-gray-300">Firecrawl API Key (FIRECRAWL_API_KEY)</label>
                <button
                  onClick={() => handleSaveConfig('FIRECRAWL_API_KEY', firecrawlKey, 'Firecrawl Scraper API key')}
                  disabled={savingKey === 'FIRECRAWL_API_KEY'}
                  className="flex items-center gap-1 bg-google-blue hover:bg-google-blueDark text-white px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Save size={10} />
                  <span>{savingKey === 'FIRECRAWL_API_KEY' ? 'Saving...' : 'Save'}</span>
                </button>
              </div>
              <input
                type="password"
                value={firecrawlKey}
                onChange={(e) => setFirecrawlKey(e.target.value)}
                placeholder="fc-..."
                className={`w-full px-3 py-2 text-xs rounded border focus:outline-none focus:ring-1 focus:ring-google-blue font-mono ${isDark ? 'bg-google-sidebarDark border-google-borderDark text-gray-100' : 'bg-white border-gray-200 text-gray-800'
                  }`}
              />
            </div>
          </div>
        </div>

        {/* Right Column: Domains Weightings (col-span-5) */}
        <div className={`lg:col-span-5 border rounded-lg overflow-hidden flex flex-col shadow-sm ${isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
          }`}>
          <div className="p-4 border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30 flex items-center gap-2">
            <Globe size={16} className="text-google-blue" />
            <h2 className="text-xs font-semibold uppercase tracking-wider font-mono text-google-textMuted">Domain Sender Weights</h2>
          </div>

          <div className="flex-1 overflow-auto max-h-[500px]">
            {domains.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center h-48 space-y-2">
                <Globe size={24} className="text-google-textMuted" />
                <span className="text-xs text-google-textMuted font-mono">No sender domains seeded.</span>
              </div>
            ) : (
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b dark:border-google-borderDark bg-gray-50/20 dark:bg-google-sidebarDark/10 text-google-textMuted font-mono uppercase text-[10px]">
                    <th className="p-3">Domain</th>
                    <th className="p-3">Weight</th>
                    <th className="p-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-google-borderDark/10 font-mono">
                  {domains.map((d) => (
                    <tr key={d.id} className="hover:bg-gray-50/20 dark:hover:bg-google-borderDark/10">
                      <td className="p-3 font-semibold">{d.domain}</td>
                      <td className="p-3">{d.weight}%</td>
                      <td className="p-3 text-right">
                        {d.is_active ? (
                          <span className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold text-[10px] uppercase">
                            ACTIVE
                          </span>
                        ) : (
                          <span className="bg-red-500/10 text-red-400 px-2 py-0.5 rounded font-bold text-[10px] uppercase">
                            BLOCKED
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
