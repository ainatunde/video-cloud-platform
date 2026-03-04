#!/usr/bin/env python3
"""Standalone YOLO scene detector script."""
import sys
import os
import json
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Detect scene changes in a video using YOLO'
    )
    parser.add_argument('video', help='Input video file path')
    parser.add_argument('--model', default='yolov8n.pt', help='YOLO model file (default: yolov8n.pt)')
    parser.add_argument('--threshold', type=float, default=0.5,
                        help='Scene change sensitivity threshold 0.0-1.0 (default: 0.5)')
    parser.add_argument('--output', default='scene_changes.json',
                        help='Output JSON file path (default: scene_changes.json)')
    parser.add_argument('--frame-skip', type=int, default=5,
                        help='Process every Nth frame (default: 5)')
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print(f"Error: Video file '{args.video}' not found", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../services/ai-analysis'))

    try:
        from yolo_scene_detector import YOLOSceneDetector
    except ImportError as e:
        print(f"Error: Cannot import YOLOSceneDetector: {e}", file=sys.stderr)
        print("Ensure services/ai-analysis/yolo_scene_detector.py exists and dependencies are installed",
              file=sys.stderr)
        sys.exit(1)

    print(f"Loading YOLO model: {args.model}")
    detector = YOLOSceneDetector(
        model_path=args.model,
        scene_change_threshold=args.threshold,
    )

    print(f"Analyzing video: {args.video}")
    print(f"  Frame skip: {args.frame_skip}, Threshold: {args.threshold}")

    scene_changes = detector.batch_process_video(args.video)

    output = [
        {
            "timestamp": sc.timestamp,
            "confidence": sc.confidence,
            "objects_before": sc.objects_before,
            "objects_after": sc.objects_after,
        }
        for sc in scene_changes
    ]

    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nFound {len(scene_changes)} scene changes. Saved to: {args.output}")
    print("")
    for sc in scene_changes:
        print(f"  t={sc.timestamp:7.2f}s  confidence={sc.confidence:.3f}  "
              f"objects: {sc.objects_before} → {sc.objects_after}")


if __name__ == '__main__':
    main()
