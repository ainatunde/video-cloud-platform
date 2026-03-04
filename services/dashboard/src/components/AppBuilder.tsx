import React, { useState } from 'react';
import { Download, Eye, Code2 } from 'lucide-react';

type Template = 'web-player' | 'react-native' | 'electron';
type Protocol = 'hls' | 'dash' | 'both';

interface AppConfig {
  template: Template;
  protocol: Protocol;
  adsEnabled: boolean;
  analyticsEnabled: boolean;
  streamUrl: string;
  adServerUrl: string;
}

const TEMPLATES: { id: Template; label: string; description: string }[] = [
  { id: 'web-player', label: 'Web Player', description: 'HTML5 player with HLS.js + IMA SDK. Zero dependencies, CDN-ready.' },
  { id: 'react-native', label: 'React Native App', description: 'Cross-platform iOS/Android app with react-native-video and offline caching.' },
  { id: 'electron', label: 'Electron Desktop', description: 'Desktop player for Windows/macOS/Linux with hardware-accelerated rendering.' },
];

const generateWebPlayerConfig = (cfg: AppConfig): string => `
<!-- Video Cloud Platform - Web Player -->
<!-- Stream URL: ${cfg.streamUrl || 'http://your-host:8080/live/stream.m3u8'} -->
<!-- Ads: ${cfg.adsEnabled ? 'enabled' : 'disabled'} -->
<!-- Analytics: ${cfg.analyticsEnabled ? 'enabled' : 'disabled'} -->

const PLAYER_CONFIG = {
  streamUrl: '${cfg.streamUrl || 'http://your-host:8080/live/stream.m3u8'}',
  protocol: '${cfg.protocol}',
  ads: { enabled: ${cfg.adsEnabled}, vastUrl: '${cfg.adServerUrl || 'http://ad-server:3000/ads/vast'}' },
  analytics: { enabled: ${cfg.analyticsEnabled}, endpoint: '/api/metrics' }
};
`.trim();

const generateRNConfig = (cfg: AppConfig): string => `
// React Native App Configuration
export const APP_CONFIG = {
  streamUrl: '${cfg.streamUrl || 'http://your-host:8080/live/stream.m3u8'}',
  protocol: '${cfg.protocol}' as const,
  ads: {
    enabled: ${cfg.adsEnabled},
    vastUrl: '${cfg.adServerUrl || 'http://ad-server:3000/ads/vast'}',
  },
  analytics: {
    enabled: ${cfg.analyticsEnabled},
    endpoint: 'http://your-host:3002/api/metrics',
  },
  player: {
    allowsExternalPlayback: true,
    pictureInPicture: true,
    preferredForwardBufferDuration: 30,
  },
};
`.trim();

export default function AppBuilder() {
  const [config, setConfig] = useState<AppConfig>({
    template: 'web-player',
    protocol: 'hls',
    adsEnabled: true,
    analyticsEnabled: true,
    streamUrl: '',
    adServerUrl: '',
  });
  const [showPreview, setShowPreview] = useState(false);

  const previewCode = config.template === 'react-native'
    ? generateRNConfig(config)
    : generateWebPlayerConfig(config);

  const handleDownload = () => {
    const blob = new Blob([previewCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${config.template}-config.${config.template === 'react-native' ? 'ts' : 'js'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">App Builder</h2>

      {/* Template selection */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {TEMPLATES.map(t => (
          <button
            key={t.id}
            onClick={() => setConfig(c => ({ ...c, template: t.id }))}
            className={`text-left p-4 rounded-lg border transition-colors ${
              config.template === t.id
                ? 'border-blue-500 bg-blue-900/30'
                : 'border-gray-700 bg-gray-900 hover:border-gray-500'
            }`}
          >
            <div className="font-semibold mb-1 text-white">{t.label}</div>
            <div className="text-xs text-gray-400">{t.description}</div>
          </button>
        ))}
      </div>

      {/* Options */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-5 mb-6">
        <h3 className="font-semibold mb-4 text-gray-200">Player Options</h3>
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-300 mb-1">Streaming Protocol</label>
              <select
                value={config.protocol}
                onChange={e => setConfig(c => ({ ...c, protocol: e.target.value as Protocol }))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              >
                <option value="hls">HLS only</option>
                <option value="dash">DASH only</option>
                <option value="both">HLS + DASH (auto-select)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">Stream URL</label>
              <input
                type="text"
                value={config.streamUrl}
                onChange={e => setConfig(c => ({ ...c, streamUrl: e.target.value }))}
                placeholder="http://your-host:8080/live/stream.m3u8"
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Enable Ad Integration</span>
              <button
                onClick={() => setConfig(c => ({ ...c, adsEnabled: !c.adsEnabled }))}
                className={`w-10 h-6 rounded-full transition-colors ${config.adsEnabled ? 'bg-blue-600' : 'bg-gray-600'}`}
              >
                <span className={`block w-4 h-4 bg-white rounded-full mx-1 transition-transform ${config.adsEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
              </button>
            </label>
            {config.adsEnabled && (
              <div>
                <label className="block text-sm text-gray-300 mb-1">Ad Server URL</label>
                <input
                  type="text"
                  value={config.adServerUrl}
                  onChange={e => setConfig(c => ({ ...c, adServerUrl: e.target.value }))}
                  placeholder="http://ad-server:3000/ads/vast"
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
                />
              </div>
            )}
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Enable Analytics</span>
              <button
                onClick={() => setConfig(c => ({ ...c, analyticsEnabled: !c.analyticsEnabled }))}
                className={`w-10 h-6 rounded-full transition-colors ${config.analyticsEnabled ? 'bg-blue-600' : 'bg-gray-600'}`}
              >
                <span className={`block w-4 h-4 bg-white rounded-full mx-1 transition-transform ${config.analyticsEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
              </button>
            </label>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-4">
        <button
          onClick={() => setShowPreview(!showPreview)}
          className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded text-sm transition-colors"
        >
          <Eye size={14} /> {showPreview ? 'Hide' : 'Preview'} Config
        </button>
        <button
          onClick={handleDownload}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm transition-colors"
        >
          <Download size={14} /> Download Config
        </button>
      </div>

      {/* Preview */}
      {showPreview && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <div className="px-4 py-2 border-b border-gray-800 flex items-center gap-2 text-sm text-gray-400">
            <Code2 size={14} /> Generated Configuration
          </div>
          <pre className="p-4 text-xs text-green-300 font-mono overflow-x-auto whitespace-pre-wrap">
            {previewCode}
          </pre>
        </div>
      )}
    </div>
  );
}
