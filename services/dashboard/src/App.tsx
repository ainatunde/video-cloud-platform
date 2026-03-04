import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import StreamManager from './components/StreamManager';
import SCTE35Config from './components/SCTE35Config';
import ABRConfig from './components/ABRConfig';
import AdServerConfig from './components/AdServerConfig';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import AppBuilder from './components/AppBuilder';

const navItems = [
  { path: '/', label: 'Streams' },
  { path: '/scte35', label: 'SCTE-35' },
  { path: '/abr', label: 'ABR Config' },
  { path: '/ads', label: 'Ad Servers' },
  { path: '/analytics', label: 'Analytics' },
  { path: '/app-builder', label: 'App Builder' },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <h1 className="text-xl font-bold text-blue-400">Video Cloud Platform</h1>
            <nav className="flex gap-4">
              {navItems.map(item => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) =>
                    `px-3 py-1 rounded text-sm ${isActive ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<StreamManager />} />
            <Route path="/scte35" element={<SCTE35Config />} />
            <Route path="/abr" element={<ABRConfig />} />
            <Route path="/ads" element={<AdServerConfig />} />
            <Route path="/analytics" element={<AnalyticsDashboard />} />
            <Route path="/app-builder" element={<AppBuilder />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
