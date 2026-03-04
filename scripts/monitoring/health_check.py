#!/usr/bin/env python3
"""
Platform Health Check
=====================
Checks every service endpoint and prints a status summary.
Exits non-zero if any critical service is unhealthy.
"""
import sys
import time
import urllib.request
import urllib.error
from typing import List, Tuple

SERVICES: List[Tuple[str, str, bool]] = [
    # (name, url, critical)
    ("SRS HTTP API",       "http://localhost:1985/api/v1/versions",  True),
    ("SRS HLS Origin",     "http://localhost:8080/",                 False),
    ("YOLO Analyzer",      "http://localhost:8000/health",           True),
    ("SCTE-35 Processor",  "http://localhost:8001/health",           True),
    ("FFmpeg Transcoder",  "http://localhost:8002/health",           True),
    ("Shaka Packager",     "http://localhost:8003/health",           True),
    ("Ad Server",          "http://localhost:3000/health",           True),
    ("Dashboard",          "http://localhost:3002/health",           False),
    ("Grafana",            "http://localhost:3001/api/health",       False),
    ("Prometheus",         "http://localhost:9090/-/healthy",        False),
]

TIMEOUT = 5


def check(name: str, url: str) -> Tuple[bool, str]:
    try:
        req = urllib.request.urlopen(url, timeout=TIMEOUT)
        return True, f"HTTP {req.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:60]


def main() -> int:
    print("\n  Video Cloud Platform — Health Check")
    print("  " + "─" * 50)
    failures = 0
    for name, url, critical in SERVICES:
        ok, detail = check(name, url)
        icon = "✔" if ok else ("✘" if critical else "⚠")
        status = "OK" if ok else "FAIL"
        print(f"  {icon}  {name:<24} {status:<6}  {detail}")
        if not ok and critical:
            failures += 1

    print()
    if failures:
        print(f"  ✘  {failures} critical service(s) are unhealthy\n")
    else:
        print("  ✔  All critical services healthy\n")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
