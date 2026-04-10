#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.28.0",
# ]
# ///
"""
Concurrent Seedance Runner — submit multiple Seedance jobs in parallel.

Usage:
    from concurrent_seedance import SeedanceJob, run_concurrent

    jobs = [
        SeedanceJob(name="anime-seg1", prompt="...", images=[...], output="anime/seg1.mp4"),
        SeedanceJob(name="realistic-seg1", prompt="...", images=[], output="realistic/seg1.mp4"),
    ]
    results = run_concurrent(jobs, ark_key="...", seedance_script="...", max_workers=2)
"""

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SeedanceJob:
    """A single Seedance generation job."""
    name: str
    prompt: str
    output: str
    images: list[str] = field(default_factory=list)
    input_video: Optional[str] = None
    duration: int = 15
    ratio: str = "9:16"


@dataclass
class SeedanceResult:
    """Result of a Seedance job."""
    name: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    moderation_blocked: bool = False
    elapsed_seconds: float = 0


def upload_to_tmpfiles(local_path: str) -> str:
    """Upload a local file to tmpfiles.org and return direct download URL."""
    import requests
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    page_url = resp.json()["data"]["url"]
    return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")


def _run_single(job: SeedanceJob, ark_key: str, seedance_script: str) -> SeedanceResult:
    """Execute a single Seedance job (designed to run in a thread)."""
    start = time.time()
    print(f"[{job.name}] Starting... (prompt: {len(job.prompt)} chars, images: {len(job.images)})")

    cmd = [
        "python3", seedance_script, "run",
        "--prompt", job.prompt,
        "--ratio", job.ratio,
        "--duration", str(job.duration),
        "--out", job.output,
    ]

    # Upload and attach video ref
    if job.input_video:
        video_url = job.input_video
        if os.path.isfile(video_url) and not video_url.startswith("http"):
            try:
                video_url = upload_to_tmpfiles(video_url)
            except Exception as e:
                return SeedanceResult(job.name, False, error=f"Video upload failed: {e}",
                                      elapsed_seconds=time.time() - start)
        cmd.extend(["--video", video_url])

    # Upload and attach images
    for img_path in job.images:
        if os.path.isfile(img_path) and not img_path.startswith("http"):
            try:
                img_path = upload_to_tmpfiles(img_path)
            except Exception as e:
                return SeedanceResult(job.name, False, error=f"Image upload failed: {e}",
                                      elapsed_seconds=time.time() - start)
        cmd.extend(["--image", img_path])

    env = os.environ.copy()
    env["ARK_API_KEY"] = ark_key

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    except subprocess.TimeoutExpired:
        return SeedanceResult(job.name, False, error="Timeout (1800s)",
                              elapsed_seconds=time.time() - start)

    elapsed = time.time() - start

    if result.returncode != 0:
        stderr = result.stderr
        if any(kw in stderr for kw in ["内容审核", "content moderation", "审核", "blocked"]):
            print(f"[{job.name}] ⛔ MODERATION BLOCKED ({elapsed:.0f}s)")
            return SeedanceResult(job.name, False, error="Moderation blocked",
                                  moderation_blocked=True, elapsed_seconds=elapsed)
        print(f"[{job.name}] ✗ Failed ({elapsed:.0f}s): {stderr[:200]}")
        return SeedanceResult(job.name, False, error=stderr[:500], elapsed_seconds=elapsed)

    print(f"[{job.name}] ✓ Done ({elapsed:.0f}s) → {job.output}")
    return SeedanceResult(job.name, True, output=job.output, elapsed_seconds=elapsed)


def run_concurrent(
    jobs: list[SeedanceJob],
    ark_key: str,
    seedance_script: str,
    max_workers: int = 2,
) -> dict[str, SeedanceResult]:
    """
    Run multiple Seedance jobs concurrently.
    
    Returns dict mapping job.name → SeedanceResult.
    """
    os.makedirs(os.path.dirname(jobs[0].output) if jobs else ".", exist_ok=True)
    for job in jobs:
        os.makedirs(os.path.dirname(job.output), exist_ok=True)

    results = {}
    print(f"\n{'='*60}")
    print(f"Concurrent Seedance: {len(jobs)} jobs, max_workers={max_workers}")
    print(f"{'='*60}")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_run_single, job, ark_key, seedance_script): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = SeedanceResult(job.name, False, error=str(e))
            results[result.name] = result

    # Summary
    print(f"\n--- Concurrent Results ---")
    for name, r in results.items():
        status = "✓" if r.success else ("⛔ MOD" if r.moderation_blocked else "✗")
        print(f"  {status} {name}: {r.elapsed_seconds:.0f}s")

    return results
