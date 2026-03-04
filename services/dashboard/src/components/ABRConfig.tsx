import React, { useState } from 'react';
import { Settings, Cpu, Video } from 'lucide-react';

interface ABRProfile {
  name: string;
  width: number;
  height: number;
  videoBitrate: number;
  audioBitrate: number;
  codec: string;
  preset: string;
  enabled: boolean;
}

const DEFAULT_PROFILES: ABRProfile[] = [
  { name: '360p', width: 640, height: 360, videoBitrate: 800, audioBitrate: 64, codec: 'libx264', preset: 'fast', enabled: true },
  { name: '480p', width: 854, height: 480, videoBitrate: 1400, audioBitrate: 96, codec: 'libx264', preset: 'fast', enabled: true },
  { name: '720p', width: 1280, height: 720, videoBitrate: 2800, audioBitrate: 128, codec: 'libx264', preset: 'fast', enabled: true },
  { name: '1080p', width: 1920, height: 1080, videoBitrate: 5000, audioBitrate: 192, codec: 'libx264', preset: 'medium', enabled: true },
];

interface GlobalConfig {
  hwAccel: boolean;
  gopSize: number;
  segmentDuration: number;
  hlsWindow: number;
}

export default function ABRConfig() {
  const [profiles, setProfiles] = useState<ABRProfile[]>(DEFAULT_PROFILES);
  const [global, setGlobal] = useState<GlobalConfig>({
    hwAccel: false,
    gopSize: 60,
    segmentDuration: 6,
    hlsWindow: 10,
  });
  const [saved, setSaved] = useState(false);

  const updateProfile = (index: number, field: keyof ABRProfile, value: string | number | boolean) => {
    setProfiles(prev => prev.map((p, i) => i === index ? { ...p, [field]: value } : p));
    setSaved(false);
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">ABR Configuration</h2>
        <button
          onClick={handleSave}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${saved ? 'bg-green-600 text-white' : 'bg-blue-600 hover:bg-blue-500 text-white'}`}
        >
          {saved ? '✓ Saved' : 'Save Configuration'}
        </button>
      </div>

      {/* Global settings */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-5 mb-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2 text-gray-200">
          <Settings size={16} /> Global Settings
        </h3>
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-300 flex items-center gap-2">
                <Cpu size={14} /> Hardware Acceleration (NVENC/VAAPI)
              </span>
              <button
                onClick={() => setGlobal(g => ({ ...g, hwAccel: !g.hwAccel }))}
                className={`w-10 h-6 rounded-full transition-colors ${global.hwAccel ? 'bg-blue-600' : 'bg-gray-600'}`}
              >
                <span className={`block w-4 h-4 bg-white rounded-full mx-1 transition-transform ${global.hwAccel ? 'translate-x-4' : 'translate-x-0'}`} />
              </button>
            </label>
            <div>
              <label className="block text-sm text-gray-300 mb-1">GOP Size (frames)</label>
              <input
                type="number"
                value={global.gopSize}
                onChange={e => setGlobal(g => ({ ...g, gopSize: parseInt(e.target.value) }))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-300 mb-1">HLS Segment Duration (s)</label>
              <input
                type="number"
                value={global.segmentDuration}
                onChange={e => setGlobal(g => ({ ...g, segmentDuration: parseInt(e.target.value) }))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">HLS Window Size (segments)</label>
              <input
                type="number"
                value={global.hlsWindow}
                onChange={e => setGlobal(g => ({ ...g, hlsWindow: parseInt(e.target.value) }))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Profile table */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
          <Video size={14} className="text-gray-400" />
          <span className="font-semibold text-sm text-gray-300">ABR Profiles</span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-left">
              <th className="px-4 py-3">Profile</th>
              <th className="px-4 py-3">Resolution</th>
              <th className="px-4 py-3">Video Bitrate (kbps)</th>
              <th className="px-4 py-3">Audio Bitrate (kbps)</th>
              <th className="px-4 py-3">Codec</th>
              <th className="px-4 py-3">Preset</th>
              <th className="px-4 py-3">Enabled</th>
            </tr>
          </thead>
          <tbody>
            {profiles.map((p, i) => (
              <tr key={p.name} className="border-b border-gray-800/50">
                <td className="px-4 py-3 font-medium text-white">{p.name}</td>
                <td className="px-4 py-3 text-gray-400">{p.width}×{p.height}</td>
                <td className="px-4 py-3">
                  <input
                    type="number"
                    value={p.videoBitrate}
                    onChange={e => updateProfile(i, 'videoBitrate', parseInt(e.target.value))}
                    className="w-24 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                  />
                </td>
                <td className="px-4 py-3">
                  <input
                    type="number"
                    value={p.audioBitrate}
                    onChange={e => updateProfile(i, 'audioBitrate', parseInt(e.target.value))}
                    className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                  />
                </td>
                <td className="px-4 py-3">
                  <select
                    value={p.codec}
                    onChange={e => updateProfile(i, 'codec', e.target.value)}
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                  >
                    <option value="libx264">libx264</option>
                    <option value="h264_nvenc">h264_nvenc</option>
                    <option value="libx265">libx265</option>
                    <option value="hevc_nvenc">hevc_nvenc</option>
                  </select>
                </td>
                <td className="px-4 py-3">
                  <select
                    value={p.preset}
                    onChange={e => updateProfile(i, 'preset', e.target.value)}
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                  >
                    <option value="ultrafast">ultrafast</option>
                    <option value="fast">fast</option>
                    <option value="medium">medium</option>
                    <option value="slow">slow</option>
                  </select>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => updateProfile(i, 'enabled', !p.enabled)}
                    className={`w-8 h-5 rounded-full transition-colors ${p.enabled ? 'bg-blue-600' : 'bg-gray-600'}`}
                  >
                    <span className={`block w-3 h-3 bg-white rounded-full mx-0.5 transition-transform ${p.enabled ? 'translate-x-4' : 'translate-x-0'}`} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
