# Video Cloud Distribution Platform

A production-ready, containerised video cloud distribution platform supporting live RTMP/SRT ingest, AI-powered scene detection, SCTE-35 ad insertion, adaptive bitrate transcoding, HLS/DASH packaging, server-side ad stitching, and real-time analytics.

---

## Architecture Overview

```
                          ┌─────────────────────────────────────────────────────────┐
                          │                   VIDEO CLOUD PLATFORM                  │
                          └─────────────────────────────────────────────────────────┘

  Encoder / Camera                             CDN / Players
  ┌─────────────┐                             ┌──────────────────────┐
  │  OBS / vMix │──RTMP/SRT──►┌───────────┐  │  Video.js / Shaka    │
  │  Hardware   │             │    SRS    │  │  HLS.js / Safari     │
  │  Encoder    │             │  Ingest   │  └──────────┬───────────┘
  └─────────────┘             │  Server   │             │ HLS/DASH
                              └─────┬─────┘             │
                                    │ RTMP stream        │
                       ┌────────────┼────────────┐       │
                       ▼            ▼            ▼       │
              ┌─────────────┐ ┌──────────┐ ┌──────────┐  │
              │   FFmpeg    │ │   YOLO   │ │ SCTE-35  │  │
              │ Transcoder  │ │Analyzer  │ │Processor │  │
              │ (ABR Ladder)│ │(Scene AI)│ │(TSDuck/  │  │
              └──────┬──────┘ └────┬─────┘ │threefive)│  │
                     │             │       └────┬─────┘  │
                     │      scene changes        │        │
                     │      + IAB context  splice│pts     │
                     ▼            ▼              ▼        │
              ┌──────────────────────────────────────┐    │
              │         Shaka Packager               │    │
              │   HLS master.m3u8 + DASH MPD         │    │
              │   EXT-X-DATERANGE SCTE-35 tags       │    │
              └─────────────────┬────────────────────┘    │
                                │                         │
                                ▼                         │
              ┌──────────────────────────────────────┐    │
              │         SSAI / Ad-Insertion          │────┘
              │  Ad Decision Server (VAST/VPAID)     │
              │  Segment replacement at splice pts   │
              │  Google Ad Manager / SpotX support   │
              └──────────────┬───────────────────────┘
                             │
              ┌──────────────┼──────────────────┐
              ▼              ▼                  ▼
       ┌────────────┐ ┌────────────┐    ┌────────────┐
       │ TimescaleDB│ │  Grafana   │    │  Postgres  │
       │ (Metrics)  │ │(Dashboards)│    │ (Ad logs)  │
       └────────────┘ └────────────┘    └────────────┘
              ▲
       ┌──────┴─────┐
       │ Prometheus │
       │ (Scraping) │
       └────────────┘

              ┌──────────────────────────────────────┐
              │        Nginx Reverse Proxy           │
              │  :80/:443  →  HLS/DASH origin        │
              │  /api/*    →  internal services      │
              └──────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Ingest** | SRS (Simple Realtime Server) | 5.x | RTMP/SRT ingest, HLS origin |
| **AI Analysis** | Ultralytics YOLO | YOLOv8n | Scene detection, content classification |
| **SCTE-35 Injection** | TSDuck | latest | MPEG-TS marker injection |
| **SCTE-35 Parsing** | threefive | 3.x | SCTE-35 encode/decode/validate |
| **Transcoding** | FFmpeg | 7.1 | ABR ladder, keyframe alignment |
| **Packaging** | Shaka Packager | 3.2.0 | HLS/DASH output, DRM-ready |
| **Player** | Video.js + Shaka Player | latest | Adaptive playback, SSAI |
| **Ad Server** | Express + VAST | custom | Ad decisions, impression tracking |
| **Time-series DB** | TimescaleDB | pg14 | Stream metrics, ad events |
| **Analytics** | Grafana + Prometheus | latest | Real-time dashboards |
| **Database** | PostgreSQL | 14 | Ad inventory, user data |
| **Proxy** | Nginx | alpine | TLS termination, routing |

---

## Features

- 📡 **Multi-protocol ingest** — RTMP, SRT, HTTP-FLV input
- 🤖 **AI scene detection** — YOLOv8 object detection drives ad opportunity identification
- 📺 **SCTE-35 splice markers** — Injection via TSDuck, parsing/encoding via threefive
- 🎬 **ABR transcoding** — 360p/480p/720p/1080p ladder with hardware acceleration support (NVENC/VAAPI/QSV)
- 📦 **HLS & DASH packaging** — Shaka Packager with `EXT-X-DATERANGE` SCTE-35 tags
- 💰 **Server-Side Ad Insertion** — VAST 3/4, Google Ad Manager, SpotX integration
- 📊 **Real-time analytics** — Prometheus → TimescaleDB → Grafana dashboards
- 🔒 **Production security** — JWT auth, Helmet.js, TLS via Nginx
- 🐳 **Fully containerised** — Docker Compose for local; Kubernetes manifests for cloud

---

## System Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| **CPU** | 4 cores | 8+ cores (or GPU for YOLO) |
| **RAM** | 8 GB | 16–32 GB |
| **Disk** | 50 GB SSD | 500 GB NVMe |
| **Network** | 100 Mbps | 1 Gbps |
| **OS** | Linux (Ubuntu 22.04+) | Ubuntu 22.04 LTS |
| **Docker** | 24.x | 25.x + Compose v2 |

---

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/your-org/video-cloud-platform.git
cd video-cloud-platform
cp .env.example .env          # edit secrets before production use

# 2. Run setup (creates directories, pulls models)
make setup

# 3. Start the full stack
make up

# 4. Verify services are healthy
make health

# 5. Push a test stream (requires ffmpeg locally)
make test-stream
```

