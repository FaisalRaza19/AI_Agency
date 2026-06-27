import React, { useEffect, useRef, useState } from 'react';
import { Trash2, Copy, ArrowDown, ShieldAlert } from 'lucide-react';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  agent: string;
  message: string;
}

interface LogStreamerProps {
  logs: LogEntry[];
  onClearLogs: () => void;
  isDark: boolean;
}

export const LogStreamer: React.FC<LogStreamerProps> = ({ logs, onClearLogs, isDark }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  // Auto scroll logic when logs arrive
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const copyToClipboard = () => {
    const text = logs.map(l => `[${l.timestamp}] [${l.level.toUpperCase()}] [${l.agent.toUpperCase()}]: ${l.message}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLogLevelClass = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
      case 'critical':
        return 'text-red-500 font-bold';
      case 'warning':
        return 'text-yellow-500 font-semibold';
      case 'info':
      default:
        return 'text-green-400';
    }
  };

  return (
    <div className={`flex flex-col rounded border h-[450px] shadow ${
      isDark 
        ? 'bg-[#1e1e1e] border-google-borderDark text-gray-200' 
        : 'bg-gray-900 border-gray-800 text-gray-100'
    }`}>
      {/* Console Header */}
      <div className="flex justify-between items-center bg-gray-850 px-4 py-2 border-b border-gray-800 text-xs">
        <div className="flex items-center gap-2">
          <ShieldAlert size={14} className="text-google-blue" />
          <span className="font-mono font-semibold tracking-wider">CLOUD LOGGING CONSOLE</span>
          <span className="bg-gray-800 px-1.5 py-0.5 rounded text-gray-400 font-semibold">
            {logs.length} entries
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`p-1.5 rounded hover:bg-gray-800 transition-colors flex items-center gap-1 ${
              autoScroll ? 'text-google-blue font-semibold' : 'text-gray-400'
            }`}
            title="Toggle Auto Scroll"
          >
            <ArrowDown size={14} className={autoScroll ? 'animate-bounce' : ''} />
            <span>Auto Scroll</span>
          </button>
          
          <button
            onClick={copyToClipboard}
            className="p-1.5 rounded hover:bg-gray-800 text-gray-450 transition-colors flex items-center gap-1"
            title="Copy Logs"
          >
            <Copy size={14} />
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>
          
          <button
            onClick={onClearLogs}
            className="p-1.5 rounded hover:bg-red-900/40 text-red-400 transition-colors flex items-center gap-1"
            title="Clear Logs"
          >
            <Trash2 size={14} />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Terminal logs list */}
      <div 
        ref={containerRef}
        className="flex-1 p-4 overflow-y-auto font-mono text-[13px] leading-relaxed select-text bg-black/90 scroll-smooth"
      >
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-google-textMuted select-none">
            &gt; Waiting for UABE logs stream connection...
          </div>
        ) : (
          logs.map((log) => {
            const isSandbox = log.agent.toLowerCase() === 'sandbox';
            return (
              <div 
                key={log.id} 
                className={`hover:bg-gray-800/40 py-0.5 border-b border-gray-900/10 transition-colors ${
                  isSandbox ? 'bg-cyan-950/20 border-cyan-900/30' : ''
                }`}
              >
                <span className="text-gray-500 mr-2">[{log.timestamp}]</span>
                <span className={`mr-2 ${getLogLevelClass(log.level)}`}>
                  [{log.level.toUpperCase()}]
                </span>
                <span className={`font-semibold mr-2 ${isSandbox ? 'text-cyan-400' : 'text-google-blue'}`}>
                  [{log.agent.toUpperCase()}]
                </span>
                <span className={`break-words ${isSandbox ? 'text-cyan-100' : 'text-gray-300'}`}>
                  {log.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
