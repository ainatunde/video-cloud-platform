#!/bin/bash
# Complete TSDuck SCTE-35 pipeline
# Usage: ./tsduck_pipeline.sh <input_ts> <output_ts> <pts_seconds>
set -e

INPUT_TS="${1:-input.ts}"
OUTPUT_TS="${2:-output_with_scte35.ts}"
PTS_SECONDS="${3:-30}"

# Validate inputs
if [[ ! -f "$INPUT_TS" ]]; then
    echo "Error: Input file '$INPUT_TS' not found"
    exit 1
fi

command -v tsp >/dev/null 2>&1 || { echo "Error: tsduck (tsp) is not installed"; exit 1; }
command -v bc >/dev/null 2>&1 || { echo "Error: bc is not installed"; exit 1; }

PTS=$(echo "$PTS_SECONDS * 90000" | bc | cut -d. -f1)
DURATION_PTS=$(echo "$PTS_SECONDS * 90000" | bc | cut -d. -f1)

echo "Injecting SCTE-35 splice_insert at PTS ${PTS} (${PTS_SECONDS}s)..."

# Create the XML splice descriptor in a temp file
SPLICE_XML=$(mktemp /tmp/scte35_XXXXXX.xml)
cat > "$SPLICE_XML" <<XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<tsduck>
  <SCTE35 version="0" current="true" PID="500">
    <splice_info_section splice_command_type="0x05">
      <splice_insert splice_event_id="1" out_of_network="true"
        splice_immediate="false" unique_program_id="1">
        <splice_time PTS="${PTS}"/>
        <break_duration auto_return="true" duration="${DURATION_PTS}"/>
      </splice_insert>
    </splice_info_section>
  </SCTE35>
</tsduck>
XMLEOF

echo "XML descriptor written to: ${SPLICE_XML}"

# Run tsp pipeline: read input → inject SCTE-35 → write output
tsp \
  -I file "$INPUT_TS" \
  -P inject \
    --pid 500 \
    --xml "$SPLICE_XML" \
    --bitrate 3000 \
  -O file "$OUTPUT_TS"

# Clean up temp file
rm -f "$SPLICE_XML"

echo "Validating SCTE-35 markers in $OUTPUT_TS..."
tsp \
  -I file "$OUTPUT_TS" \
  -P tables --pid 500 --section-syntax short \
  -O drop

echo "Done. Output written to: $OUTPUT_TS"
echo "Verify with: tsp -I file $OUTPUT_TS -P tables --pid 500 -O drop"
