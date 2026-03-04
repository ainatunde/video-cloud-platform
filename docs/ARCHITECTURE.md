# Architecture Overview

## System Architecture

```
                          ┌─────────────────────────────────────────────────────────┐
                          │                    Video Cloud Platform                  │
                          └─────────────────────────────────────────────────────────┘

  ┌──────────────┐         ┌────────────────────────────────────────────────────────┐
  │  OBS / FFmpeg│ RTMP/SRT│               Ingest Layer                             │
  │  Encoder     │────────▶│  SRS (Simple Realtime Server)                          │
  │              │         │  • RTMP :1935  • SRT :8890  • HTTP-API :1985           │
  └──────────────┘         └───────────┬─────────────────────────┬──────────────────┘
                                       │ Raw TS/FLV               │ HLS Segments
                                       ▼                          │
                          ┌─────────────────────────┐            │
                          │   AI Analysis (YOLO)     │            │
                          │   :8000                  │            │
                          │  • Scene detection       │            │
                          │  • Object classification │            │
                          │  • IAB categorization    │            │
                          └──────────┬──────────────┘            │
                                     │ Scene change events        │
                                     ▼                            │
                          ┌─────────────────────────┐            │
                          │  SCTE-35 Processor       │            │
                          │  (TSDuck + threefive)    │            │
                          │  :8001                   │            │
                          │  • Splice point injection│            │
                          │  • Marker validation     │            │
                          └──────────┬──────────────┘            │
                                     │ TS with SCTE-35            │
                                     ▼                            │
                          ┌─────────────────────────┐            │
                          │  FFmpeg Transcoder       │            │
                          │  :8002                   │            │
                          │  • ABR ladder            │◀───────────┘
                          │  • 360p/480p/720p/1080p  │
                          │  • HW accel (NVENC/VAAPI)│
                          └──────────┬──────────────┘
                                     │ Multi-bitrate TS
                                     ▼
                          ┌─────────────────────────┐
                          │  Shaka Packager          │
                          │  :8003                   │
                          │  • HLS packaging         │
                          │  • MPEG-DASH packaging   │
                          │  • Segment encryption    │
                          └──────────┬──────────────┘
                                     │ HLS/DASH manifests
                                     ▼
  ┌────────────────────────────────────────────────────────────────────────────────┐
  │                           Delivery / CDN Layer                                 │
  │  Nginx Origin    ───▶  CloudFront / Fastly / Cloudflare CDN                    │
  │  :80/:443              Global edge caching for HLS/DASH segments               │
  └───────────────────────────────────────────────────────────────────────────────┘
        │                                                         │
        │ VAST/VMAP requests                                      │ Playback
        ▼                                                         ▼
  ┌─────────────────────┐                               ┌─────────────────────────┐
  │  Ad Server (SSAI)   │                               │  End Viewers            │
  │  :3000              │                               │  Web / Mobile / Desktop │
  │  • GAM integration  │                               │  (Video.js, AVPlayer,   │
  │  • SpotX / FreeWheel│                               │   ExoPlayer, VLC)       │
  │  • VAST parser      │                               └─────────────────────────┘
  └──────────┬──────────┘
             │ Ad events
             ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │                          Analytics Layer                                      │
  │                                                                               │
  │  Redis (event bus) ──▶ Stream Metrics Collector ──▶ TimescaleDB :5432         │
  │                        Ad Analytics Collector    ──▶ (hypertables)            │
  │                                                                               │
  │  Prometheus :9090  ──▶ Grafana :3001                                          │
  │  (service metrics)     (dashboards)                                           │
  └──────────────────────────────────────────────────────────────────────────────┘
             │
             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  Management Dashboard :3002                                      │
  │  React + TypeScript + Tailwind                                   │
  │  • Stream management  • SCTE-35 config  • ABR profiles          │
  │  • Ad server config   • Analytics       • App builder           │
  └─────────────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### 1. SRS (Simple Realtime Server) — Ingest Layer

**Role**: RTMP/SRT ingest, HLS segment generation, HTTP API.

- Accepts live streams from OBS, FFmpeg, hardware encoders via RTMP (port 1935) or SRT (port 8890).
- Generates HLS `.m3u8` playlists and `.ts` segments at 6-second intervals.
- Exposes an HTTP management API at port 1985 for stream listing, client counts, and bitrate statistics.
- Supports WebRTC for browser-based ingest via the built-in RTC server.

**Configuration**: `services/ingest/srs.conf`

### 2. YOLO Analyzer — AI Content Analysis

**Role**: Real-time scene detection and content categorization using YOLO neural networks.

- Receives video frames from SRS via HTTP or WebSocket stream.
- Runs YOLOv8 inference to detect objects per frame (persons, vehicles, products, etc.).
- Computes cosine similarity between consecutive frame feature vectors to identify scene changes.
- Maps detected content to IAB content taxonomy (Tier 1 and Tier 2 categories) for ad targeting.
- Publishes scene change events to Redis for downstream SCTE-35 injection.

**Models**: YOLOv8n (CPU/dev), YOLOv8x (GPU/production)  
**API Port**: 8000  
**Configuration**: `services/ai-analysis/`

### 3. SCTE-35 Processor — Ad Break Signaling

**Role**: Inserts SCTE-35 splice point markers into the MPEG-TS stream.

- Listens for scene change events from the YOLO analyzer (via Redis pub/sub).
- Uses TSDuck (`tsp` pipeline) to inject `splice_insert` or `time_signal` SCTE-35 descriptors.
- Also integrates with `threefive` Python library for lightweight parsing and validation.
- Validates injected markers: checks PTS accuracy (±100ms tolerance), CRC integrity, section syntax.
- Exposes `/inject` REST endpoint for manual marker injection via Dashboard.

**API Port**: 8001  
**Configuration**: `services/scte35-processor/`

### 4. FFmpeg Transcoder — ABR Ladder

**Role**: Transforms ingest stream into multi-bitrate ABR ladder for adaptive streaming.

- Pulls from SRS via RTMP or reads TS with SCTE-35 markers.
- Produces four quality levels: 360p/800kbps, 480p/1400kbps, 720p/2800kbps, 1080p/5000kbps.
- Supports hardware-accelerated encoding via NVENC (NVIDIA) or VAAPI (Intel/AMD).
- Configurable via JSON preset files in `services/transcoding/presets/`.
- GOP size fixed at 60 frames (2 seconds at 30fps) for HLS segment alignment.

**API Port**: 8002  
**Presets**: `services/transcoding/presets/*.json`

### 5. Shaka Packager — HLS/DASH Packaging

**Role**: Packages multi-bitrate streams into HLS and MPEG-DASH manifests.

- Generates HLS master playlists with `#EXT-X-STREAM-INF` entries per quality level.
- Generates MPEG-DASH MPD manifests for DASH clients.
- Supports SCTE-35 splice point passthrough in HLS `#EXT-X-CUE-OUT` / `#EXT-X-CUE-IN` tags.
- Optional AES-128 or SAMPLE-AES encryption for DRM-lite protection.

**API Port**: 8003  
**Output**: `/var/www/streams` (served via Nginx)

### 6. Ad Server — SSAI Engine

**Role**: Server-Side Ad Insertion (SSAI) and VAST/VMAP integration.

- Receives ad decision requests triggered by SCTE-35 markers in the stream.
- Supports multiple ad networks: Google Ad Manager (GAM), SpotX, FreeWheel, local fallback.
- Parses VAST 2.0/3.0/4.x responses and stitches ad creative into the HLS segment timeline.
- Records impression, click, complete, and skip events to Redis for async analytics ingestion.
- Exposes VAST endpoint at `/ads/vast/{id}` for client-side ad requests (CSAI fallback).

**API Port**: 3000  
**Configuration**: `services/ad-insertion/config/ad-servers.json`

### 7. TimescaleDB — Time-Series Analytics Storage

**Role**: PostgreSQL-compatible time-series database optimized for metrics.

- Stores four hypertables: `stream_metrics`, `content_analysis`, `scte35_markers`, `ad_analytics`.
- Continuous aggregate `stream_metrics_hourly` pre-computes hourly rollups automatically.
- `ad_fill_rate` view provides real-time completion rate calculations.
- Handles hundreds of thousands of inserts per minute with automatic chunk compression.

**Port**: 5432  
**Init SQL**: `services/analytics/timescaledb/init.sql`

### 8. Grafana — Dashboards

**Role**: Real-time visualization of all platform metrics.

Five pre-built dashboards:
- **Streaming Overview**: Active streams, viewer count, bitrate trends, geo distribution.
- **AI Content Analysis**: Object detections/sec, content categories, scene changes.
- **SCTE-35 Markers**: Marker count, validation rate, type distribution, timeline.
- **Ad Performance**: Impressions, completion rate, CTR, fill rate over time.
- **Quality Metrics**: Startup time, buffering ratio, packet loss, jitter, latency histogram.

**Port**: 3001  
**Datasource**: TimescaleDB via PostgreSQL plugin

### 9. Management Dashboard — React Frontend

**Role**: Unified operator control panel.

- **Stream Manager**: Lists active streams, displays RTMP/SRT ingest URLs and live stats.
- **SCTE-35 Config**: Toggle AI auto-insertion, configure splice duration/type, manual injection.
- **ABR Config**: Edit quality profiles, toggle hardware acceleration, adjust GOP and segment settings.
- **Ad Server Config**: Enable/disable ad networks, update VAST URLs, test ad requests.
- **Analytics**: Embeds Grafana panels, shows key metric stat cards.
- **App Builder**: Generate configuration for web, React Native, or Electron video apps.

**Port**: 3002

---

## Data Flow

```
Stream Ingest
    │
    ├──▶ SRS stores HLS segments → local filesystem
    │
    ├──▶ YOLO Analyzer receives frames
    │        │
    │        └──▶ Scene change detected → Redis pub/sub "scene_changes"
    │
    └──▶ SCTE-35 Processor subscribes to Redis
              │
              └──▶ tsp pipeline injects SCTE-35 marker into TS
                        │
                        └──▶ FFmpeg Transcoder pulls modified TS
                                  │
                                  ├──▶ Encodes 360p, 480p, 720p, 1080p
                                  │
                                  └──▶ Shaka Packager creates HLS/DASH
                                            │
                                            └──▶ Nginx Origin → CDN → Viewers
                                                      │
                                                      └──▶ Ad Server triggered by SCTE-35
                                                                │
                                                                ├──▶ VAST request to GAM/SpotX
                                                                │
                                                                └──▶ Ad events → Redis → TimescaleDB
```

---

## Technology Decisions and Rationale

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Ingest | SRS | Battle-tested RTMP/SRT server; HTTP API simplifies monitoring; written in C for low latency |
| AI Analysis | YOLOv8 (Ultralytics) | State-of-the-art speed/accuracy tradeoff; Python ecosystem; ONNX export for GPU acceleration |
| SCTE-35 | TSDuck + threefive | TSDuck provides production-grade TS manipulation; threefive enables lightweight Python parsing |
| Transcoding | FFmpeg | De-facto standard; NVENC/VAAPI HW accel; widest codec support |
| Packaging | Shaka Packager | Google-backed; supports HLS + DASH + SCTE-35 passthrough; segment encryption |
| Time-series DB | TimescaleDB | PostgreSQL compatibility; automatic partitioning; continuous aggregates; SQL familiarity |
| Dashboards | Grafana | Rich visualization; TimescaleDB/Postgres datasource; alerting; team collaboration |
| Frontend | React + TypeScript | Type safety; component reuse; large ecosystem; Vite for fast builds |
| Container Orchestration | Kubernetes | Industry standard; horizontal pod autoscaling; cloud-portable |

---

## Scalability Considerations

### Horizontal Scaling

- **SRS**: Deploy multiple instances behind a Layer-4 load balancer (NLB). Streams are sticky to origin; use shared NFS/S3 for HLS segment storage.
- **FFmpeg Transcoder**: Stateless; scale replicas based on CPU/GPU utilization. Use KEDA for event-driven autoscaling triggered by SRS stream count.
- **Ad Server**: Stateless Node.js; scale horizontally with HPA (`minReplicas: 2`, `maxReplicas: 10`).
- **TimescaleDB**: Use TimescaleDB multi-node (access + data nodes) for write-heavy workloads exceeding 100k rows/sec.
- **Shaka Packager**: Stateless; each instance processes independent streams. Scale with stream count.

### CDN Integration

Segment URLs follow the pattern `https://cdn.example.com/hls/{stream_id}/{segment}.ts`. Configure CDN with:
- **Cache-Control**: `max-age=6` for `.ts` segments, `max-age=2` for `.m3u8` playlists.
- **Origin Shield**: Route all CDN misses through a single origin region to prevent thundering herd.
- **Geo-routing**: Route viewers to nearest CDN PoP; use latency-based routing for live streams.

### GPU Acceleration

For production deployments with >10 concurrent 1080p streams, enable NVENC:
1. Set `HARDWARE_ACCEL=nvenc` in the FFmpeg transcoder environment.
2. Use `h264_nvenc` codec with preset `p4` (balanced quality/speed).
3. Deploy on GPU-enabled nodes (`nvidia.com/gpu: 1` resource request).
4. YOLO inference switches to CUDA automatically when `GPU_ENABLED=true`.

---

## Security Architecture

### Network Isolation

All internal services communicate within the `video-platform` Kubernetes namespace using ClusterIP services. Only the following ports are externally exposed via the Ingress or LoadBalancer:
- SRS: RTMP (1935), SRT (8890) — ingest only
- Dashboard: HTTP (3000) — operator access
- Nginx Origin: HTTP (80) — CDN pull

### Secrets Management

All credentials are stored in Kubernetes Secrets (`platform-secrets`):
- `postgres-password` — TimescaleDB admin password
- `database-url` — Full connection string for services
- `grafana-admin-password` — Grafana admin UI password

In production, integrate with AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault via the External Secrets Operator.

### TLS/SSL

The Nginx Ingress controller handles TLS termination. Configure cert-manager with Let's Encrypt:
```yaml
annotations:
  cert-manager.io/cluster-issuer: "letsencrypt-prod"
```

### RTMP Authentication

Enable publish token validation via SRS HTTP hooks:
```conf
http_hooks {
    enabled     on;
    on_publish  http://ad-server:3000/hooks/on_publish;
}
```

The ad server validates a `?token=<jwt>` query parameter on the RTMP publish URL.