Services after startup:

| Service | URL |
|---|---|
| HLS Playback | `http://localhost/live/stream.m3u8` |
| SRS HTTP API | `http://localhost:8080/api/v1/versions` |
| Ad Server | `http://localhost:3000/health` |
| Grafana | `http://localhost:3001` (admin / see .env) |
| Dashboard | `http://localhost:3002` |
| Prometheus | `http://localhost:9090` |

---

## Development Mode

```bash
# Hot-reload for dashboard + ad-server, source mounts, debug ports
make dev
```

---

## Kubernetes Deployment

```bash
make k8s-deploy   # kubectl apply -f kubernetes/
make k8s-delete   # kubectl delete -f kubernetes/
```

---

## Component Descriptions

### `services/ingest/` — SRS Ingest Server
Accepts RTMP (port 1935) and SRT (port 8890) streams, writes HLS segments to shared volume, exposes HTTP API on port 1985.

### `services/ai-analysis/` — YOLO Scene Analyzer
FastAPI service wrapping YOLOv8. Processes video frames, detects objects, classifies IAB content categories, returns scene-change events for ad opportunity detection.

### `services/scte35-processor/` — SCTE-35 Processor
Converts scene-change events into SCTE-35 splice_insert markers. Uses TSDuck (`tsp`) for TS stream injection and threefive for encode/decode/validation.

### `services/transcoding/` — FFmpeg Transcoder
Manages ABR transcoding jobs (live and VOD). Enforces GOP alignment at splice points using `-force_key_frames`. Supports NVENC/VAAPI/QSV hardware acceleration with CPU fallback.

### `services/packaging/` — Shaka Packager
Packages transcoded streams into HLS/DASH. Injects `EXT-X-DATERANGE` tags for SCTE-35 cue-out/cue-in. Generates master manifests.

### `services/ad-insertion/` — Ad Insertion Service
Node.js/Express server-side ad insertion engine. Fetches VAST from Google Ad Manager, SpotX, or local inventory. Stitches ad segments at splice points. Tracks impressions and clicks.

### `services/dashboard/` — Analytics Dashboard
React/Next.js real-time dashboard consuming Grafana/Prometheus metrics and ad insertion events.

---

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — Detailed architecture decisions
- [`docs/scte35-guide.md`](docs/scte35-guide.md) — SCTE-35 implementation guide
- [`docs/ad-insertion.md`](docs/ad-insertion.md) — SSAI configuration and VAST integration
- [`docs/transcoding.md`](docs/transcoding.md) — ABR profiles and hardware acceleration
- [`docs/api-reference.md`](docs/api-reference.md) — Internal service API reference
- [`docs/kubernetes.md`](docs/kubernetes.md) — Kubernetes deployment guide

---

## License

MIT © Your Organisation
Video cloud distribution platform and scte35 insertion
