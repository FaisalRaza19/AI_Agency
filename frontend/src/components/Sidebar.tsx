import React from 'react';
import { 
  LayoutDashboard, 
  Megaphone, 
  Volume2, 
  Wallet, 
  Settings, 
  Menu, 
  ChevronLeft, 
  ChevronRight,
  Sun,
  Moon
} from 'lucide-react';

interface SidebarProps {
  currentView: string;
  onViewChange: (view: string) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onViewChange,
  isDark,
  onToggleTheme,
  isCollapsed,
  onToggleCollapse
}) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'campaigns', label: 'Campaigns Console', icon: Megaphone },
    { id: 'rava', label: 'Live RAVA Telemetry', icon: Volume2 },
    { id: 'wallet', label: 'Wallet & Guardrails', icon: Wallet },
    { id: 'settings', label: 'Master Settings', icon: Settings },
  ];

  return (
    <aside 
      className={`flex flex-col border-r h-screen transition-all duration-300 ${
        isCollapsed ? 'w-16' : 'w-64'
      } ${
        isDark 
          ? 'bg-google-sidebarDark border-google-borderDark text-gray-100' 
          : 'bg-white border-gray-200 text-gray-800'
      }`}
    >
      {/* Sidebar Header */}
      <div className="flex justify-between items-center border-b p-4 h-16">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <span className="font-bold text-google-blue text-lg tracking-wider">UABE</span>
            <span className="bg-google-blue/10 px-2 py-0.5 rounded text-google-blue text-xs font-semibold">CORE</span>
          </div>
        )}
        <button 
          onClick={onToggleCollapse}
          className={`p-1 rounded hover:bg-gray-100 dark:hover:bg-google-borderDark transition-colors ${isCollapsed ? 'mx-auto' : ''}`}
          aria-label="Toggle Sidebar"
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 space-y-1 p-2 mt-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              className={`flex items-center gap-3 w-full p-2.5 rounded text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-google-blue text-white'
                  : 'hover:bg-gray-100 dark:hover:bg-google-borderDark'
              } ${isCollapsed ? 'justify-center' : ''}`}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon size={20} className={isActive ? 'text-white' : 'text-google-blue'} />
              {!isCollapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Sidebar Footer (Theme Toggle + Profile Status) */}
      <div className="border-t p-2 space-y-2">
        <button
          onClick={onToggleTheme}
          className={`flex items-center gap-3 w-full p-2.5 rounded text-sm hover:bg-gray-100 dark:hover:bg-google-borderDark transition-colors ${
            isCollapsed ? 'justify-center' : ''
          }`}
          title="Toggle Color Theme"
        >
          {isDark ? <Sun size={20} className="text-yellow-400" /> : <Moon size={20} className="text-gray-500" />}
          {!isCollapsed && <span>{isDark ? 'Light Mode' : 'Dark Mode'}</span>}
        </button>
        
        {!isCollapsed && (
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="relative">
              <div className="w-8 h-8 rounded-full bg-google-blue flex items-center justify-center text-white text-sm font-semibold shadow-inner">
                M
              </div>
              <div className="bottom-0 right-0 absolute w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-white dark:border-google-sidebarDark status-indicator"></div>
            </div>
            <div className="text-left leading-tight truncate">
              <p className="font-semibold text-sm truncate">Master Owner</p>
              <p className="text-google-textMuted text-xs truncate">admin@uabe.com</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
