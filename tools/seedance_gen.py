#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0"]
# ///
"""
Seedance 2.0 Video Generator — Supports concurrent task submission + polling.

Usage:
    # Single generation
    python3 -u tools/seedance_gen.py --prompt "..." --images img1.webp img2.webp --out seg1.mp4

    # With video extension (Seg2)
    python3 -u tools/seedance_gen.py --prompt "..." --video seg1.mp4 --out seg2.mp4

    # Batch mode (concurrent)
    python3 -u tools/seedance_gen.py --batch batch.json --out-dir output/

Batch JSON format:
[
  {"id": "anime-seg1", "prompt": "...", "images": ["a.webp"], "out": "anime-seg1.mp4"},
  {"id": "real-seg1",  "prompt": "...", "images": ["b.webp"], "out": "real-seg1.mp4"}
]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_keys


def upload_to_tmpfiles(local_path: str, max_retries: int = 5) -> str:
    """Upload a local file to tmpfiles.org and return direct download URL."""
    import requests
    print(f"  Uploading {os.path.basename(local_path)} to tmpfiles.org...", flush=True)
    for attempt in range(1, max_retries + 1):
        try:
            with open(local_path, "rb") as f:
                resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=180)
            resp.raise_for_status()
            page_url = resp.json()["data"]["url"]
            direct_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            print(f"  → {direct_url}", flush=True)
            return direct_url
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"  ⚠ Upload attempt {attempt}/{max_retries} failed: {e}", flush=True)
            if attempt < max_retries:
                wait = 15 * attempt
                print(f"  Retrying in {wait}s...", flush=True)
                time.sleep(wait)
            else:
                raise


def run_seedance(seedance_script: str, ark_key: str, prompt: str,
                 images: list = None, video: str = None,
                 output: str = "output.mp4", duration: int = 15,
                 ratio: str = "9:16", keep_audio: bool = False) -> dict:
    """Run seedance.py. Returns {"ok": bool, "path": str, "error": str}."""
    cmd = [
        "python3", "-u", seedance_script, "run",
        "--prompt", prompt,
        "--ratio", ratio,
        "--duration", str(duration),
        "--out", output,
    ]

    if video:
        v = video
        if os.path.isfile(v) and not v.startswith("http"):
            if keep_audio:
                print(f"  --keep-audio: preserving audio track in {os.path.basename(v)}", flush=True)
            else:
                # Strip audio before upload to prevent Seedance extend from copying input audio
                stripped = v.rsplit(".", 1)[0] + "-noaudio.mp4"
                print(f"  Stripping audio from {os.path.basename(v)} to prevent audio leak...", flush=True)
                subprocess.run(
                    ["ffmpeg", "-i", v, "-an", "-c:v", "copy", "-y", stripped],
                    capture_output=True, timeout=60
                )
                if os.path.exists(stripped) and os.path.getsize(stripped) > 0:
                    v = stripped
                else:
                    print(f"  ⚠️ Audio strip failed, using original", flush=True)
            v = upload_to_tmpfiles(v)
        cmd.extend(["--video", v])

    for img in (images or []):
        cmd.extend(["--image", img])

    env = os.environ.copy()
    env["ARK_API_KEY"] = ark_key
    env["PYTHONUNBUFFERED"] = "1"

    print(f"  Seedance: {os.path.basename(output)} (prompt: {prompt[:120]}...)", flush=True)
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    elapsed = time.time() - t0

    if result.returncode == 0 and os.path.exists(output):
        size_mb = os.path.getsize(output) / 1024 / 1024
        print(f"  ✓ {os.path.basename(output)} ({size_mb:.1f}MB, {elapsed:.0f}s)", flush=True)
        return {"ok": True, "path": output, "elapsed": elapsed}
    else:
        err = result.stderr[-500:] if result.stderr else "Unknown error"
        # Check content moderation
        if "content" in err.lower() and ("moderat" in err.lower() or "审核" in err or "block" in err.lower()):
            print(f"  ⛔ MODERATION BLOCK: {os.path.basename(output)}", flush=True)
            return {"ok": False, "path": output, "error": "MODERATION_BLOCK", "elapsed": elapsed}
        print(f"  ✗ {os.path.basename(output)}: {err[:200]}", flush=True)
        return {"ok": False, "path": output, "error": err[:500], "elapsed": elapsed}


def main():
    parser = argparse.ArgumentParser(description="Seedance 2.0 video generator (concurrent)")
    parser.add_argument("--prompt", help="Seedance prompt")
    parser.add_argument("--images", nargs="*", default=[], help="Reference images")
    parser.add_argument("--video", help="Input video for extension")
    parser.add_argument("--out", default="output.mp4", help="Output path")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--ratio", default="9:16")
    parser.add_argument("--batch", help="Batch JSON file for concurrent generation")
    parser.add_argument("--out-dir", help="Output directory for batch mode")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrent Seedance calls")
    parser.add_argument("--keep-audio", action="store_true", help="Keep input video audio (skip strip)")
    args = parser.parse_args()

    keys = load_keys()
    if not keys["ark_key"]:
        print("ERROR: ARK_API_KEY not found", file=sys.stderr)
        sys.exit(1)
    if not keys["seedance_script"]:
        print("ERROR: seedance.py not found", file=sys.stderr)
        sys.exit(1)

    if args.batch:
        with open(args.batch) as f:
            tasks = json.load(f)
        out_dir = args.out_dir or "output"
        os.makedirs(out_dir, exist_ok=True)

        print(f"Batch: {len(tasks)} tasks, concurrency={args.concurrency}", flush=True)
        results = []
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {}
            for t in tasks:
                out_path = os.path.join(out_dir, t["out"]) if not os.path.isabs(t["out"]) else t["out"]
                fut = pool.submit(
                    run_seedance, keys["seedance_script"], keys["ark_key"],
                    t["prompt"], t.get("images", []), t.get("video"),
                    out_path, t.get("duration", 15), t.get("ratio", "9:16"),
                    t.get("keep_audio", False)
                )
                futures[fut] = t.get("id", t.get("name", t["out"]))
            for fut in as_completed(futures):
                tid = futures[fut]
                r = fut.result()
                r["id"] = tid
                results.append(r)

        ok = sum(1 for r in results if r["ok"])
        print(f"\nBatch done: {ok}/{len(results)} succeeded", flush=True)

        log_path = os.path.join(out_dir, "seedance-batch-log.json")
        with open(log_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        sys.exit(0 if ok == len(results) else 1)

    elif args.prompt:
        r = run_seedance(
            keys["seedance_script"], keys["ark_key"],
            args.prompt, args.images, args.video,
            args.out, args.duration, args.ratio, args.keep_audio
        )
        sys.exit(0 if r["ok"] else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
