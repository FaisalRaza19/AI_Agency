import React, { useState, useEffect } from 'react';
import { 
  Wallet, 
  RefreshCw, 
  ShieldAlert
} from 'lucide-react';
import { api } from '../services/api';

interface WalletItem {
  id: string;
  name: string;
  budget: number;
  cost_spent: number;
  is_liquidated: boolean;
}

interface WalletGuardrailsProps {
  isDark: boolean;
}

export const WalletGuardrails: React.FC<WalletGuardrailsProps> = ({ isDark }) => {
  const [wallets, setWallets] = useState<WalletItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchWallets();
  }, []);

  const fetchWallets = async () => {
    setLoading(true);
    try {
      const res = await api.get('/campaigns');
      // Format response list to fetch wallet parameters
      const mapped = res.data.map((c: any) => ({
        id: c.id,
        name: c.name,
        budget: c.budget,
        cost_spent: c.cost_spent,
        is_liquidated: c.is_liquidated
      }));
      setWallets(mapped);
    } catch (err) {
      console.error('Failed to load wallets:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFreeze = async (walletId: string, currentFreeze: boolean) => {
    setActionLoading(walletId);
    try {
      // Endpoint pause/resume acts as local budget freeze toggles
      const action = currentFreeze ? 'resume' : 'pause';
      await api.post(`/campaigns/${walletId}/${action}`);
      alert(`Wallet allocation successfully ${currentFreeze ? 'unfrozen' : 'frozen/liquidated'}!`);
      await fetchWallets();
    } catch (err) {
      alert('Failed to modify wallet liquidation status.');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* View Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold font-sans">Wallet & Guardrails</h1>
          <p className="text-xs text-google-textMuted mt-1">Manage budget caps, outbound key slot allocations, and liquidation guardrails.</p>
        </div>
        <button 
          onClick={fetchWallets} 
          className={`p-2 rounded border transition-colors cursor-pointer ${
            isDark 
              ? 'bg-google-cardDark border-google-borderDark hover:bg-google-borderDark text-gray-300' 
              : 'bg-white border-gray-200 hover:bg-gray-50 text-gray-700'
          }`}
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* Left Column: Wallets table (col-span-8) */}
        <div className={`lg:col-span-8 border rounded-lg overflow-hidden flex flex-col shadow-sm ${
          isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
        }`}>
          <div className="p-4 border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30">
            <h2 className="text-xs font-semibold uppercase tracking-wider font-mono text-google-textMuted">Operational Wallet Registry</h2>
          </div>

          <div className="flex-1 overflow-auto max-h-[450px]">
            {wallets.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center h-48 space-y-2">
                <Wallet size={28} className="text-google-textMuted" />
                <span className="text-xs text-google-textMuted font-mono">No operational wallets configured. Create a campaign to assign a wallet.</span>
              </div>
            ) : (
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b dark:border-google-borderDark bg-gray-50/20 dark:bg-google-sidebarDark/10 text-google-textMuted font-mono uppercase text-[10px]">
                    <th className="p-3">Campaign Channel</th>
                    <th className="p-3">Budget Allocation</th>
                    <th className="p-3">Burn Spent</th>
                    <th className="p-3 text-center">Guardrail Status</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-google-borderDark/10 font-mono">
                  {wallets.map((w) => (
                    <tr key={w.id} className="hover:bg-gray-50/20 dark:hover:bg-google-borderDark/10">
                      <td className="p-3 font-semibold">{w.name}</td>
                      <td className="p-3">${w.budget.toFixed(2)}</td>
                      <td className="p-3">${w.cost_spent.toFixed(2)}</td>
                      <td className="p-3 text-center">
                        {w.is_liquidated ? (
                          <span className="bg-red-500/10 text-red-400 px-2 py-0.5 rounded font-bold text-[10px] uppercase">
                            LIQUIDATED / FROZEN
                          </span>
                        ) : (
                          <span className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold text-[10px] uppercase">
                            LIQUID SAFE
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => handleToggleFreeze(w.id, w.is_liquidated)}
                          disabled={actionLoading === w.id}
                          className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase cursor-pointer transition-colors ${
                            w.is_liquidated 
                              ? 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' 
                              : 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                          }`}
                        >
                          {w.is_liquidated ? 'Unfreeze' : 'Freeze'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right Column: Guardrails configuration definitions (col-span-4) */}
        <div className={`lg:col-span-4 p-5 border rounded-lg shadow-sm flex flex-col justify-between ${
          isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
        }`}>
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider font-mono text-google-textMuted flex items-center gap-2">
              <ShieldAlert size={16} className="text-google-blue" />
              Active System Guardrails
            </h3>

            <div className="space-y-3 font-mono text-xs text-gray-300">
              <div className="p-3 rounded border dark:border-google-borderDark/10 bg-gray-50/10 dark:bg-google-sidebarDark/20">
                <p className="font-bold text-google-blue">Max Burn Threshold</p>
                <p className="mt-1 text-[11px] text-google-textMuted">Automatically suspends a campaign channel if cost burn exceeds 95% of total budget limit.</p>
              </div>

              <div className="p-3 rounded border dark:border-google-borderDark/10 bg-gray-50/10 dark:bg-google-sidebarDark/20">
                <p className="font-bold text-google-blue">Dynamic Rate Limiter</p>
                <p className="mt-1 text-[11px] text-google-textMuted">Caps outgoing emails to a maximum of 50 per hour per domain slot to prevent spam listings.</p>
              </div>

              <div className="p-3 rounded border dark:border-google-borderDark/10 bg-gray-50/10 dark:bg-google-sidebarDark/20">
                <p className="font-bold text-google-blue">HNSW Multi-Vector Safety</p>
                <p className="mt-1 text-[11px] text-google-textMuted">Flags duplicate leads dynamically to maintain high qualification standards.</p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
