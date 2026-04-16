import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Lightbulb,
  BarChart2,
  Users,
  Sparkles,
  Settings,
  Cloud,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/advisor', icon: Lightbulb, label: 'Azure Advisor' },
  { to: '/costs', icon: BarChart2, label: 'Cost Analysis' },
  { to: '/m365', icon: Users, label: 'M365 Licensing' },
  { to: '/analysis', icon: Sparkles, label: 'AI Analysis' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col flex-shrink-0">
      {/* Logo Area */}
      <div className="h-16 flex items-center gap-3 px-4 border-b border-gray-700">
        <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <Cloud className="w-5 h-5 text-white" />
        </div>
        <div>
          <span className="text-white font-semibold text-sm leading-tight block">
            Cost Optimizer
          </span>
          <span className="text-blue-400 text-xs">Azure + M365</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/30'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`
            }
          >
            <Icon className="w-5 h-5 flex-shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom Section */}
      <div className="p-4 border-t border-gray-700">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
          <span className="text-gray-500 text-xs">v1.0.0</span>
        </div>
        <p className="text-gray-600 text-xs mt-1">Azure Cost Optimizer</p>
      </div>
    </aside>
  );
}

export default Sidebar;
