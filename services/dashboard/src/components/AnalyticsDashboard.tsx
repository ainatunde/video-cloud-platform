import React from 'react';
import { BarChart2, Users, Tv, Clock } from 'lucide-react';

const GRAFANA_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:3001'
  : '/grafana';

const STAT_CARDS = [
  { icon: Tv, label: 'Active Streams', value: '—', color: 'text-green-400' },
  { icon: Users, label: 'Total Viewers', value: '—', color: 'text-blue-400' },
  { icon: BarChart2, label: 'Ad Fill Rate', value: '—', color: 'text-yellow-400' },
  { icon: Clock, label: 'Avg Latency', value: '—', color: 'text-purple-400' },
];

interface GrafanaPanel {
  title: string;
  uid: string;
  panelId: number;
  height: number;
}

const PANELS: GrafanaPanel[] = [
  { title: 'Streaming Overview', uid: 'streaming-overview', panelId: 3, height: 300 },
  { title: 'Avg Latency', uid: 'quality-metrics', panelId: 3, height: 300 },
  { title: 'Ad Performance', uid: 'ad-performance', panelId: 6, height: 300 },
  { title: 'SCTE-35 Markers Timeline', uid: 'scte35-markers', panelId: 5, height: 300 },
];

export default function AnalyticsDashboard() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Analytics Dashboard</h2>

      {/* Quick stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {STAT_CARDS.map(card => (
          <div key={card.label} className="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
              <card.icon size={14} />
              {card.label}
            </div>
            <div className={`text-3xl font-bold ${card.color}`}>{card.value}</div>
            <div className="text-xs text-gray-500 mt-1">Live from TimescaleDB</div>
          </div>
        ))}
      </div>

      {/* Grafana iframe panels */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {PANELS.map(panel => (
          <div key={panel.uid + panel.panelId} className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
            <div className="px-3 py-2 border-b border-gray-800 text-sm font-medium text-gray-300">
              {panel.title}
            </div>
            <iframe
              src={`${GRAFANA_URL}/d-solo/${panel.uid}?orgId=1&panelId=${panel.panelId}&refresh=5s&theme=dark`}
              width="100%"
              height={panel.height}
              frameBorder="0"
              title={panel.title}
              className="bg-gray-900"
            />
          </div>
        ))}
      </div>

      {/* Full dashboard links */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <h3 className="font-semibold mb-3 text-gray-300">Full Grafana Dashboards</h3>
        <div className="flex flex-wrap gap-3">
          {[
            { label: 'Streaming Overview', uid: 'streaming-overview' },
            { label: 'AI Content Analysis', uid: 'ai-content-analysis' },
            { label: 'SCTE-35 Markers', uid: 'scte35-markers' },
            { label: 'Ad Performance', uid: 'ad-performance' },
            { label: 'Quality Metrics', uid: 'quality-metrics' },
          ].map(d => (
            <a
              key={d.uid}
              href={`${GRAFANA_URL}/d/${d.uid}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-blue-400 hover:text-blue-300 rounded text-sm transition-colors"
            >
              {d.label} ↗
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
