import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import type { WalletState, LeadState } from './components/Dashboard';
import type { LogEntry } from './components/LogStreamer';
import { api } from './services/api';
import { telemetryWS } from './services/websocket';
import { KeyRound, ShieldAlert, LogIn } from 'lucide-react';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [loginError, setLoginError] = useState<string>('');
  
  // Dashboard & Navigation States
  const [currentView, setCurrentView] = useState<string>('dashboard');
  const [isDark, setIsDark] = useState<boolean>(true);
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [activeKeyIdx, setActiveKeyIdx] = useState<number>(0);
  
  // Telemetry Data States
  const [wallet, setWallet] = useState<WalletState | null>(null);
  const [leads, setLeads] = useState<LeadState[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);

  // Check auth session on startup
  useEffect(() => {
    const token = localStorage.getItem('uabe_access_token');
    if (token) {
      setIsAuthenticated(true);
      telemetryWS.connect();
    }

    // Toggle body dark class
    if (isDark) {
      document.body.classList.add('dark');
    } else {
      document.body.classList.remove('dark');
    }

    // Bind logout dispatch listener
    const handleLogoutEvent = () => {
      setIsAuthenticated(false);
      telemetryWS.disconnect();
    };
    window.addEventListener('auth_logout', handleLogoutEvent);

    return () => {
      window.removeEventListener('auth_logout', handleLogoutEvent);
    };
  }, [isDark]);

  // Bind WebSocket state listeners
  useEffect(() => {
    if (!isAuthenticated) return;

    // Listen for WebSocket status shifts
    const unsubscribeStatus = telemetryWS.onStatusChange((status) => {
      setWsStatus(status);
    });

    // Listen for real-time telemetry frame events
    const unsubscribeMessage = telemetryWS.onMessage((data) => {
      if (data.event === 'telemetry_update') {
        if (data.wallet) setWallet(data.wallet);
        if (data.leads) setLeads(data.leads);
        if (data.active_key_index !== undefined) {
          setActiveKeyIdx(data.active_key_index);
        }
      } else if (data.event === 'agent_log') {
        const newLog: LogEntry = {
          id: data.log_id || Math.random().toString(),
          timestamp: new Date().toLocaleTimeString(),
          level: data.level || 'info',
          agent: data.agent || 'executive',
          message: data.message || ''
        };
        // Slice logs array to keep last 1000 items (virtual memory scroll protection)
        setLogs((prevLogs) => [...prevLogs, newLog].slice(-1000));
      }
    });

    return () => {
      unsubscribeStatus();
      unsubscribeMessage();
    };
  }, [isAuthenticated]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    try {
      const res = await api.post('/auth/login', { email, password });
      localStorage.setItem('uabe_access_token', res.data.access_token);
      localStorage.setItem('uabe_refresh_token', res.data.refresh_token);
      setIsAuthenticated(true);
      telemetryWS.connect();
    } catch (err: any) {
      setLoginError(err.response?.data?.detail || 'Authentication failed. Please verify credentials.');
    }
  };

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (e) {
      // ignore logout rest errors, clear session anyway
    }
    localStorage.removeItem('uabe_access_token');
    localStorage.removeItem('uabe_refresh_token');
    setIsAuthenticated(false);
    telemetryWS.disconnect();
    // Reset local data
    setWallet(null);
    setLeads([]);
    setLogs([]);
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  // 1. Render login screen if unauthenticated
  if (!isAuthenticated) {
    return (
      <div className={`flex items-center justify-center min-h-screen ${
        isDark ? 'bg-google-darkBg text-gray-100' : 'bg-gray-50 text-gray-900'
      }`}>
        <div className={`w-full max-w-md p-8 border rounded-lg shadow-lg ${
          isDark ? 'bg-google-cardDark border-google-borderDark' : 'bg-white border-gray-200'
        }`}>
          <div className="text-center space-y-2 mb-6">
            <div className="w-12 h-12 bg-google-blue/10 rounded-full flex items-center justify-center mx-auto text-google-blue">
              <ShieldAlert size={28} />
            </div>
            <h1 className="text-2xl font-bold font-sans">UABE System Sign-In</h1>
            <p className="text-xs text-google-textMuted uppercase tracking-wider font-mono">Core Gateway Authentication</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-google-textMuted uppercase">Email Address</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@uabe.com"
                className={`w-full p-2.5 rounded border text-sm focus:outline-none focus:ring-1 focus:ring-google-blue ${
                  isDark 
                    ? 'bg-google-darkBg border-google-borderDark text-gray-100' 
                    : 'bg-white border-gray-300 text-gray-900'
                }`}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-google-textMuted uppercase">Secret Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={`w-full p-2.5 rounded border text-sm focus:outline-none focus:ring-1 focus:ring-google-blue ${
                  isDark 
                    ? 'bg-google-darkBg border-google-borderDark text-gray-100' 
                    : 'bg-white border-gray-300 text-gray-900'
                }`}
              />
            </div>

            {loginError && (
              <div className="bg-red-500/10 border border-red-500/30 p-2.5 rounded text-xs text-red-500 font-mono">
                {loginError}
              </div>
            )}

            <button
              type="submit"
              className="w-full bg-google-blue hover:bg-google-blueHover text-white py-2.5 rounded text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <LogIn size={18} />
              <span>Authenticate Session</span>
            </button>
          </form>
        </div>
      </div>
    );
  }

  // 2. Render core dashboard layout upon successful authentication
  return (
    <div className={`flex min-h-screen ${isDark ? 'bg-google-darkBg text-gray-100' : 'bg-gray-50 text-gray-900'}`}>
      <Sidebar
        currentView={currentView}
        onViewChange={setCurrentView}
        isDark={isDark}
        onToggleTheme={() => setIsDark(!isDark)}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
      />
      
      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-screen overflow-y-auto">
        {/* Top Header Bar */}
        <header className={`flex justify-end items-center px-6 h-16 border-b ${
          isDark ? 'bg-google-sidebarDark border-google-borderDark' : 'bg-white border-gray-200'
        }`}>
          <button 
            onClick={handleLogout}
            className="flex items-center gap-2 text-xs font-semibold text-red-500 hover:bg-red-500/10 px-3 py-1.5 rounded transition-colors font-mono uppercase"
          >
            <KeyRound size={14} />
            <span>Revoke Token</span>
          </button>
        </header>

        {/* View Router */}
        <div className="flex-1 p-6">
          {currentView === 'dashboard' && (
            <Dashboard
              wallet={wallet}
              leads={leads}
              logs={logs}
              onClearLogs={handleClearLogs}
              isDark={isDark}
              wsStatus={wsStatus}
              activeKeyIdx={activeKeyIdx}
            />
          )}

          {currentView !== 'dashboard' && (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
              <ShieldAlert size={48} className="text-google-blue" />
              <div>
                <h2 className="text-xl font-bold uppercase tracking-wider font-mono">{currentView} console</h2>
                <p className="text-sm text-google-textMuted mt-1">This console segment is sandboxed under active development.</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
