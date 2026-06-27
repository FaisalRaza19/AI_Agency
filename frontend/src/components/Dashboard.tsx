import React from 'react';
import { 
  TrendingUp, 
  Users, 
  Activity, 
  AlertTriangle, 
  CheckCircle,
  Clock
} from 'lucide-react';
import { LogStreamer } from './LogStreamer';
import type { LogEntry } from './LogStreamer';

export interface WalletState {
  campaign_id: string;
  budget: number;
  cost_spent: number;
  is_liquidated: boolean;
}

export interface LeadState {
  id: string;
  email: string;
  company: string;
  outreach_status: string;
  score: number;
}

interface DashboardProps {
  wallet: WalletState | null;
  leads: LeadState[];
  logs: LogEntry[];
  onClearLogs: () => void;
  isDark: boolean;
  wsStatus: 'connecting' | 'connected' | 'disconnected';
  activeKeyIdx: number;
}

export const Dashboard: React.FC<DashboardProps> = ({
  wallet,
  leads,
  logs,
  onClearLogs,
  isDark,
  wsStatus,
  activeKeyIdx
}) => {
  // Calculations
  const totalLeads = leads.length;
  const activeNegotiations = leads.filter(l => 
    l.outreach_status === 'IN_LIVE_NEGOTIATION' || l.outreach_status === 'CONTRACT_PENDING'
  ).length;

  const budget = wallet ? wallet.budget : 100.0;
  const spent = wallet ? wallet.cost_spent : 0.0;
  const usageRatio = budget > 0 ? (spent / budget) : 0;
  const usagePercent = Math.min(100, Math.round(usageRatio * 100));

  // Determine progress bar color based on ROI safety thresholds
  const getProgressBarColor = () => {
    if (usageRatio >= 0.75) return 'bg-red-500';
    if (usageRatio >= 0.50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'IN_LIVE_NEGOTIATION':
        return <span className="bg-blue-100 text-blue-800 text-[11px] font-semibold px-2 py-0.5 rounded dark:bg-blue-900/30 dark:text-blue-300">Live Negotiation</span>;
      case 'CONTRACT_PENDING':
        return <span className="bg-purple-100 text-purple-800 text-[11px] font-semibold px-2 py-0.5 rounded dark:bg-purple-900/30 dark:text-purple-300">Contract Pending</span>;
      case 'declined':
        return <span className="bg-red-100 text-red-800 text-[11px] font-semibold px-2 py-0.5 rounded dark:bg-red-900/30 dark:text-red-300">Declined</span>;
      case 'email_sent':
        return <span className="bg-yellow-100 text-yellow-800 text-[11px] font-semibold px-2 py-0.5 rounded dark:bg-yellow-900/30 dark:text-yellow-300">Email Sent</span>;
      default:
        return <span className="bg-gray-100 text-gray-800 text-[11px] font-semibold px-2 py-0.5 rounded dark:bg-gray-800 dark:text-gray-300">Pending</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Dashboard Top Health bar */}
      <div className={`flex flex-wrap justify-between items-center border p-4 rounded-lg shadow-sm ${
        isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
      }`}>
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold font-sans">UABE Control Panel</h1>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full status-indicator ${
              wsStatus === 'connected' ? 'bg-green-500' : wsStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
            }`} />
            <span className="text-google-textMuted text-xs font-mono uppercase">
              Websocket: {wsStatus}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-6 text-sm font-mono text-google-textMuted">
          <div>
            <span>ACTIVE KEY SLOT: </span>
            <span className="text-google-blue font-bold">#{activeKeyIdx}</span>
          </div>
          <div>
            <span>ENGINE STATE: </span>
            <span className="text-green-500 font-bold">ONLINE</span>
          </div>
        </div>
      </div>

      {/* Analytics Matrix Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Budget Gate */}
        <div className={`border p-5 rounded-lg shadow-sm flex flex-col justify-between h-48 ${
          isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
        }`}>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-google-textMuted text-xs font-semibold uppercase tracking-wider">Campaign Wallet</p>
              <h2 className="text-2xl font-bold mt-1">${spent.toFixed(2)} / ${budget.toFixed(2)}</h2>
            </div>
            <div className={`p-2 rounded-lg bg-google-blue/10 text-google-blue`}>
              <TrendingUp size={20} />
            </div>
          </div>
          
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-xs text-google-textMuted font-mono">
              <span>Budget Usage</span>
              <span>{usagePercent}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 h-2.5 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${getProgressBarColor()}`}
                style={{ width: `${usagePercent}%` }}
              />
            </div>
          </div>

          <div className="flex items-center gap-1.5 mt-2 text-xs">
            {usageRatio >= 0.75 ? (
              activeNegotiations > 0 ? (
                <div className="flex items-center gap-1 text-purple-500">
                  <CheckCircle size={12} />
                  <span>Bypassed Freeze: Live Deals Active</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-red-500">
                  <AlertTriangle size={12} />
                  <span>Campaign Frozen: No Warm Leads</span>
                </div>
              )
            ) : (
              <div className="flex items-center gap-1 text-green-500">
                <CheckCircle size={12} />
                <span>Wallet Safe (ROI Threshold Normal)</span>
              </div>
            )}
          </div>
        </div>

        {/* Card 2: Active Leads / negotiations */}
        <div className={`border p-5 rounded-lg shadow-sm flex flex-col justify-between h-48 ${
          isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
        }`}>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-google-textMuted text-xs font-semibold uppercase tracking-wider">Active Deals</p>
              <h2 className="text-2xl font-bold mt-1">{activeNegotiations} / {totalLeads}</h2>
            </div>
            <div className="p-2 rounded-lg bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400">
              <Users size={20} />
            </div>
          </div>

          <div className="space-y-1.5 mt-3">
            <div className="flex justify-between text-xs font-mono text-google-textMuted">
              <span>Outbound Conversion Rate</span>
              <span>{totalLeads > 0 ? Math.round((activeNegotiations / totalLeads) * 100) : 0}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 h-2.5 rounded-full overflow-hidden">
              <div 
                className="h-full bg-purple-500 rounded-full"
                style={{ width: `${totalLeads > 0 ? (activeNegotiations / totalLeads) * 100 : 0}%` }}
              />
            </div>
          </div>

          <div className="flex items-center gap-1.5 mt-2 text-xs text-google-textMuted font-mono">
            <Clock size={12} />
            <span>Outreach metrics synced dynamically</span>
          </div>
        </div>

        {/* Card 3: Leads List summary */}
        <div className={`border p-4 rounded-lg shadow-sm flex flex-col h-48 overflow-y-auto ${
          isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-center gap-2 mb-2 border-b pb-1.5 border-gray-200 dark:border-google-borderDark">
            <Activity size={14} className="text-google-blue" />
            <span className="text-xs font-semibold uppercase tracking-wider text-google-textMuted">Live Leads Registry</span>
          </div>
          
          <div className="space-y-2 flex-1">
            {leads.length === 0 ? (
              <div className="text-xs text-google-textMuted text-center mt-6">
                No active outreach targets loaded.
              </div>
            ) : (
              leads.slice(0, 3).map((lead) => (
                <div key={lead.id} className="flex justify-between items-center text-xs">
                  <div className="truncate pr-2">
                    <p className="font-semibold truncate">{lead.company}</p>
                    <p className="text-[10px] text-google-textMuted truncate">{lead.email}</p>
                  </div>
                  <div>
                    {getStatusBadge(lead.outreach_status)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Streaming Log Console */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-google-textMuted">Live Orchestrator Telemetry</h3>
        <LogStreamer logs={logs} onClearLogs={onClearLogs} isDark={isDark} />
      </div>
    </div>
  );
};
