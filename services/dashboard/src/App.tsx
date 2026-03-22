import { useState, useEffect, useCallback } from 'react'
import './App.css'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ServiceInfo {
  name: string
  apiPath: string
  status: 'up' | 'down' | 'loading'
  detail: string
}

interface TranscodeJob {
  job_id: string
  kind: string
  status: string
  stream_name?: string
  output_name?: string
  error?: string
}

interface SrsStream {
  id: string
  name: string
  clients: number
  kbps?: { recv_30s?: number }
}

// ── Service definitions ───────────────────────────────────────────────────────

const SERVICE_DEFS = [
  { name: 'Ad Server',    apiPath: '/api/ads/health' },
  { name: 'Transcoder',   apiPath: '/api/transcoding/health' },
  { name: 'Packager',     apiPath: '/api/packaging/health' },
  { name: 'SCTE-35',      apiPath: '/api/scte35/health' },
  { name: 'AI Analysis',  apiPath: '/api/ai/health' },
  { name: 'SRS Ingest',   apiPath: '/api/srs/api/v1/versions' },
]

// ── Helper ────────────────────────────────────────────────────────────────────

async function safeFetch<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [services, setServices] = useState<ServiceInfo[]>(
    SERVICE_DEFS.map(s => ({ ...s, status: 'loading', detail: '…' }))
  )
  const [jobs, setJobs]       = useState<TranscodeJob[]>([])
  const [streams, setStreams] = useState<SrsStream[]>([])
  const [refreshed, setRefreshed] = useState(new Date())

  const checkHealth = useCallback(async () => {
    const results = await Promise.all(
      SERVICE_DEFS.map(async (svc) => {
        try {
          const res = await fetch(svc.apiPath, { signal: AbortSignal.timeout(5000) })
          if (res.ok) {
            const data = await res.json() as Record<string, unknown>
            return { ...svc, status: 'up' as const, detail: String(data['status'] ?? 'ok') }
          }
          return { ...svc, status: 'down' as const, detail: `HTTP ${res.status}` }
        } catch {
          return { ...svc, status: 'down' as const, detail: 'unreachable' }
        }
      })
    )
    setServices(results)
    setRefreshed(new Date())
  }, [])

  const fetchJobs = useCallback(async () => {
    const data = await safeFetch<TranscodeJob[]>('/api/transcoding/jobs')
    if (data) setJobs(data)
  }, [])

  const fetchStreams = useCallback(async () => {
    const data = await safeFetch<{ streams?: SrsStream[] }>('/api/srs/api/v1/streams')
    if (data?.streams) setStreams(data.streams)
  }, [])

  useEffect(() => {
    checkHealth()
    fetchJobs()
    fetchStreams()
    const id = setInterval(() => {
      checkHealth()
      fetchJobs()
      fetchStreams()
    }, 15_000)
    return () => clearInterval(id)
  }, [checkHealth, fetchJobs, fetchStreams])

  const upCount   = services.filter(s => s.status === 'up').length
  const total     = services.length
  const allUp     = upCount === total
  const noneUp    = upCount === 0

  const host = window.location.hostname
  const grafanaUrl    = `http://${host}:3001`
  const prometheusUrl = `http://${host}:9090`

  return (
    <div className="dashboard">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="dash-header">
        <div className="dash-header-left">
          <span className="dash-logo">📡</span>
          <h1>Video Cloud Platform</h1>
          <span className={`platform-badge ${allUp ? 'badge-all-up' : noneUp ? 'badge-down' : 'badge-partial'}`}>
            {upCount}/{total} services up
          </span>
        </div>
        <div className="dash-header-right">
          <span className="refresh-label">Updated {refreshed.toLocaleTimeString()}</span>
          <button
            className="btn"
            onClick={() => { checkHealth(); fetchJobs(); fetchStreams() }}
          >
            ↻ Refresh
          </button>
        </div>
      </header>

      <main className="dash-main">

        {/* ── Service health ───────────────────────────────────────────────── */}
        <section className="panel">
          <h2 className="panel-title">Service Health</h2>
          <div className="service-grid">
            {services.map(svc => (
              <div key={svc.name} className={`svc-card svc-${svc.status}`}>
                <span className="svc-dot" />
                <span className="svc-name">{svc.name}</span>
                <span className="svc-detail">{svc.detail}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ── Streams + Jobs ───────────────────────────────────────────────── */}
        <div className="two-col">

          <section className="panel">
            <h2 className="panel-title">Active Streams ({streams.length})</h2>
            {streams.length === 0
              ? <p className="empty">No active streams</p>
              : (
                <table className="tbl">
                  <thead>
                    <tr><th>Name</th><th>Clients</th><th>Bitrate</th></tr>
                  </thead>
                  <tbody>
                    {streams.map(s => (
                      <tr key={s.id}>
                        <td>{s.name}</td>
                        <td>{s.clients}</td>
                        <td>{s.kbps?.recv_30s ?? 0} kbps</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            }
          </section>

          <section className="panel">
            <h2 className="panel-title">Transcoding Jobs ({jobs.length})</h2>
            {jobs.length === 0
              ? <p className="empty">No transcoding jobs</p>
              : (
                <table className="tbl">
                  <thead>
                    <tr><th>ID</th><th>Type</th><th>Status</th></tr>
                  </thead>
                  <tbody>
                    {[...jobs].reverse().slice(0, 10).map(j => (
                      <tr key={j.job_id}>
                        <td className="mono">{j.job_id.slice(0, 8)}</td>
                        <td>{j.kind}</td>
                        <td><span className={`job-badge job-${j.status}`}>{j.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            }
          </section>

        </div>

        {/* ── Quick links ──────────────────────────────────────────────────── */}
        <section className="panel">
          <h2 className="panel-title">Analytics &amp; API Docs</h2>
          <div className="links-grid">
            <a href={grafanaUrl}                        target="_blank" rel="noopener noreferrer" className="link-card">
              <span className="link-icon">📊</span><span>Grafana Dashboards</span>
            </a>
            <a href={prometheusUrl}                     target="_blank" rel="noopener noreferrer" className="link-card">
              <span className="link-icon">🔥</span><span>Prometheus Metrics</span>
            </a>
            <a href="/api/transcoding/docs"             target="_blank" rel="noopener noreferrer" className="link-card">
              <span className="link-icon">🎬</span><span>Transcoder API</span>
            </a>
            <a href="/api/packaging/docs"               target="_blank" rel="noopener noreferrer" className="link-card">
              <span className="link-icon">📦</span><span>Packager API</span>
            </a>
            <a href="/api/scte35/docs"                  target="_blank" rel="noopener noreferrer" className="link-card">
              <span className="link-icon">📺</span><span>SCTE-35 API</span>
            </a>
            <a href="/api/ai/docs"                      target="_blank" rel="noopener noreferrer" className="link-card">
              <span className="link-icon">🤖</span><span>AI Analysis API</span>
            </a>
          </div>
        </section>

      </main>
    </div>
  )
}

