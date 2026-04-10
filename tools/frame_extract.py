#!/usr/bin/env python3
"""
Extract frames from video files.

Usage:
    python3 -u tools/frame_extract.py --input seg1.mp4 --last --out last-frame.png
    python3 -u tools/frame_extract.py --input seg1.mp4 --at 7.5 --out mid-frame.png
    python3 -u tools/frame_extract.py --help
"""

import argparse
import os
import subprocess
import sys


def extract_last_frame(video: str, output: str) -> bool:
    r = subprocess.run([
        "ffmpeg", "-sseof", "-0.1", "-i", video,
        "-frames:v", "1", "-y", output
    ], capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(output):
        print(f"  ✓ Last frame: {output}", flush=True)
        return True
    print(f"  ✗ Failed: {r.stderr[-200:]}", flush=True)
    return False


def extract_at(video: str, timestamp: float, output: str) -> bool:
    r = subprocess.run([
        "ffmpeg", "-ss", str(timestamp), "-i", video,
        "-frames:v", "1", "-y", output
    ], capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(output):
        print(f"  ✓ Frame @{timestamp}s: {output}", flush=True)
        return True
    print(f"  ✗ Failed: {r.stderr[-200:]}", flush=True)
    return False


def main():
    parser = argparse.ArgumentParser(description="Extract frames from video")
    parser.add_argument("--input", required=True, help="Input video")
    parser.add_argument("--out", required=True, help="Output image path")
    parser.add_argument("--last", action="store_true", help="Extract last frame")
    parser.add_argument("--at", type=float, help="Extract frame at timestamp (seconds)")
    args = parser.parse_args()

    if args.last:
        ok = extract_last_frame(args.input, args.out)
    elif args.at is not None:
        ok = extract_at(args.input, args.at, args.out)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
