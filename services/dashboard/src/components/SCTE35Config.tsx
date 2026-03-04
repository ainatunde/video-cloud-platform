import React, { useState } from 'react';
import { Tag, Play, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import axios from 'axios';

type SpliceType = 'splice_insert' | 'time_signal';

interface MarkerConfig {
  aiEnabled: boolean;
  spliceDuration: number;
  spliceType: SpliceType;
  streamId: string;
}

interface MarkerRecord {
  id: number;
  time: string;
  streamId: string;
  type: SpliceType;
  duration: number;
  pts: number;
  validated: boolean;
}

const MOCK_HISTORY: MarkerRecord[] = [
  { id: 1, time: new Date(Date.now() - 60000).toISOString(), streamId: 'live/stream1', type: 'splice_insert', duration: 30, pts: 2700000, validated: true },
  { id: 2, time: new Date(Date.now() - 180000).toISOString(), streamId: 'live/stream1', type: 'splice_insert', duration: 30, pts: 1620000, validated: true },
  { id: 3, time: new Date(Date.now() - 420000).toISOString(), streamId: 'live/stream3', type: 'time_signal', duration: 15, pts: 810000, validated: false },
];

export default function SCTE35Config() {
  const [config, setConfig] = useState<MarkerConfig>({
    aiEnabled: true,
    spliceDuration: 30,
    spliceType: 'splice_insert',
    streamId: 'live/stream1',
  });
  const [manualPts, setManualPts] = useState('');
  const [manualDuration, setManualDuration] = useState('30');
  const [history, setHistory] = useState<MarkerRecord[]>(MOCK_HISTORY);
  const [injecting, setInjecting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const handleInject = async () => {
    if (!manualPts) return;
    setInjecting(true);
    setFeedback(null);
    try {
      await axios.post('/api/scte35/inject', {
        stream_id: config.streamId,
        pts: parseFloat(manualPts),
        duration: parseFloat(manualDuration),
        splice_type: config.spliceType,
      });
      const newRecord: MarkerRecord = {
        id: Date.now(),
        time: new Date().toISOString(),
        streamId: config.streamId,
        type: config.spliceType,
        duration: parseFloat(manualDuration),
        pts: parseFloat(manualPts) * 90000,
        validated: false,
      };
      setHistory(prev => [newRecord, ...prev]);
      setFeedback({ type: 'success', msg: 'Marker injected successfully' });
      setManualPts('');
    } catch {
      setFeedback({ type: 'error', msg: 'Injection failed — check SCTE-35 processor logs' });
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">SCTE-35 Configuration</h2>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* AI Auto-Insertion */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2 text-gray-200">
            <Tag size={16} /> Auto-Insertion Settings
          </h3>
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-300">AI-Based Auto Insertion</span>
              <button
                onClick={() => setConfig(c => ({ ...c, aiEnabled: !c.aiEnabled }))}
                className={`w-10 h-6 rounded-full transition-colors ${config.aiEnabled ? 'bg-blue-600' : 'bg-gray-600'}`}
              >
                <span className={`block w-4 h-4 bg-white rounded-full mx-1 transition-transform ${config.aiEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
              </button>
            </label>

            <div>
              <label className="block text-sm text-gray-300 mb-1">
                Splice Type
              </label>
              <select
                value={config.spliceType}
                onChange={e => setConfig(c => ({ ...c, spliceType: e.target.value as SpliceType }))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              >
                <option value="splice_insert">splice_insert</option>
                <option value="time_signal">time_signal</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-1">
                Splice Duration: <span className="text-blue-400">{config.spliceDuration}s</span>
              </label>
              <input
                type="range"
                min={5}
                max={120}
                step={5}
                value={config.spliceDuration}
                onChange={e => setConfig(c => ({ ...c, spliceDuration: parseInt(e.target.value) }))}
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>5s</span><span>120s</span>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-1">Target Stream ID</label>
              <input
                type="text"
                value={config.streamId}
                onChange={e => setConfig(c => ({ ...c, streamId: e.target.value }))}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
                placeholder="live/stream1"
              />
            </div>
          </div>
        </div>

        {/* Manual Injection */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2 text-gray-200">
            <Play size={16} /> Manual Marker Injection
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-300 mb-1">PTS (seconds)</label>
              <input
                type="number"
                value={manualPts}
                onChange={e => setManualPts(e.target.value)}
                placeholder="e.g. 30.0"
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">Duration (seconds)</label>
              <input
                type="number"
                value={manualDuration}
                onChange={e => setManualDuration(e.target.value)}
                placeholder="30"
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              />
            </div>
            {feedback && (
              <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded ${feedback.type === 'success' ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
                {feedback.type === 'success' ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
                {feedback.msg}
              </div>
            )}
            <button
              onClick={handleInject}
              disabled={injecting || !manualPts}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
            >
              {injecting ? 'Injecting…' : 'Inject Marker'}
            </button>
          </div>
        </div>
      </div>

      {/* Marker History */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
          <Clock size={14} className="text-gray-400" />
          <span className="font-semibold text-sm text-gray-300">Recent Markers</span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-left">
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Stream</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3">PTS</th>
              <th className="px-4 py-3">Validated</th>
            </tr>
          </thead>
          <tbody>
            {history.map(m => (
              <tr key={m.id} className="border-b border-gray-800/50 hover:bg-gray-800/40">
                <td className="px-4 py-3 text-gray-400 text-xs">{new Date(m.time).toLocaleTimeString()}</td>
                <td className="px-4 py-3 font-mono text-xs">{m.streamId}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 bg-purple-900/50 text-purple-300 rounded text-xs">{m.type}</span>
                </td>
                <td className="px-4 py-3">{m.duration}s</td>
                <td className="px-4 py-3 font-mono text-xs text-gray-400">{m.pts}</td>
                <td className="px-4 py-3">
                  {m.validated
                    ? <CheckCircle size={14} className="text-green-400" />
                    : <Clock size={14} className="text-yellow-400" />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
