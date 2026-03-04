# TSDuck Integration Guide

## Overview

[TSDuck](https://tsduck.io/) is an MPEG-TS toolkit used for SCTE-35 splice point injection, validation, and analysis. The platform uses TSDuck's `tsp` (TS processor) pipeline to insert ad break markers into the live MPEG-TS stream.

---

## TSDuck Installation

### Ubuntu/Debian

```bash
# Add TSDuck repository
curl -s https://raw.githubusercontent.com/tsduck/tsduck/master/pkg/install-tsduck.sh | bash

# Install
apt-get install -y tsduck

# Verify
tsp --version
tsanalyze --version
```

### Docker

The `scte35-processor` service uses a TSDuck base image:

```dockerfile
FROM debian:bookworm-slim
RUN apt-get update && \
    curl -s https://raw.githubusercontent.com/tsduck/tsduck/master/pkg/install-tsduck.sh | bash && \
    apt-get install -y tsduck && \
    rm -rf /var/lib/apt/lists/*
```

### macOS

```bash
brew tap tsduck/tsduck
brew install tsduck
```

---

## SCTE-35 Marker Formats

### splice_insert

Used to signal a simple ad break with start/end times:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tsduck>
  <SCTE35 version="0" current="true" PID="500">
    <splice_info_section splice_command_type="0x05">
      <splice_insert
        splice_event_id="1"
        out_of_network="true"
        splice_immediate="false"
        unique_program_id="1">
        <splice_time PTS="2700000"/>
        <break_duration auto_return="true" duration="2700000"/>
      </splice_insert>
    </splice_info_section>
  </SCTE35>
</tsduck>
```

**Key attributes:**
- `splice_event_id`: Unique identifier (1–4294967295)
- `out_of_network`: `true` = cut to ad, `false` = return to content
- `splice_immediate`: `true` = insert now, `false` = insert at `splice_time`
- `PTS`: Presentation Timestamp in 90kHz ticks
- `duration`: Ad break duration in 90kHz ticks
- `auto_return`: If `true`, automatically insert the return-from-ad marker

### time_signal

More flexible signaling using segmentation descriptors (SCTE-35 2022):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tsduck>
  <SCTE35 version="0" current="true" PID="500">
    <splice_info_section splice_command_type="0x06">
      <time_signal>
        <splice_time PTS="2700000"/>
      </time_signal>
      <splice_descriptor tag="0x02">
        <!-- Segmentation descriptor -->
        <segmentation_descriptor
          segmentation_event_id="1"
          segmentation_type_id="0x30"
          segment_num="1"
          segments_expected="1">
          <segmentation_duration value="2700000"/>
        </segmentation_descriptor>
      </splice_descriptor>
    </splice_info_section>
  </SCTE35>
</tsduck>
```

---

## XML Schema for Splice Points

The `tsduck_injector.py` generates XML from Python objects:

```python
def build_splice_insert_xml(
    event_id: int,
    pts_ticks: int,
    duration_ticks: int,
    out_of_network: bool = True,
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<tsduck>
  <SCTE35 version="0" current="true" PID="500">
    <splice_info_section splice_command_type="0x05">
      <splice_insert
        splice_event_id="{event_id}"
        out_of_network="{str(out_of_network).lower()}"
        splice_immediate="false"
        unique_program_id="1">
        <splice_time PTS="{pts_ticks}"/>
        <break_duration auto_return="true" duration="{duration_ticks}"/>
      </splice_insert>
    </splice_info_section>
  </SCTE35>
</tsduck>"""
```

---

## PTS Calculation from Wall-Clock Time

MPEG-TS PTS values run at 90,000 Hz (90 kHz clock). To convert:

```python
PTS_HZ = 90000  # 90 kHz

def pts_from_timestamp(seconds: float) -> int:
    """Convert wall-clock seconds to PTS ticks."""
    return int(seconds * PTS_HZ)

def timestamp_from_pts(pts_ticks: int) -> float:
    """Convert PTS ticks to wall-clock seconds."""
    return pts_ticks / PTS_HZ

# Examples:
pts_from_timestamp(1.0)   # → 90000
pts_from_timestamp(30.0)  # → 2700000
pts_from_timestamp(0.5)   # → 45000
```

**Important**: PTS wraps at 2^33 ticks (~26.5 hours). For long-running streams, handle wrap-around:

```python
MAX_PTS = (1 << 33)  # 8589934592

def normalize_pts(pts: int) -> int:
    return pts % MAX_PTS
```

---

## Pipeline Integration: tsp Commands

### Basic Injection Pipeline

```bash
tsp \
  -I file input.ts \
  -P inject \
    --pid 500 \
    --xml splice_insert.xml \
    --bitrate 3000 \
  -O file output_with_scte35.ts
```

### Live Stream Injection

```bash
# Read from SRS HLS, inject SCTE-35, output to FFmpeg
tsp \
  -I http --url http://srs:8080/live/stream1.ts \
  -P inject --pid 500 --xml /tmp/current_marker.xml --bitrate 3000 \
  -O http --url http://ffmpeg-transcoder:8002/ingest/stream1
```

### Chain Multiple Processors

```bash
tsp \
  -I file input.ts \
  -P until --packet 10000 \
  -P tables --pid 500 --section-syntax short --xml-output /tmp/scte35_out.xml \
  -P inject --pid 500 --xml splice_command.xml --bitrate 3000 \
  -P continuity \
  -O file output.ts
```

---

## Validation with tsp --analyze

### Analyze SCTE-35 sections in a TS file

```bash
# List all SCTE-35 tables
tsp -I file output.ts \
  -P tables --pid 500 --section-syntax short \
  -O drop

# Extract to XML for inspection
tsp -I file output.ts \
  -P tables --pid 500 --xml-output scte35_extracted.xml \
  -O drop

# Analyze full TS structure
tsanalyze output.ts

# Check specific PID
tsp -I file output.ts -P psi --psi-merge --all-sections -O drop
```

### Verify PTS accuracy

```bash
# Show PTS values in the TS
tsp -I file output.ts -P tables --pid 500 --all-sections -O drop 2>&1 | grep -i pts
```

---

## Troubleshooting Common Issues

### "No SCTE-35 tables found in output"

**Cause**: The injected PID (500) conflicts with existing PIDs in the stream.

**Fix**: Check existing PIDs with `tsanalyze input.ts` and choose an unused PID:
```bash
tsp -I file input.ts \
  -P inject --pid 600 --xml splice.xml --bitrate 3000 \
  -O file output.ts
```

---

### "PTS is in the past"

**Cause**: The splice PTS was computed before the stream's current PTS.

**Fix**: Add a sufficient lead time (≥10 seconds) when computing the target PTS:

```python
# Get current stream PTS from SRS API
# Add 10 second lead time
target_pts = current_pts + pts_from_timestamp(10.0)
```

---

### "CRC mismatch in injected section"

**Cause**: TSDuck XML was malformed or the `duration` value overflowed 32 bits.

**Fix**: Ensure duration fits in 33 bits (`< 8589934592` ticks, ~26.5 hours):
```python
assert duration_ticks < (1 << 33), "Duration too large for SCTE-35"
```

---

### "tsp: command not found"

**Fix**: TSDuck is not installed or not in `PATH`:
```bash
which tsp || apt-get install -y tsduck
export PATH=/usr/bin:$PATH
```

---

### Markers appear but ad server is not triggered

**Cause**: The ad server is not subscribed to the Redis `scene_changes` channel, or the SCTE-35 processor is not publishing events.

**Debug**:
```bash
# Monitor Redis pub/sub
redis-cli subscribe scene_changes

# Check SCTE-35 processor logs
docker compose logs -f scte35-processor
```

---

### High CPU usage in tsp pipeline

**Cause**: Processing full-bitrate live stream without dropping packets.

**Fix**: Use `--max-flushed-packets` to control buffer size and `--bitrate-adjust` to pace output:
```bash
tsp \
  -I http --url http://srs:8080/live/stream1.ts \
  --bitrate 4000000 \
  -P inject --pid 500 --xml marker.xml --bitrate 3000 \
  -O file output.ts
```
