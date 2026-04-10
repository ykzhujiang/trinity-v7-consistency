#!/usr/bin/env python3
"""
FFmpeg Video Concatenation + Audio Integrity Check.

Usage:
    python3 -u tools/ffmpeg_concat.py --inputs seg1.mp4 seg2.mp4 --out final.mp4
    python3 -u tools/ffmpeg_concat.py --inputs seg1.mp4 seg2.mp4 --out final.mp4 --check-audio
    python3 -u tools/ffmpeg_concat.py --help
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile


def get_duration(path: str, stream: str = "v") -> float:
    """Get duration of a stream (v=video, a=audio)."""
    r = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", stream,
        "-show_entries", "stream=duration", "-of", "csv=p=0", path
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip().split("\n")[0])
    except (ValueError, IndexError):
        return 0.0


def has_audio(path: str) -> bool:
    """Check if file has an audio stream."""
    r = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type", "-of", "csv=p=0", path
    ], capture_output=True, text=True)
    return bool(r.stdout.strip())


def concat(inputs: list, output: str) -> bool:
    """Concatenate videos with re-encode (safe for audio)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for inp in inputs:
            f.write(f"file '{os.path.abspath(inp)}'\n")
        list_path = f.name

    try:
        r = subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", output
        ], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ✗ ffmpeg failed: {r.stderr[-300:]}", flush=True)
            return False
        print(f"  ✓ Concatenated: {output}", flush=True)
        return True
    finally:
        os.unlink(list_path)


def check_audio_integrity(output: str, num_segments: int) -> dict:
    """Verify audio covers the full video duration."""
    v_dur = get_duration(output, "v")
    a_dur = get_duration(output, "a")
    has_a = has_audio(output)
    ratio = a_dur / v_dur if v_dur > 0 else 0

    result = {
        "video_duration": round(v_dur, 2),
        "audio_duration": round(a_dur, 2),
        "has_audio": has_a,
        "audio_video_ratio": round(ratio, 3),
        "pass": has_a and ratio >= 0.9,
    }

    if result["pass"]:
        print(f"  ✓ Audio OK: {a_dur:.1f}s / {v_dur:.1f}s ({ratio:.0%})", flush=True)
    else:
        print(f"  ⛔ AUDIO FAIL: audio={a_dur:.1f}s video={v_dur:.1f}s has_audio={has_a}", flush=True)

    return result


def main():
    parser = argparse.ArgumentParser(description="Concatenate videos + check audio")
    parser.add_argument("--inputs", nargs="+", required=True, help="Input video files in order")
    parser.add_argument("--out", required=True, help="Output file path")
    parser.add_argument("--check-audio", action="store_true", help="Verify audio integrity")
    parser.add_argument("--check-per-segment", action="store_true",
                        help="Also check each input segment for audio")
    args = parser.parse_args()

    # Pre-check segments
    if args.check_per_segment:
        for i, inp in enumerate(args.inputs):
            if not has_audio(inp):
                print(f"  ⛔ Segment {i+1} ({inp}) has NO audio!", flush=True)

    ok = concat(args.inputs, args.out)
    if not ok:
        sys.exit(1)

    if args.check_audio:
        result = check_audio_integrity(args.out, len(args.inputs))
        # Write check result next to output
        check_path = args.out.replace(".mp4", "-audio-check.json")
        with open(check_path, "w") as f:
            json.dump(result, f, indent=2)
        if not result["pass"]:
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
