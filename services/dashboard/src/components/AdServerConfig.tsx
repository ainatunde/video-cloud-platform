import React, { useState } from 'react';
import { Server, CheckCircle, XCircle, Play, AlertTriangle } from 'lucide-react';
import axios from 'axios';

interface AdServer {
  id: string;
  name: string;
  type: 'GAM' | 'SpotX' | 'FreeWheel' | 'Local';
  enabled: boolean;
  vastUrl: string;
  defaultDuration: number;
  priority: number;
}

const DEFAULT_SERVERS: AdServer[] = [
  {
    id: 'gam',
    name: 'Google Ad Manager',
    type: 'GAM',
    enabled: true,
    vastUrl: 'https://pubads.g.doubleclick.net/gampad/ads?sz=640x480&iu=/124319096/external/single_ad_samples&ciu_szs=300x250&impl=s&gdfp_req=1&env=vp&output=vast&unviewed_position_start=1',
    defaultDuration: 30,
    priority: 1,
  },
  {
    id: 'spotx',
    name: 'SpotX',
    type: 'SpotX',
    enabled: false,
    vastUrl: 'https://search.spotxchange.com/vast/2.00/85394?content_page_url=',
    defaultDuration: 30,
    priority: 2,
  },
  {
    id: 'local',
    name: 'Local Ad Server',
    type: 'Local',
    enabled: true,
    vastUrl: 'http://ad-server:3000/ads/vast',
    defaultDuration: 15,
    priority: 3,
  },
];

type TestResult = { server: string; status: 'success' | 'error' | 'testing'; message: string };

export default function AdServerConfig() {
  const [servers, setServers] = useState<AdServer[]>(DEFAULT_SERVERS);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [saved, setSaved] = useState(false);

  const toggleServer = (id: string) => {
    setServers(prev => prev.map(s => s.id === id ? { ...s, enabled: !s.enabled } : s));
    setSaved(false);
  };

  const updateServer = (id: string, field: keyof AdServer, value: string | number | boolean) => {
    setServers(prev => prev.map(s => s.id === id ? { ...s, [field]: value } : s));
    setSaved(false);
  };

  const testAdRequest = async (server: AdServer) => {
    setTestResults(prev => ({
      ...prev,
      [server.id]: { server: server.name, status: 'testing', message: 'Sending test request…' },
    }));
    try {
      const res = await axios.get('/api/ads/test', {
        params: { url: server.vastUrl },
        timeout: 10000,
      });
      setTestResults(prev => ({
        ...prev,
        [server.id]: { server: server.name, status: 'success', message: `Response: ${res.status} — VAST received` },
      }));
    } catch {
      setTestResults(prev => ({
        ...prev,
        [server.id]: { server: server.name, status: 'error', message: 'Request failed — check VAST URL' },
      }));
    }
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Ad Server Configuration</h2>
        <button
          onClick={handleSave}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${saved ? 'bg-green-600 text-white' : 'bg-blue-600 hover:bg-blue-500 text-white'}`}
        >
          {saved ? '✓ Saved' : 'Save Configuration'}
        </button>
      </div>

      <div className="space-y-4">
        {servers.map(server => (
          <div key={server.id} className="bg-gray-900 rounded-lg border border-gray-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Server size={16} className="text-gray-400" />
                <span className="font-semibold text-white">{server.name}</span>
                <span className="text-xs px-2 py-0.5 bg-gray-800 text-gray-400 rounded">{server.type}</span>
                <span className="text-xs text-gray-500">Priority: {server.priority}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-400">{server.enabled ? 'Enabled' : 'Disabled'}</span>
                <button
                  onClick={() => toggleServer(server.id)}
                  className={`w-10 h-6 rounded-full transition-colors ${server.enabled ? 'bg-blue-600' : 'bg-gray-600'}`}
                >
                  <span className={`block w-4 h-4 bg-white rounded-full mx-1 transition-transform ${server.enabled ? 'translate-x-4' : 'translate-x-0'}`} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <label className="block text-xs text-gray-400 mb-1">VAST URL</label>
                <input
                  type="text"
                  value={server.vastUrl}
                  onChange={e => updateServer(server.id, 'vastUrl', e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-xs text-white font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Default Duration (s)</label>
                <input
                  type="number"
                  value={server.defaultDuration}
                  onChange={e => updateServer(server.id, 'defaultDuration', parseInt(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
                />
              </div>
            </div>

            <div className="mt-3 flex items-center gap-3">
              <button
                onClick={() => testAdRequest(server)}
                disabled={testResults[server.id]?.status === 'testing'}
                className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 rounded text-sm transition-colors"
              >
                <Play size={12} /> Test Ad Request
              </button>
              {testResults[server.id] && (
                <div className={`flex items-center gap-2 text-xs ${
                  testResults[server.id].status === 'success' ? 'text-green-400' :
                  testResults[server.id].status === 'error' ? 'text-red-400' : 'text-yellow-400'
                }`}>
                  {testResults[server.id].status === 'success' && <CheckCircle size={12} />}
                  {testResults[server.id].status === 'error' && <XCircle size={12} />}
                  {testResults[server.id].status === 'testing' && <AlertTriangle size={12} />}
                  {testResults[server.id].message}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
