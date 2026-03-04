# YOLO Integration Guide

## Overview

The platform uses YOLOv8 (You Only Look Once, version 8) from Ultralytics for real-time video content analysis. YOLO inference runs in the `yolo-analyzer` service and drives automatic SCTE-35 splice point injection based on scene changes.

---

## Model Selection

| Model | Size | mAP | Speed (CPU) | Speed (GPU T4) | Use Case |
|-------|------|-----|-------------|----------------|----------|
| `yolov8n.pt` | 6 MB | 37.3 | ~95 ms/frame | ~2 ms/frame | Development, low-power edge |
| `yolov8s.pt` | 22 MB | 44.9 | ~120 ms/frame | ~3 ms/frame | Balanced speed/accuracy |
| `yolov8m.pt` | 52 MB | 50.2 | ~230 ms/frame | ~5 ms/frame | Production (CPU) |
| `yolov8l.pt` | 87 MB | 52.9 | ~390 ms/frame | ~8 ms/frame | High accuracy |
| `yolov8x.pt` | 136 MB | 53.9 | ~640 ms/frame | ~12 ms/frame | Maximum accuracy (GPU only) |

**Recommendation:**
- CPU-only deployments: `yolov8n.pt` (nano) for real-time at 30fps with `FRAME_SKIP=5`
- GPU deployments: `yolov8x.pt` (extra-large) for maximum detection accuracy

Set via environment variable:
```bash
YOLO_MODEL=yolov8n.pt   # development
YOLO_MODEL=yolov8x.pt   # production GPU
```

---

## Scene Detection Algorithm

### Feature Extraction

Each frame is processed by the YOLO model in two stages:

1. **Object Detection**: YOLO identifies bounding boxes and class labels for all detected objects above the confidence threshold (`CONFIDENCE_THRESHOLD`, default `0.25`).

2. **Feature Vector Construction**: A 80-dimensional vector is built from YOLO's 80 COCO classes. Each dimension represents the maximum confidence score for that class across all detections in the frame. This captures the "semantic signature" of the frame.

```python
# Simplified example
feature_vector = np.zeros(80)
for detection in results:
    class_id = int(detection.cls)
    confidence = float(detection.conf)
    feature_vector[class_id] = max(feature_vector[class_id], confidence)
```

### Cosine Similarity

Scene change detection compares consecutive frame feature vectors using cosine similarity:

```
similarity = (A · B) / (||A|| × ||B||)
```

- **Similarity = 1.0**: Identical frames (no scene change)
- **Similarity ≈ 0.5**: Moderate change
- **Similarity ≈ 0.0**: Completely different scene

A scene change is triggered when similarity falls below `SCENE_CHANGE_THRESHOLD` (default `0.5`).

### Threshold Tuning

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| `0.3` | Very sensitive | News content with frequent cuts |
| `0.5` | Balanced (default) | General live sports/events |
| `0.7` | Conservative | Slow-paced content; fewer false positives |
| `0.8` | Very conservative | Continuous scene only; only major cuts |

Adjust in `services/ai-analysis/api/main.py` or via `SCENE_CHANGE_THRESHOLD` env var.

---

## Content Classification and IAB Categories

Detected objects are mapped to the IAB Tech Lab Content Taxonomy 3.0:

| YOLO Class | IAB Tier 1 | IAB Tier 2 |
|-----------|-----------|-----------|
| person | IAB14 | Society |
| car, truck, bus | IAB19 | Automotive |
| bicycle, motorcycle | IAB23 | Sports > Cycling |
| sports ball, tennis racket | IAB17 | Sports |
| dog, cat, bird | IAB16 | Pets |
| bottle, wine glass | IAB8 | Food & Drink |
| laptop, cell phone, tv | IAB19 | Technology |
| airplane | IAB21 | Travel |
| boat, ship | IAB21 | Travel > Cruises |

The full mapping is in `services/ai-analysis/content_analyzer.py` in the `ContentAnalyzer.IAB_MAPPING` dictionary.

---

## Integration with SCTE-35 Pipeline

When a scene change is detected, the YOLO analyzer publishes an event to Redis:

```json
{
  "type": "scene_change",
  "stream_id": "live/stream1",
  "pts": 1234567890.123,
  "confidence": 0.76,
  "content_category": "IAB-17",
  "iab_tier1": "Sports",
  "iab_tier2": "Motor Racing",
  "objects": ["person", "sports ball"]
}
```

The SCTE-35 processor subscribes to the `scene_changes` Redis channel and:
1. Checks if `AUTO_INJECT_ENABLED=true`
2. Calculates PTS ticks: `pts_ticks = pts_seconds * 90000`
3. Calls TSDuck to inject `splice_insert` at the calculated PTS
4. Records the marker in TimescaleDB

---

## Performance Optimization

### Frame Skipping

Processing every frame at 30fps is rarely necessary. Use `FRAME_SKIP=5` to process every 5th frame (effective 6fps analysis rate), reducing CPU load by ~80%.

```python
# In the WebSocket handler
if frame_number % FRAME_SKIP != 0:
    continue  # skip this frame
```

### Batch Processing

For GPU deployments, process multiple frames simultaneously:

```python
BATCH_SIZE=8  # Process 8 frames per GPU inference call
```

This improves GPU utilization from ~30% to >85%.

### Resolution Scaling

Resize input frames before inference to reduce computation:

```python
# YOLO default input: 640x640
# Acceptable downscale for detection: 320x320
results = model(frame, imgsz=320)  # 4x faster, ~5% accuracy loss
```

---

## GPU Acceleration with CUDA

### Prerequisites

- NVIDIA GPU with CUDA Compute Capability 6.0+
- NVIDIA CUDA Toolkit 11.8+
- cuDNN 8.x

### Setup

```bash
# Verify GPU availability inside container
docker run --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# Start with GPU enabled
GPU_ENABLED=true \
YOLO_MODEL=yolov8x.pt \
docker compose up -d yolo-analyzer
```

### Docker Compose GPU Configuration

```yaml
services:
  yolo-analyzer:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Kubernetes GPU Configuration

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

### Verifying GPU Usage

```bash
# Check YOLO service is using GPU
curl http://localhost:8000/health
# Response includes: "gpu": true, "device": "cuda:0"

# Monitor GPU utilization
nvidia-smi dmon -s u
```

---

## Downloading YOLO Models

```bash
# Download via ultralytics CLI
pip install ultralytics
yolo export model=yolov8n.pt format=pt  # CPU
yolo export model=yolov8x.pt format=pt  # GPU

# Or via Python
from ultralytics import YOLO
model = YOLO('yolov8n.pt')  # Downloads automatically on first use

# Copy to shared volume
docker cp yolov8n.pt container_name:/models/
```
