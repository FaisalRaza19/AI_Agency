import React, { useState, useEffect } from 'react';
import { 
  RefreshCw, 
  ArrowUpRight, 
  FileCode,
  Gauge
} from 'lucide-react';
import { api } from '../services/api';

interface StagedPrompt {
  id: number;
  prompt_key: string;
  prompt_text: string;
  version: number;
  status: string;
  benchmark_score: number | null;
}

interface RavaTelemetryProps {
  isDark: boolean;
}

export const RavaTelemetry: React.FC<RavaTelemetryProps> = ({ isDark }) => {
  const [prompts, setPrompts] = useState<StagedPrompt[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [_, setError] = useState<string>('');

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/settings/prompts');
      setPrompts(res.data);
    } catch (err: any) {
      setError('Failed to retrieve staged prompts registry.');
    } finally {
      setLoading(false);
    }
  };

  const handlePromote = async (promptId: number) => {
    setActionLoading(promptId);
    try {
      await api.post('/settings/promote-prompt', { prompt_id: promptId });
      alert('Prompt version successfully promoted to active pinned status!');
      await fetchPrompts();
    } catch (err) {
      alert('Failed to promote prompt version.');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* View Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold font-sans">Live RAVA Telemetry</h1>
          <p className="text-xs text-google-textMuted mt-1">Staging registry for active prompts, execution reflection loops, and LLM benchmark scores.</p>
        </div>
        <button 
          onClick={fetchPrompts} 
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
        
        {/* Left Column: Prompts List (col-span-7) */}
        <div className={`lg:col-span-7 border rounded-lg overflow-hidden flex flex-col shadow-sm ${
          isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
        }`}>
          <div className="p-4 border-b border-google-borderDark/20 bg-gray-50/50 dark:bg-google-sidebarDark/30">
            <h2 className="text-xs font-semibold uppercase tracking-wider font-mono text-google-textMuted">Staged Prompt Versions</h2>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-google-borderDark/10 max-h-[500px]">
            {prompts.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center h-48 space-y-2">
                <FileCode size={28} className="text-google-textMuted" />
                <span className="text-xs text-google-textMuted font-mono">No prompts registered in staging database.</span>
              </div>
            ) : (
              prompts.map((p) => (
                <div key={p.id} className="p-4 space-y-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-bold text-sm text-google-blue font-mono">{p.prompt_key}</h3>
                      <p className="text-[11px] text-google-textMuted font-mono mt-0.5">Version {p.version} | ID: #{p.id}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {p.status === 'pinned' ? (
                        <span className="bg-emerald-500/10 text-emerald-400 text-[10px] px-2 py-0.5 rounded font-mono uppercase tracking-wider font-bold">
                          PINNED
                        </span>
                      ) : (
                        <span className="bg-gray-500/10 text-gray-400 text-[10px] px-2 py-0.5 rounded font-mono uppercase tracking-wider">
                          STAGED
                        </span>
                      )}
                      
                      {p.status !== 'pinned' && (
                        <button
                          onClick={() => handlePromote(p.id)}
                          disabled={actionLoading === p.id}
                          className="flex items-center gap-1 bg-google-blue/10 hover:bg-google-blue/20 text-google-blue text-[10px] font-bold uppercase font-mono px-2 py-1 rounded transition-colors cursor-pointer"
                        >
                          <ArrowUpRight size={10} />
                          <span>{actionLoading === p.id ? 'Promoting...' : 'Promote'}</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="p-3 bg-gray-50/50 dark:bg-google-sidebarDark/30 rounded border dark:border-google-borderDark/10 text-xs font-mono whitespace-pre-wrap max-h-36 overflow-y-auto">
                    {p.prompt_text}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Prompt Benchmarks (col-span-5) */}
        <div className="lg:col-span-5 flex flex-col space-y-6">
          <div className={`p-5 border rounded-lg shadow-sm ${
            isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
          }`}>
            <h3 className="text-xs font-semibold uppercase tracking-wider font-mono text-google-textMuted flex items-center gap-2 mb-4">
              <Gauge size={16} className="text-google-blue" />
              Evaluation Benchmark Metrics
            </h3>

            <div className="space-y-4">
              {prompts.map((p) => {
                const score = p.benchmark_score || 0;
                return (
                  <div key={p.id} className="space-y-1 font-mono text-xs">
                    <div className="flex justify-between text-google-textMuted">
                      <span className="font-semibold text-gray-300 line-clamp-1">{p.prompt_key} (v{p.version})</span>
                      <span className="font-bold text-google-blue">{score.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-google-borderDark h-2 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all ${
                          score >= 90 ? 'bg-emerald-500' : score >= 75 ? 'bg-google-blue' : 'bg-yellow-500'
                        }`}
                        style={{ width: `${score}%` }}
                      />
                    </div>
                  </div>
                );
              })}
              {prompts.length === 0 && (
                <span className="text-xs text-google-textMuted font-mono">No benchmarks populated.</span>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
