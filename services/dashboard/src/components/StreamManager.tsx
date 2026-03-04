import React, { useState, useEffect } from 'react';
import { Activity, Users, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import axios from 'axios';

interface Stream {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'error';
  ingestUrl: string;
  hlsUrl: string;
  viewers: number;
  bitrate: number;
  fps: number;
  createdAt: string;
}

const MOCK_STREAMS: Stream[] = [
  {
    id: 'live/stream1',
    name: 'Main Stage Feed',
    status: 'active',
    ingestUrl: 'rtmp://localhost:1935/live/stream1',
    hlsUrl: 'http://localhost:8080/live/stream1.m3u8',
    viewers: 1243,
    bitrate: 4200000,
    fps: 30,
    createdAt: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 'live/stream2',
    name: 'Backup Feed',
    status: 'idle',
    ingestUrl: 'rtmp://localhost:1935/live/stream2',
    hlsUrl: 'http://localhost:8080/live/stream2.m3u8',
    viewers: 0,
    bitrate: 0,
    fps: 0,
    createdAt: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 'live/stream3',
    name: 'Mobile Ingest',
    status: 'active',
    ingestUrl: 'srt://localhost:8890?streamid=live/stream3',
    hlsUrl: 'http://localhost:8080/live/stream3.m3u8',
    viewers: 389,
    bitrate: 2100000,
    fps: 25,
    createdAt: new Date(Date.now() - 1800000).toISOString(),
  },
];

function StatusBadge({ status }: { status: Stream['status'] }) {
  const colors = {
    active: 'bg-green-900 text-green-300 border border-green-700',
    idle: 'bg-gray-800 text-gray-400 border border-gray-600',
    error: 'bg-red-900 text-red-300 border border-red-700',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status]}`}>
      {status.toUpperCase()}
    </span>
  );
}

function formatBitrate(bps: number): string {
  if (bps === 0) return '—';
  if (bps >= 1_000_000) return `${(bps / 1_000_000).toFixed(1)} Mbps`;
  return `${(bps / 1_000).toFixed(0)} kbps`;
}

function formatUptime(createdAt: string): string {
  const seconds = Math.floor((Date.now() - new Date(createdAt).getTime()) / 1000);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h}h ${m}m ${s}s`;
}

export default function StreamManager() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStreams = async () => {
    try {
      const res = await axios.get('/api/streams', { timeout: 5000 });
      const raw = res.data?.streams ?? [];
      const mapped: Stream[] = raw.map((s: Record<string, unknown>) => ({
        id: String(s.id ?? ''),
        name: String(s.name ?? s.id ?? ''),
        status: (s.clients as number) > 0 ? 'active' : 'idle',
        ingestUrl: `rtmp://localhost:1935/${s.id}`,
        hlsUrl: `http://localhost:8080/${s.id}.m3u8`,
        viewers: Number(s.clients ?? 0),
        bitrate: Number((s as Record<string, Record<string, number>>).kbps?.recv_30s ?? 0) * 1000,
        fps: Number((s as Record<string, Record<string, number>>).video?.fps ?? 0),
        createdAt: new Date().toISOString(),
      }));
      setStreams(mapped.length ? mapped : MOCK_STREAMS);
      setError(null);
    } catch {
      setStreams(MOCK_STREAMS);
      setError('Using mock data — SRS API not reachable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStreams();
    const id = setInterval(fetchStreams, 10000);
    return () => clearInterval(id);
  }, []);

  const activeCount = streams.filter(s => s.status === 'active').length;
  const totalViewers = streams.reduce((sum, s) => sum + s.viewers, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Stream Manager</h2>
        <button
          onClick={fetchStreams}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-sm"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 px-4 py-2 bg-yellow-900/40 border border-yellow-700 rounded text-yellow-300 text-sm">
          {error}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Activity size={14} /> Active Streams
          </div>
          <div className="text-3xl font-bold text-green-400">{activeCount}</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Users size={14} /> Total Viewers
          </div>
          <div className="text-3xl font-bold text-blue-400">{totalViewers.toLocaleString()}</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Wifi size={14} /> Total Streams
          </div>
          <div className="text-3xl font-bold text-gray-200">{streams.length}</div>
        </div>
      </div>

      {/* Stream table */}
      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading streams…</div>
      ) : (
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-left">
                <th className="px-4 py-3">Stream</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Ingest URL</th>
                <th className="px-4 py-3">Viewers</th>
                <th className="px-4 py-3">Bitrate</th>
                <th className="px-4 py-3">FPS</th>
                <th className="px-4 py-3">Uptime</th>
                <th className="px-4 py-3">HLS</th>
              </tr>
            </thead>
            <tbody>
              {streams.map(stream => (
                <tr key={stream.id} className="border-b border-gray-800/50 hover:bg-gray-800/40">
                  <td className="px-4 py-3 font-medium text-white">{stream.name}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={stream.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-400 font-mono text-xs truncate max-w-48">
                    {stream.ingestUrl}
                  </td>
                  <td className="px-4 py-3 text-blue-300">
                    {stream.status === 'active' ? stream.viewers.toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3">{formatBitrate(stream.bitrate)}</td>
                  <td className="px-4 py-3">{stream.fps > 0 ? `${stream.fps}` : '—'}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{formatUptime(stream.createdAt)}</td>
                  <td className="px-4 py-3">
                    {stream.status === 'active' ? (
                      <a
                        href={stream.hlsUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 text-xs underline"
                      >
                        Play
                      </a>
                    ) : (
                      <span className="text-gray-600 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Ingest instructions */}
      <div className="mt-6 bg-gray-900 rounded-lg border border-gray-800 p-4">
        <h3 className="font-semibold mb-2 text-gray-300">Ingest Endpoints</h3>
        <div className="space-y-2 text-sm">
          <div>
            <span className="text-gray-400">RTMP:</span>{' '}
            <code className="text-green-300 font-mono">rtmp://&lt;host&gt;:1935/live/&lt;stream-key&gt;</code>
          </div>
          <div>
            <span className="text-gray-400">SRT:</span>{' '}
            <code className="text-green-300 font-mono">srt://&lt;host&gt;:8890?streamid=live/&lt;stream-key&gt;</code>
          </div>
          <div>
            <span className="text-gray-400">HLS playback:</span>{' '}
            <code className="text-green-300 font-mono">http://&lt;host&gt;:8080/live/&lt;stream-key&gt;.m3u8</code>
          </div>
        </div>
      </div>
    </div>
  );
}
