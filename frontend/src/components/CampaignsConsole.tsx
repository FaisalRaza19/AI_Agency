import React, { useState, useEffect } from 'react';
import {
  Megaphone,
  Plus,
  Play,
  Pause,
  RefreshCw,
  Users,
  DollarSign,
  Compass,
  Activity,
  AlertTriangle,
  FolderOpen
} from 'lucide-react';
import { api } from '../services/api';

interface CampaignItem {
  id: string;
  name: string;
  objective: string;
  status: string;
  created_at: string;
  budget: number;
  cost_spent: number;
  is_liquidated: boolean;
}

interface LeadItem {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  company: string | null;
  phone: string | null;
  qualification_score: number;
  verification_status: string;
  outreach_status: string;
}

interface LogItem {
  id: number;
  agent_name: string;
  log_level: string;
  message: string;
  created_at: string;
}

interface CampaignsConsoleProps {
  isDark: boolean;
}

export const CampaignsConsole: React.FC<CampaignsConsoleProps> = ({ isDark }) => {
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<CampaignItem | null>(null);
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [campaignLogs, setCampaignLogs] = useState<LogItem[]>([]);

  // Modals & Forms
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [name, setName] = useState<string>('');
  const [objective, setObjective] = useState<string>('');
  const [budget, setBudget] = useState<number>(100.0);

  // Statuses
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Closer Call Simulation States
  const [showCloserModal, setShowCloserModal] = useState<boolean>(false);
  const [closerTranscript, setCloserTranscript] = useState<string>('');
  const [closerSummary, setCloserSummary] = useState<string>('');
  const [closerAgreed, setCloserAgreed] = useState<boolean>(false);
  const [closerPrice, setCloserPrice] = useState<number>(0);
  const [closerCheckout, setCloserCheckout] = useState<string>('');

  // Phase 6: Deliverables & QA States
  interface DeliverableItem {
    id: string;
    campaign_id: string;
    lead_id: string | null;
    title: string;
    content_type: string;
    content_body: string;
    image_url: string | null;
    status: string;
    refinement_count: number;
    qa_feedback: string | null;
    created_at: string;
  }
  const [activePanelTab, setActivePanelTab] = useState<'leads' | 'deliverables' | 'reflection'>('leads');
  const [deliverables, setDeliverables] = useState<DeliverableItem[]>([]);
  const [deliverablesLoading, setDeliverablesLoading] = useState<boolean>(false);
  const [selectedDeliverable, setSelectedDeliverable] = useState<DeliverableItem | null>(null);
  const [showDeliverableModal, setShowDeliverableModal] = useState<boolean>(false);
  const [rebuildFeedback, setRebuildFeedback] = useState<string>('');
  const [rebuildingId, setRebuildingId] = useState<string | null>(null);
  const [generatingType, setGeneratingType] = useState<string | null>(null);

  interface ReflectionLogItem {
    id: number;
    campaign_id: string | null;
    agent_name: string;
    log_level: string;
    message: string;
    is_reflection: boolean;
    created_at: string;
  }
  const [reflectionLogs, setReflectionLogs] = useState<ReflectionLogItem[]>([]);
  const [reflectionLoading, setReflectionLoading] = useState<boolean>(false);

  useEffect(() => {
    fetchCampaigns();
  }, []);

  useEffect(() => {
    if (selectedCampaign) {
      fetchCampaignDetails(selectedCampaign.id);
      fetchCampaignDeliverables(selectedCampaign.id);
      fetchReflectionLogs(selectedCampaign.id);
    } else {
      setLeads([]);
      setCampaignLogs([]);
      setDeliverables([]);
      setReflectionLogs([]);
    }
  }, [selectedCampaign]);

  const fetchCampaigns = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/campaigns');
      setCampaigns(res.data);
      if (res.data.length > 0 && !selectedCampaign) {
        setSelectedCampaign(res.data[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch campaigns.');
    } finally {
      setLoading(false);
    }
  };

  const fetchCampaignDetails = async (campaignId: string) => {
    try {
      const [leadsRes, logsRes] = await Promise.all([
        api.get(`/campaigns/${campaignId}/leads`),
        api.get(`/campaigns/${campaignId}/logs`)
      ]);
      setLeads(leadsRes.data);
      setCampaignLogs(logsRes.data);
    } catch (err) {
      console.error('Failed to load campaign details:', err);
    }
  };

  const fetchCampaignDeliverables = async (campaignId: string) => {
    setDeliverablesLoading(true);
    try {
      const res = await api.get(`/campaigns/${campaignId}/deliverables`);
      setDeliverables(res.data);
    } catch (err) {
      console.error('Failed to load deliverables:', err);
    } finally {
      setDeliverablesLoading(false);
    }
  };

  const fetchReflectionLogs = async (campaignId: string) => {
    try {
      const res = await api.get(`/campaigns/${campaignId}/reflection-logs`);
      setReflectionLogs(res.data);
    } catch (err) {
      console.error('Failed to load reflection logs:', err);
    }
  };

  const handleTriggerReflection = async () => {
    if (!selectedCampaign) return;
    setReflectionLoading(true);
    try {
      await api.post(`/campaigns/${selectedCampaign.id}/reflect`);
      await Promise.all([
        fetchReflectionLogs(selectedCampaign.id),
        fetchCampaignDetails(selectedCampaign.id)
      ]);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Reflection loop failed.');
    } finally {
      setReflectionLoading(false);
    }
  };

  const handleGenerateDeliverable = async (contentType: string) => {
    if (!selectedCampaign) return;
    setGeneratingType(contentType);
    try {
      const res = await api.post(`/campaigns/${selectedCampaign.id}/deliverables/generate`, {
        content_type: contentType
      });
      setDeliverables((prev) => [res.data, ...prev]);
      alert(`Deliverable successfully compiled! Status: ${res.data.status}`);
      await fetchCampaignDetails(selectedCampaign.id);
    } catch (err) {
      console.error('Generation error:', err);
      alert('Failed to generate deliverable copywriting.');
    } finally {
      setGeneratingType(null);
    }
  };

  const handleRebuildDeliverable = async (deliverableId: string) => {
    if (!selectedCampaign) return;
    setRebuildingId(deliverableId);
    try {
      const res = await api.post(`/campaigns/${selectedCampaign.id}/deliverables/${deliverableId}/rebuild`, {
        custom_feedback: rebuildFeedback
      });
      setDeliverables((prev) =>
        prev.map((d) => (d.id === deliverableId ? res.data : d))
      );
      if (selectedDeliverable && selectedDeliverable.id === deliverableId) {
        setSelectedDeliverable(res.data);
      }
      setRebuildFeedback('');
      alert(`Deliverable successfully rebuilt and re-validated! New status: ${res.data.status}`);
      await fetchCampaignDetails(selectedCampaign.id);
    } catch (err) {
      console.error('Rebuild error:', err);
      alert('Failed to rebuild deliverable.');
    } finally {
      setRebuildingId(null);
    }
  };

  const handleOpenDeliverableDetail = (deliv: DeliverableItem) => {
    setSelectedDeliverable(deliv);
    setShowDeliverableModal(true);
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const res = await api.post('/campaigns', { name, objective, budget });
      setCampaigns((prev) => [res.data, ...prev]);
      setSelectedCampaign(res.data);
      setShowCreateModal(false);
      setName('');
      setObjective('');
      setBudget(100.0);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create campaign.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (campaign: CampaignItem) => {
    setActionLoading(campaign.id);
    const action = campaign.status === 'active' ? 'pause' : 'resume';
    try {
      const res = await api.post(`/campaigns/${campaign.id}/${action}`);
      setCampaigns((prev) =>
        prev.map((c) => (c.id === campaign.id ? res.data : c))
      );
      setSelectedCampaign(res.data);
    } catch (err) {
      console.error('Failed to toggle campaign status:', err);
    } finally {
      setActionLoading(null);
    }
  };
  const handleSimulateCloser = async (leadId: string) => {
    if (!selectedCampaign) return;
    setActionLoading(leadId);
    setError('');
    try {
      const res = await api.post(`/campaigns/${selectedCampaign.id}/leads/${leadId}/simulate-closer`);
      setCloserTranscript(res.data.transcript);
      setCloserSummary(res.data.summary);
      setCloserAgreed(res.data.is_agreed);
      setCloserPrice(res.data.agreed_price);
      setCloserCheckout(res.data.checkout_url || '');
      setShowCloserModal(true);
      
      // Refresh details
      await fetchCampaignDetails(selectedCampaign.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to simulate closer call.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleViewContract = async (leadId: string, _company: string) => {
    if (!selectedCampaign) return;
    try {
      const res = await api.get(`/campaigns/${selectedCampaign.id}/leads/${leadId}/contract`, {
        responseType: 'blob'
      });
      const file = new Blob([res.data], { type: 'text/html' });
      const fileURL = URL.createObjectURL(file);
      window.open(fileURL, '_blank');
    } catch (err) {
      console.error('Failed to view contract:', err);
      alert('Failed to retrieve signed contract SLA.');
    }
  };

  const handleMockPayment = async (leadId: string) => {
    if (!selectedCampaign) return;
    try {
      const mockPayload = {
        id: `evt_test_payment_${Math.random().toString(36).substr(2, 9)}`,
        type: 'checkout.session.completed',
        data: {
          object: {
            id: 'cs_test_session',
            metadata: {
              lead_id: leadId,
              campaign_id: selectedCampaign.id
            }
          }
        }
      };
      await api.post('/billing/webhook', mockPayload, {
        headers: {
          'stripe-signature': 'mock_signature'
        }
      });
      alert('Mock payment webhook completed successfully! Status updated to Closed Won.');
      await fetchCampaignDetails(selectedCampaign.id);
    } catch (err) {
      console.error('Mock payment error:', err);
      alert('Mock payment webhook failed.');
    }
  };


  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return (
          <span className="flex items-center gap-1.5 bg-green-500/10 text-green-400 text-xs px-2 py-0.5 rounded font-mono uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Active
          </span>
        );
      case 'paused':
        return (
          <span className="flex items-center gap-1.5 bg-yellow-500/10 text-yellow-400 text-xs px-2 py-0.5 rounded font-mono uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
            Paused
          </span>
        );
      case 'interrupted':
        return (
          <span className="flex items-center gap-1.5 bg-red-500/10 text-red-400 text-xs px-2 py-0.5 rounded font-mono uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
            Frozen
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 bg-gray-500/10 text-gray-400 text-xs px-2 py-0.5 rounded font-mono uppercase tracking-wider">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* View Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold font-sans">Campaigns Console</h1>
          <p className="text-xs text-google-textMuted mt-1">Configure business objectives, manage budget allocations, and launch outbound agents.</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={fetchCampaigns}
            className={`p-2 rounded border transition-colors ${isDark
                ? 'bg-google-cardDark border-google-borderDark hover:bg-google-borderDark text-gray-300'
                : 'bg-white border-gray-200 hover:bg-gray-50 text-gray-700'
              }`}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 bg-google-blue hover:bg-google-blueDark text-white px-4 py-2 rounded text-sm font-semibold transition-colors shadow-sm"
          >
            <Plus size={16} />
            <span>Launch Campaign</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded text-sm font-mono">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Main Console Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">

        {/* Left Column: Campaigns List (col-span-5) */}
        <div className={`lg:col-span-5 flex flex-col border rounded-lg overflow-hidden shadow-sm ${isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
          }`}>
          <div className="p-4 border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30">
            <h2 className="text-sm font-semibold uppercase tracking-wider font-mono text-google-textMuted">Operational Channels</h2>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-google-borderDark/10">
            {campaigns.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center h-48 space-y-2">
                <Megaphone size={28} className="text-google-textMuted" />
                <span className="text-sm text-google-textMuted font-mono">No campaigns registered. Click "Launch Campaign" to start.</span>
              </div>
            ) : (
              campaigns.map((c) => {
                const isSelected = selectedCampaign?.id === c.id;
                const progress = c.budget > 0 ? (c.cost_spent / c.budget) * 100 : 0;
                return (
                  <div
                    key={c.id}
                    onClick={() => setSelectedCampaign(c)}
                    className={`p-4 cursor-pointer transition-all ${isSelected
                        ? 'bg-google-blue/5 dark:bg-google-blue/10 border-l-4 border-google-blue'
                        : 'hover:bg-gray-50/50 dark:hover:bg-google-borderDark/20'
                      }`}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <h3 className="font-bold text-sm">{c.name}</h3>
                        <p className="text-xs text-google-textMuted line-clamp-1 mt-0.5">{c.objective}</p>
                      </div>
                      {getStatusBadge(c.status)}
                    </div>

                    {/* Cost Progress Indicator */}
                    <div className="mt-3 space-y-1">
                      <div className="flex justify-between text-[11px] font-mono text-google-textMuted">
                        <span>Spent: ${c.cost_spent.toFixed(2)}</span>
                        <span>Limit: ${c.budget.toFixed(0)}</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-google-borderDark h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${progress >= 90 ? 'bg-red-500' : progress >= 75 ? 'bg-yellow-500' : 'bg-google-blue'
                            }`}
                          style={{ width: `${Math.min(100, progress)}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex justify-between items-center mt-3 pt-2 border-t border-google-borderDark/10">
                      <span className="text-[10px] font-mono text-google-textMuted uppercase">
                        ID: {c.id.substring(0, 8)}...
                      </span>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleStatus(c);
                        }}
                        disabled={actionLoading === c.id}
                        className={`flex items-center gap-1 text-[11px] font-bold uppercase font-mono px-2 py-1 rounded transition-colors ${c.status === 'active'
                            ? 'text-yellow-500 hover:bg-yellow-500/10'
                            : 'text-green-500 hover:bg-green-500/10'
                          }`}
                      >
                        {c.status === 'active' ? (
                          <>
                            <Pause size={10} />
                            <span>Pause</span>
                          </>
                        ) : (
                          <>
                            <Play size={10} />
                            <span>Resume</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Campaign details (col-span-7) */}
        <div className="lg:col-span-7 flex flex-col space-y-6">

          {selectedCampaign ? (
            <>
              {/* Campaign Header Details */}
              <div className={`p-5 border rounded-lg shadow-sm ${isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
                }`}>
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted">Selected Campaign Profile</span>
                    <h2 className="text-lg font-bold mt-0.5">{selectedCampaign.name}</h2>
                  </div>
                  {getStatusBadge(selectedCampaign.status)}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5 pt-4 border-t border-google-borderDark/20">
                  <div className="flex items-center gap-2">
                    <Compass className="text-google-blue" size={16} />
                    <div className="text-xs">
                      <p className="text-google-textMuted font-mono uppercase text-[10px]">Budget Cap</p>
                      <p className="font-bold">${selectedCampaign.budget.toFixed(2)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <DollarSign className="text-google-blue" size={16} />
                    <div className="text-xs">
                      <p className="text-google-textMuted font-mono uppercase text-[10px]">Cost Burned</p>
                      <p className="font-bold">${selectedCampaign.cost_spent.toFixed(2)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Users className="text-google-blue" size={16} />
                    <div className="text-xs">
                      <p className="text-google-textMuted font-mono uppercase text-[10px]">Qualified Leads</p>
                      <p className="font-bold">{leads.length}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 p-3 rounded text-xs bg-gray-50/50 dark:bg-google-sidebarDark/30 border dark:border-google-borderDark/10">
                  <p className="font-bold font-mono text-[10px] uppercase text-google-textMuted">Business Objective Instruction</p>
                  <p className="mt-1 text-gray-700 dark:text-gray-300 leading-relaxed font-mono">{selectedCampaign.objective}</p>
                </div>
              </div>

              {/* Leads Registry / Asset Deliverables Tabbed Panel */}
              <div className={`flex-1 border rounded-lg overflow-hidden flex flex-col shadow-sm min-h-[400px] ${isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
                }`}>
                <div className="border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30 flex justify-between items-center px-4">
                  <div className="flex gap-4">
                    <button
                      onClick={() => setActivePanelTab('leads')}
                      className={`py-3 text-xs font-bold uppercase tracking-wider font-mono cursor-pointer border-b-2 transition-all ${
                        activePanelTab === 'leads'
                          ? 'border-google-blue text-google-blue'
                          : 'border-transparent text-google-textMuted hover:text-white'
                      }`}
                    >
                      Leads Registry ({leads.length})
                    </button>
                    <button
                      onClick={() => setActivePanelTab('deliverables')}
                      className={`py-3 text-xs font-bold uppercase tracking-wider font-mono cursor-pointer border-b-2 transition-all ${
                        activePanelTab === 'deliverables'
                          ? 'border-google-blue text-google-blue'
                          : 'border-transparent text-google-textMuted hover:text-white'
                      }`}
                    >
                      Asset Deliverables ({deliverables.length})
                    </button>
                    <button
                      onClick={() => setActivePanelTab('reflection')}
                      className={`py-3 text-xs font-bold uppercase tracking-wider font-mono cursor-pointer border-b-2 transition-all ${
                        activePanelTab === 'reflection'
                          ? 'border-google-blue text-google-blue'
                          : 'border-transparent text-google-textMuted hover:text-white'
                      }`}
                    >
                      Self-Reflection ({reflectionLogs.length})
                    </button>
                  </div>

                  {activePanelTab === 'deliverables' && (
                    <div className="flex gap-1.5 py-2">
                      <button
                        onClick={() => handleGenerateDeliverable('email')}
                        disabled={generatingType !== null}
                        className="bg-google-blue/10 hover:bg-google-blue/20 text-google-blue font-mono font-bold text-[9px] uppercase px-2 py-1 rounded transition-colors disabled:opacity-50 cursor-pointer"
                      >
                        {generatingType === 'email' ? 'Writing...' : '✉ Email'}
                      </button>
                      <button
                        onClick={() => handleGenerateDeliverable('blog_post')}
                        disabled={generatingType !== null}
                        className="bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 font-mono font-bold text-[9px] uppercase px-2 py-1 rounded transition-colors disabled:opacity-50 cursor-pointer"
                      >
                        {generatingType === 'blog_post' ? 'Writing...' : '📄 Blog Post'}
                      </button>
                      <button
                        onClick={() => handleGenerateDeliverable('ad_copy')}
                        disabled={generatingType !== null}
                        className="bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 font-mono font-bold text-[9px] uppercase px-2 py-1 rounded transition-colors disabled:opacity-50 cursor-pointer"
                      >
                        {generatingType === 'ad_copy' ? 'Writing...' : '📢 Ad Copy'}
                      </button>
                    </div>
                  )}

                  {activePanelTab === 'reflection' && (
                    <div className="flex gap-1.5 py-2">
                      <button
                        onClick={handleTriggerReflection}
                        disabled={reflectionLoading}
                        className="bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 font-mono font-bold text-[9px] uppercase px-2 py-1 rounded transition-colors disabled:opacity-50 cursor-pointer flex items-center gap-1"
                      >
                        <RefreshCw size={10} className={reflectionLoading ? "animate-spin" : ""} />
                        {reflectionLoading ? 'Reflecting...' : '🧠 Run Reflection'}
                      </button>
                    </div>
                  )}
                </div>

                <div className="flex-1 overflow-auto max-h-80">
                  {activePanelTab === 'leads' && (
                    leads.length === 0 ? (
                      <div className="flex flex-col items-center justify-center p-8 text-center h-48 space-y-2">
                        <FolderOpen size={24} className="text-google-textMuted" />
                        <span className="text-xs text-google-textMuted font-mono">No qualified outreach targets gathered yet. Wait for deep_research log step.</span>
                      </div>
                    ) : (
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="border-b dark:border-google-borderDark bg-gray-50/20 dark:bg-google-sidebarDark/10 text-google-textMuted font-mono uppercase text-[10px]">
                            <th className="p-3">Company</th>
                            <th className="p-3">Email Address</th>
                            <th className="p-3 text-center">Score</th>
                            <th className="p-3 text-right">Outreach Status</th>
                            <th className="p-3 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-google-borderDark/10 font-mono">
                          {leads.map((l) => (
                            <tr key={l.id} className="hover:bg-gray-50/20 dark:hover:bg-google-borderDark/10">
                              <td className="p-3 font-semibold">{l.company || 'Unknown Company'}</td>
                              <td className="p-3">{l.email}</td>
                              <td className="p-3 text-center">
                                <span className="bg-google-blue/10 text-google-blue px-1.5 py-0.5 rounded font-bold text-[10px]">
                                  {l.qualification_score.toFixed(0)}%
                                </span>
                              </td>
                              <td className="p-3 text-right">
                                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${l.outreach_status === 'bounced'
                                    ? 'bg-red-500/10 text-red-400'
                                    : l.outreach_status === 'email_sent'
                                      ? 'bg-yellow-500/10 text-yellow-400'
                                      : l.outreach_status === 'replied'
                                        ? 'bg-green-500/10 text-green-400'
                                        : l.outreach_status === 'contract_pending'
                                          ? 'bg-blue-500/10 text-blue-400'
                                          : l.outreach_status === 'closed_won'
                                            ? 'bg-emerald-500/10 text-emerald-400'
                                            : 'bg-gray-500/10 text-gray-400'
                                  }`}>
                                  {l.outreach_status}
                                </span>
                              </td>
                              <td className="p-3 text-right flex justify-end gap-1.5">
                                {(l.outreach_status === 'replied' || l.outreach_status === 'pending' || l.outreach_status === 'email_sent') && (
                                  <button
                                    onClick={() => handleSimulateCloser(l.id)}
                                    disabled={actionLoading === l.id}
                                    className="bg-google-blue hover:bg-google-blueDark text-white px-2 py-0.5 rounded font-semibold text-[10px] cursor-pointer transition-all disabled:opacity-50"
                                  >
                                    {actionLoading === l.id ? 'Calling...' : '📞 Closer'}
                                  </button>
                                )}
                                {l.outreach_status === 'contract_pending' && (
                                  <>
                                    <button
                                      onClick={() => handleViewContract(l.id, l.company || 'Client')}
                                      className="bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 px-2 py-0.5 rounded font-bold text-[10px] cursor-pointer"
                                    >
                                      📄 SLA
                                    </button>
                                    <button
                                      onClick={() => handleMockPayment(l.id)}
                                      className="bg-green-500/10 text-green-400 hover:bg-green-500/20 px-2 py-0.5 rounded font-bold text-[10px] cursor-pointer"
                                    >
                                      💳 Pay
                                    </button>
                                  </>
                                )}
                                {l.outreach_status === 'closed_won' && (
                                  <>
                                    <button
                                      onClick={() => handleViewContract(l.id, l.company || 'Client')}
                                      className="bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 px-2 py-0.5 rounded font-bold text-[10px] cursor-pointer"
                                    >
                                      📄 SLA
                                    </button>
                                    <span className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold text-[10px]">
                                      ✅ Won
                                    </span>
                                  </>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )
                  )}

                  {activePanelTab === 'deliverables' && (
                    deliverablesLoading ? (
                      <div className="text-center py-12 text-xs font-mono text-google-textMuted">Loading deliverables...</div>
                    ) : deliverables.length === 0 ? (
                      <div className="flex flex-col items-center justify-center p-8 text-center h-48 space-y-2">
                        <FolderOpen size={24} className="text-google-textMuted" />
                        <span className="text-xs text-google-textMuted font-mono">No marketing deliverables generated yet. Use buttons above to compile assets.</span>
                      </div>
                    ) : (
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="border-b dark:border-google-borderDark bg-gray-50/20 dark:bg-google-sidebarDark/10 text-google-textMuted font-mono uppercase text-[10px]">
                            <th className="p-3">Deliverable Asset Title</th>
                            <th className="p-3">Format</th>
                            <th className="p-3 text-center">Tries</th>
                            <th className="p-3 text-right">QA Status</th>
                            <th className="p-3 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-google-borderDark/10 font-mono">
                          {deliverables.map((d) => (
                            <tr key={d.id} className="hover:bg-gray-50/20 dark:hover:bg-google-borderDark/10">
                              <td className="p-3 font-semibold truncate max-w-[200px]" title={d.title}>{d.title}</td>
                              <td className="p-3">
                                <span className="bg-gray-500/10 text-gray-400 px-1.5 py-0.5 rounded text-[10px] uppercase font-bold">
                                  {d.content_type}
                                </span>
                              </td>
                              <td className="p-3 text-center">{d.refinement_count}/3</td>
                              <td className="p-3 text-right">
                                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                                  d.status === 'approved'
                                    ? 'bg-emerald-500/10 text-emerald-400'
                                    : d.status === 'manual_review_pending'
                                      ? 'bg-red-500/10 text-red-400'
                                      : 'bg-yellow-500/10 text-yellow-400'
                                }`}>
                                  {d.status}
                                </span>
                              </td>
                              <td className="p-3 text-right">
                                <button
                                  onClick={() => handleOpenDeliverableDetail(d)}
                                  className="bg-google-blue hover:bg-google-blueDark text-white px-2.5 py-0.5 rounded font-semibold text-[10px] cursor-pointer"
                                >
                                  👁 View
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )
                  )}

                  {activePanelTab === 'reflection' && (
                    reflectionLogs.length === 0 ? (
                      <div className="flex flex-col items-center justify-center p-8 text-center h-48 space-y-2">
                        <FolderOpen size={24} className="text-google-textMuted" />
                        <span className="text-xs text-google-textMuted font-mono">No self-reflection cycles executed yet. Click "Run Reflection" to audit logs.</span>
                      </div>
                    ) : (
                      <div className="p-4 space-y-4 font-mono">
                        {reflectionLogs.map((log) => (
                          <div key={log.id} className="border border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/15 p-3 rounded-lg flex flex-col gap-2 text-xs">
                            <div className="flex justify-between items-center text-[10px] text-google-textMuted border-b border-google-borderDark/10 pb-1.5 font-bold uppercase">
                              <span className="text-yellow-400">🧠 Diagnostic Audit Report</span>
                              <span>{new Date(log.created_at).toLocaleString()}</span>
                            </div>
                            <pre className="whitespace-pre-wrap leading-relaxed font-mono text-[11px] text-gray-700 dark:text-gray-300">
                              {log.message}
                            </pre>
                          </div>
                        ))}
                      </div>
                    )
                  )}
                </div>
              </div>

              {/* Local agent logs for this campaign */}
              <div className={`p-4 border rounded-lg shadow-sm flex flex-col max-h-64 overflow-hidden ${isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
                }`}>
                <h3 className="text-xs font-semibold uppercase tracking-wider font-mono text-google-textMuted flex items-center gap-2 mb-3">
                  <Activity size={14} className="text-google-blue" />
                  Local Channel Logs
                </h3>
                <div className="flex-1 overflow-y-auto space-y-2 max-h-48 font-mono text-[11px] leading-relaxed pr-2">
                  {campaignLogs.length === 0 ? (
                    <span className="text-google-textMuted block text-center py-4">No log activities recorded.</span>
                  ) : (
                    campaignLogs.map((log) => (
                      <div key={log.id} className="border-b border-google-borderDark/10 pb-1.5 last:border-b-0">
                        <div className="flex justify-between items-center mb-0.5">
                          <span className={`font-bold uppercase px-1 rounded text-[9px] ${log.agent_name === 'sandbox' ? 'bg-cyan-500/10 text-cyan-400' : 'bg-google-blue/10 text-google-blue'
                            }`}>
                            [{log.agent_name}]
                          </span>
                          <span className={`text-[9px] uppercase font-bold ${log.log_level === 'error' ? 'text-red-400' : log.log_level === 'warning' ? 'text-yellow-400' : 'text-google-textMuted'
                            }`}>
                            {log.log_level}
                          </span>
                        </div>
                        <p className="text-gray-300 whitespace-pre-wrap">{log.message}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className={`flex-1 flex flex-col items-center justify-center p-8 border rounded-lg shadow-sm text-center min-h-[400px] ${isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
              }`}>
              <Megaphone size={48} className="text-google-textMuted mb-4" />
              <h2 className="text-lg font-bold uppercase tracking-wider font-mono">No Active Campaign</h2>
              <p className="text-sm text-google-textMuted mt-1 max-w-sm">Select an existing campaign channel from the sidebar list, or deploy a new campaign brain node.</p>
            </div>
          )}
        </div>
      </div>

      {/* Slide-over Create Campaign Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className={`w-full max-w-lg rounded-xl shadow-2xl overflow-hidden border ${isDark ? 'bg-google-cardDark border-google-borderDark text-gray-100' : 'bg-white border-gray-200 text-gray-800'
            }`}>
            <div className="p-5 border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30">
              <h3 className="text-md font-bold font-sans flex items-center gap-2">
                <Megaphone size={18} className="text-google-blue" />
                Launch Outbound Campaign Node
              </h3>
            </div>

            <form onSubmit={handleCreateCampaign} className="p-5 space-y-4">
              <div className="space-y-1">
                <label className="text-[11px] font-mono uppercase tracking-wider text-google-textMuted">Campaign Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., SaaS Outreach Austin"
                  required
                  className={`w-full px-3 py-2 text-sm rounded border focus:outline-none focus:ring-1 focus:ring-google-blue font-mono ${isDark
                      ? 'bg-google-sidebarDark border-google-borderDark text-gray-100'
                      : 'bg-white border-gray-200 text-gray-800'
                    }`}
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-mono uppercase tracking-wider text-google-textMuted">Strategic Business Objective</label>
                <textarea
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  placeholder="e.g., Sell SEO services to dental clinics in Austin. Minimum qualification score 80."
                  required
                  rows={4}
                  className={`w-full px-3 py-2 text-sm rounded border focus:outline-none focus:ring-1 focus:ring-google-blue font-mono ${isDark
                      ? 'bg-google-sidebarDark border-google-borderDark text-gray-100'
                      : 'bg-white border-gray-200 text-gray-800'
                    }`}
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-mono uppercase tracking-wider text-google-textMuted">Campaign Budget Limit ($)</label>
                <input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(parseFloat(e.target.value))}
                  min={1}
                  required
                  className={`w-full px-3 py-2 text-sm rounded border focus:outline-none focus:ring-1 focus:ring-google-blue font-mono ${isDark
                      ? 'bg-google-sidebarDark border-google-borderDark text-gray-100'
                      : 'bg-white border-gray-200 text-gray-800'
                    }`}
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-google-borderDark/20">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className={`px-4 py-2 rounded text-sm font-semibold transition-colors cursor-pointer ${isDark
                      ? 'hover:bg-google-borderDark text-gray-300'
                      : 'hover:bg-gray-100 text-gray-600'
                    }`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-google-blue hover:bg-google-blueDark cursor-pointer text-white px-4 py-2 rounded text-sm font-semibold transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Launching...' : 'Launch Pipeline'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Closer Call Transcript Modal */}
      {showCloserModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className={`w-full max-w-4xl h-[80vh] rounded-xl shadow-2xl overflow-hidden border flex flex-col ${isDark ? 'bg-google-cardDark border-google-borderDark text-gray-100' : 'bg-white border-gray-200 text-gray-800'
            }`}>
            <div className="p-5 border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30 flex justify-between items-center">
              <h3 className="text-md font-bold font-sans flex items-center gap-2">
                <Megaphone size={18} className="text-google-blue" />
                Closer Agent Call Logs
              </h3>
              <button
                onClick={() => setShowCloserModal(false)}
                className="text-google-textMuted hover:text-white font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 grid grid-cols-1 md:grid-cols-12 overflow-hidden">
              {/* Left Column: Call Transcript (col-span-8) */}
              <div className="md:col-span-8 flex flex-col p-5 border-r border-google-borderDark/20 overflow-hidden bg-google-sidebarDark/20">
                <h4 className="text-xs font-mono uppercase tracking-wider text-google-textMuted mb-3">Live Call Audio Transcript</h4>
                <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs pr-2 leading-relaxed">
                  {closerTranscript.split('\n').filter(l => l.trim()).map((line, idx) => {
                    const isCloser = line.startsWith('Closer Agent:');
                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg max-w-[85%] ${isCloser
                            ? 'bg-google-blue/10 border border-google-blue/20 text-blue-200 mr-auto'
                            : 'bg-google-borderDark/30 border border-google-borderDark/50 text-gray-200 ml-auto text-right'
                          }`}
                      >
                        <p className="font-bold text-[10px] uppercase opacity-75 mb-0.5">
                          {isCloser ? 'Deal Closer Bot' : 'Prospect (Miami Lead)'}
                        </p>
                        <p className="whitespace-pre-wrap">{line.replace(/^(Closer Agent:|Prospect \([^)]+\):|Prospect:)/, '').trim()}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Agreement details (col-span-4) */}
              <div className="md:col-span-4 flex flex-col p-5 space-y-5 justify-between bg-google-sidebarDark/10">
                <div className="space-y-4">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted">Negotiation Outcome</span>
                    <div className="flex items-center gap-2 mt-1">
                      {closerAgreed ? (
                        <span className="bg-emerald-500/10 text-emerald-400 text-xs px-2.5 py-0.5 rounded font-mono uppercase tracking-wider font-bold">
                          AGREEMENT SIGNED
                        </span>
                      ) : (
                        <span className="bg-red-500/10 text-red-400 text-xs px-2.5 py-0.5 rounded font-mono uppercase tracking-wider font-bold">
                          PROSPECT DECLINED
                        </span>
                      )}
                    </div>
                  </div>

                  {closerAgreed && (
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted">Monthly Negotiated Rate</span>
                      <p className="text-xl font-bold text-emerald-400 mt-0.5 font-mono">${closerPrice.toFixed(2)}/mo</p>
                    </div>
                  )}

                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted">Executive Summary</span>
                    <p className="text-xs text-gray-300 font-mono leading-relaxed mt-1">{closerSummary}</p>
                  </div>
                </div>

                <div className="space-y-2.5 pt-4 border-t border-google-borderDark/20">
                  {closerAgreed && closerCheckout && (
                    <a
                      href={closerCheckout}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-center bg-green-500 hover:bg-green-600 text-white py-2 rounded text-xs font-semibold font-mono tracking-wider transition-colors shadow-sm cursor-pointer"
                    >
                      💳 Complete Stripe Checkout
                    </a>
                  )}
                  <button
                    onClick={() => setShowCloserModal(false)}
                    className="w-full bg-google-borderDark hover:bg-google-borderDark/80 text-gray-300 py-2 rounded text-xs font-semibold font-mono transition-colors cursor-pointer"
                  >
                    Close Log View
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dynamic Deliverable Preview & QA Refinement Modal */}
      {showDeliverableModal && selectedDeliverable && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className={`w-full max-w-5xl h-[85vh] rounded-xl shadow-2xl overflow-hidden border flex flex-col ${isDark ? 'bg-google-cardDark border-google-borderDark text-gray-100' : 'bg-white border-gray-200 text-gray-800'
            }`}>
            <div className="p-5 border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30 flex justify-between items-center">
              <h3 className="text-md font-bold font-sans flex items-center gap-2">
                <FolderOpen size={18} className="text-google-blue" />
                Deliverable Asset Viewer & Editor
              </h3>
              <button
                onClick={() => setShowDeliverableModal(false)}
                className="text-google-textMuted hover:text-white font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 grid grid-cols-1 md:grid-cols-12 overflow-hidden">
              {/* Left Column: Title, Content, Image */}
              <div className="md:col-span-8 flex flex-col p-5 border-r border-google-borderDark/20 overflow-y-auto space-y-4">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted">Deliverable Title</span>
                  <h4 className="text-md font-bold font-sans mt-0.5">{selectedDeliverable.title}</h4>
                </div>

                <div className="flex-1 flex flex-col bg-google-sidebarDark/10 p-4 border border-google-borderDark/20 rounded-lg overflow-y-auto">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted mb-2 block">Content Copy</span>
                  <pre className="text-xs font-mono whitespace-pre-wrap leading-relaxed flex-1 overflow-auto">{selectedDeliverable.content_body}</pre>
                </div>

                {selectedDeliverable.image_url && (
                  <div className="border border-google-borderDark/20 rounded-lg overflow-hidden bg-google-sidebarDark/10 p-3">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted mb-2 block">Generated Marketing Graphic Asset</span>
                    <div className="max-w-md mx-auto aspect-video rounded overflow-hidden bg-black/35 relative flex items-center justify-center border border-google-borderDark/10">
                      <img
                        src={selectedDeliverable.image_url}
                        alt="Generated Campaign Graphic"
                        className="object-cover w-full h-full"
                        onError={(e) => {
                          // Display placeholder graphic if mock image fails to load
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                      <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center bg-google-blue/10">
                        <FolderOpen className="text-google-blue mb-1" size={24} />
                        <span className="text-[10px] font-mono uppercase tracking-wider text-google-blue font-bold">UABE Automated Graphic Asset</span>
                        <span className="text-[9px] text-google-textMuted font-mono mt-0.5">{selectedDeliverable.image_url}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column: QA Reports & Manual Refinement */}
              <div className="md:col-span-4 flex flex-col p-5 space-y-5 justify-between bg-google-sidebarDark/10">
                <div className="space-y-4 overflow-y-auto">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted">QA Approval Status</span>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
                        selectedDeliverable.status === 'approved'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : selectedDeliverable.status === 'manual_review_pending'
                            ? 'bg-red-500/10 text-red-400'
                            : 'bg-yellow-500/10 text-yellow-400'
                      }`}>
                        {selectedDeliverable.status}
                      </span>
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted font-bold block">Refinement Loops Limit</span>
                    <span className="text-xs font-mono text-gray-300 mt-1 block">{selectedDeliverable.refinement_count} / 3 Attempts Used</span>
                  </div>

                  {selectedDeliverable.qa_feedback && (
                    <div className="p-3 bg-yellow-500/5 border border-yellow-500/10 rounded-lg">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-yellow-500 font-bold block mb-1">Editor Rejection Feedback</span>
                      <p className="text-[11px] font-mono text-yellow-400 leading-relaxed whitespace-pre-wrap">{selectedDeliverable.qa_feedback}</p>
                    </div>
                  )}

                  <div className="pt-2">
                    <label className="text-[10px] font-mono uppercase tracking-wider text-google-textMuted font-bold block mb-1">Request Copy Refinement</label>
                    <textarea
                      value={rebuildFeedback}
                      onChange={(e) => setRebuildFeedback(e.target.value)}
                      placeholder="Add specific details or styling changes requested (e.g. 'Add call to action at the end', 'Make the tone more aggressive')."
                      rows={4}
                      className={`w-full p-2.5 text-xs rounded border focus:outline-none focus:ring-1 focus:ring-google-blue font-mono ${
                        isDark ? 'bg-google-sidebarDark border-google-borderDark text-gray-100' : 'bg-white border-gray-200 text-gray-800'
                      }`}
                    />
                  </div>
                </div>

                <div className="space-y-2 pt-4 border-t border-google-borderDark/20">
                  <button
                    onClick={() => handleRebuildDeliverable(selectedDeliverable.id)}
                    disabled={rebuildingId !== null || selectedDeliverable.refinement_count >= 3}
                    className="w-full bg-google-blue hover:bg-google-blueDark disabled:bg-gray-700 text-white py-2 rounded text-xs font-semibold font-mono tracking-wider transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                  >
                    {rebuildingId ? 'Refining Copy...' : selectedDeliverable.refinement_count >= 3 ? 'Refinement Limit Reached' : '🔄 Refine Copy Asset'}
                  </button>
                  <button
                    onClick={() => setShowDeliverableModal(false)}
                    className="w-full bg-google-borderDark hover:bg-google-borderDark/80 text-gray-300 py-2 rounded text-xs font-semibold font-mono transition-colors cursor-pointer"
                  >
                    Close Viewer
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

