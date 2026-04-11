#!/usr/bin/env python3
"""
V7-AUDIO-001: Audio Continuity A/B Test
3 groups × 3 segments = 9 Seedance calls (but Seg1 shared → 7 unique calls)

Groups:
  A: Full audio strip before extend
  B: Keep last 3s audio before extend  
  C: No strip (baseline, raw audio passthrough)

All use same Genshin-style teahouse prompts from Controller spec.
"""

import json
import os
import subprocess
import sys
import time
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLS = Path.home() / "trinity-v7-consistency" / "tools"
EXPERIMENTS = Path.home() / "trinity-v7-consistency" / "experiments"
BASE = EXPERIMENTS / "exp-v7-audio-001"

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

KEYS = load_keys()

# ─── Prompts (from Controller spec) ───

PROMPTS = {
    "seg1": (
        "Genshin Impact anime style, vibrant colors, cel-shaded lighting. "
        "Interior of a traditional Chinese teahouse, warm wood tones, paper lanterns, "
        "steam rising from teacups. A young swordsman in flowing blue-and-white robes "
        "sits at a wooden table, drinking tea. He has black hair tied in a ponytail, "
        "a thin sword resting against the chair. The teahouse owner, a plump middle-aged "
        "man in brown apron, approaches with a teapot, smiling. Camera: medium shot, "
        "slight dolly in. The swordsman looks up and nods."
    ),
    "seg2": (
        "Continuation of previous scene. Same Genshin-style teahouse interior. "
        "The teahouse owner pours tea while leaning in conspiratorially. The swordsman "
        "raises an eyebrow with a slight smirk. Camera: medium close-up, alternating "
        "between the two characters. The owner gestures dramatically while talking, "
        "nearly spilling tea."
    ),
    "seg3": (
        "Continuation of previous scene. Same teahouse. The swordsman laughs and stands "
        "up, reaching for his sword. The owner waves his hands in mock panic. Camera "
        "pulls back to a wider shot showing the full teahouse interior. Light streams "
        "through the window. The swordsman puts coins on the table and walks toward the door."
    ),
}

# Verify prompt lengths
for k, v in PROMPTS.items():
    assert len(v) <= 800, f"{k} prompt too long: {len(v)} chars"

GROUPS = {
    "A": {"desc": "Full audio strip", "method": "full_strip"},
    "B": {"desc": "Keep last 3s audio", "method": "tail_3s"},
    "C": {"desc": "No strip (raw)", "method": "no_strip"},
}

def run_cmd(cmd, timeout=1800):
    """Run command with live output."""
    print(f"[CMD] {' '.join(cmd[:6])}...", flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        print(f"[ERR] {proc.stderr[-500:]}", flush=True)
    return proc

def get_duration(path):
    """Get video duration in seconds."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())

def strip_audio_full(input_path, output_path):
    """Remove all audio from video."""
    run_cmd(["ffmpeg", "-y", "-i", str(input_path), "-an", "-c:v", "copy", str(output_path)])

def strip_audio_tail(input_path, output_path, keep_seconds=3):
    """Mute all audio except the last N seconds."""
    dur = get_duration(input_path)
    cutpoint = max(0, dur - keep_seconds)
    run_cmd([
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", f"volume=enable='lt(t,{cutpoint})':volume=0",
        "-c:v", "copy", str(output_path)
    ])

def upload_to_tmpfiles(local_path):
    """Upload to tmpfiles.org, return direct download URL."""
    r = subprocess.run(
        ["curl", "-s", "-F", f"file=@{local_path}", "https://tmpfiles.org/api/v1/upload"],
        capture_output=True, text=True, timeout=120
    )
    data = json.loads(r.stdout)
    url = data["data"]["url"]
    return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")

def seedance_gen(prompt, out_path, video_url=None):
    """Call seedance_gen.py for one generation."""
    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--prompt", prompt,
        "--ratio", "9:16",
        "--duration", "15",
        "--out", str(out_path),
    ]
    if video_url:
        cmd.extend(["--video", video_url])
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        print(f"[SEEDANCE ERR] {proc.stderr[-500:]}", flush=True)
        return False
    return os.path.exists(out_path)

def prepare_extend_input(seg_path, group_method, out_dir):
    """Prepare video for extend based on group's audio strategy."""
    base = Path(seg_path).stem
    if group_method == "full_strip":
        prepared = out_dir / f"{base}-stripped.mp4"
        strip_audio_full(seg_path, prepared)
        return prepared
    elif group_method == "tail_3s":
        prepared = out_dir / f"{base}-tail3s.mp4"
        strip_audio_tail(seg_path, prepared, keep_seconds=3)
        return prepared
    else:  # no_strip
        return Path(seg_path)

def concat_segments(seg_paths, out_path):
    """Concatenate segments using ffmpeg."""
    list_file = out_path.parent / "concat_list.txt"
    with open(list_file, "w") as f:
        for p in seg_paths:
            f.write(f"file '{p}'\n")
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(out_path)
    ])
    list_file.unlink()
    return os.path.exists(out_path)

def check_audio(video_path):
    """Check if video has audio track and measure audio levels."""
    # Check audio stream exists
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(video_path)],
        capture_output=True, text=True
    )
    has_audio = bool(r.stdout.strip())
    
    # Measure mean volume
    r2 = subprocess.run(
        ["ffmpeg", "-i", str(video_path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True
    )
    mean_vol = None
    for line in r2.stderr.split("\n"):
        if "mean_volume" in line:
            try:
                mean_vol = float(line.split("mean_volume:")[1].strip().split()[0])
            except:
                pass
    return {"has_audio": has_audio, "mean_volume_db": mean_vol}

def measure_audio_correlation(seg1_path, seg2_path):
    """Measure audio similarity between end of seg1 and start of seg2."""
    # Extract last 2s of seg1 and first 2s of seg2 as raw PCM
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        a1 = os.path.join(td, "a1.raw")
        a2 = os.path.join(td, "a2.raw")
        dur1 = get_duration(seg1_path)
        
        subprocess.run([
            "ffmpeg", "-y", "-i", str(seg1_path),
            "-ss", str(max(0, dur1-2)), "-t", "2",
            "-f", "f32le", "-ac", "1", "-ar", "16000", a1
        ], capture_output=True)
        
        subprocess.run([
            "ffmpeg", "-y", "-i", str(seg2_path),
            "-t", "2",
            "-f", "f32le", "-ac", "1", "-ar", "16000", a2
        ], capture_output=True)
        
        try:
            import numpy as np
            d1 = np.fromfile(a1, dtype=np.float32)
            d2 = np.fromfile(a2, dtype=np.float32)
            if len(d1) == 0 or len(d2) == 0:
                return 0.0
            min_len = min(len(d1), len(d2))
            corr = float(np.abs(np.corrcoef(d1[:min_len], d2[:min_len])[0, 1]))
            return corr if not np.isnan(corr) else 0.0
        except:
            return 0.0

def main():
    os.makedirs(BASE, exist_ok=True)
    log = {"experiment": "V7-AUDIO-001", "groups": {}, "start_time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    
    # ─── Step 1: Generate Seg1 (shared across all groups) ───
    seg1_path = BASE / "seg1-shared.mp4"
    if not seg1_path.exists():
        print("[1/7] Generating shared Seg1 (text-to-video)...", flush=True)
        ok = seedance_gen(PROMPTS["seg1"], seg1_path)
        if not ok:
            print("[FATAL] Seg1 generation failed", flush=True)
            sys.exit(1)
    else:
        print("[1/7] Seg1 already exists, reusing.", flush=True)
    
    log["seg1_prompt"] = PROMPTS["seg1"]
    log["seg1_chars"] = len(PROMPTS["seg1"])
    
    # ─── Step 2: For each group, extend Seg2 and Seg3 ───
    for group_id, group_cfg in GROUPS.items():
        print(f"\n{'='*60}", flush=True)
        print(f"[GROUP {group_id}] {group_cfg['desc']}", flush=True)
        print(f"{'='*60}", flush=True)
        
        gdir = BASE / f"group-{group_id.lower()}"
        os.makedirs(gdir, exist_ok=True)
        
        group_log = {"desc": group_cfg["desc"], "method": group_cfg["method"], "segments": {}}
        
        # Copy seg1 to group dir
        seg1_group = gdir / "seg1.mp4"
        if not seg1_group.exists():
            shutil.copy2(seg1_path, seg1_group)
        
        # ─── Seg2 ───
        seg2_path = gdir / "seg2.mp4"
        if not seg2_path.exists():
            # Prepare extend input
            extend_input = prepare_extend_input(seg1_group, group_cfg["method"], gdir)
            upload_url = upload_to_tmpfiles(str(extend_input))
            print(f"[GROUP {group_id}] Seg1 uploaded: {upload_url}", flush=True)
            
            print(f"[GROUP {group_id}] Generating Seg2...", flush=True)
            t0 = time.time()
            ok = seedance_gen(PROMPTS["seg2"], seg2_path, video_url=upload_url)
            t1 = time.time()
            
            group_log["segments"]["seg2"] = {
                "prompt": PROMPTS["seg2"],
                "extend_input_method": group_cfg["method"],
                "upload_url": upload_url,
                "generation_time_s": round(t1 - t0, 1),
                "success": ok,
            }
            if not ok:
                print(f"[GROUP {group_id}] Seg2 FAILED, skipping group", flush=True)
                log["groups"][group_id] = group_log
                continue
        else:
            print(f"[GROUP {group_id}] Seg2 exists, reusing.", flush=True)
            group_log["segments"]["seg2"] = {"reused": True}
        
        # ─── Seg3 ───
        seg3_path = gdir / "seg3.mp4"
        if not seg3_path.exists():
            extend_input_2 = prepare_extend_input(seg2_path, group_cfg["method"], gdir)
            upload_url_2 = upload_to_tmpfiles(str(extend_input_2))
            print(f"[GROUP {group_id}] Seg2 uploaded: {upload_url_2}", flush=True)
            
            print(f"[GROUP {group_id}] Generating Seg3...", flush=True)
            t0 = time.time()
            ok = seedance_gen(PROMPTS["seg3"], seg3_path, video_url=upload_url_2)
            t1 = time.time()
            
            group_log["segments"]["seg3"] = {
                "prompt": PROMPTS["seg3"],
                "extend_input_method": group_cfg["method"],
                "upload_url": upload_url_2,
                "generation_time_s": round(t1 - t0, 1),
                "success": ok,
            }
            if not ok:
                print(f"[GROUP {group_id}] Seg3 FAILED", flush=True)
                log["groups"][group_id] = group_log
                continue
        else:
            print(f"[GROUP {group_id}] Seg3 exists, reusing.", flush=True)
            group_log["segments"]["seg3"] = {"reused": True}
        
        # ─── Concat ───
        final_path = gdir / f"final-group-{group_id.lower()}.mp4"
        print(f"[GROUP {group_id}] Concatenating...", flush=True)
        concat_segments([seg1_group, seg2_path, seg3_path], final_path)
        
        # ─── Audio checks ───
        print(f"[GROUP {group_id}] Audio checks...", flush=True)
        for seg_name, seg_p in [("seg1", seg1_group), ("seg2", seg2_path), ("seg3", seg3_path)]:
            aud = check_audio(seg_p)
            group_log["segments"].setdefault(seg_name, {})
            group_log["segments"][seg_name]["audio_check"] = aud
            if not aud["has_audio"]:
                print(f"[WARN] {seg_name} has NO audio!", flush=True)
        
        # Audio correlation (repeat detection)
        corr_12 = measure_audio_correlation(seg1_group, seg2_path)
        corr_23 = measure_audio_correlation(seg2_path, seg3_path)
        group_log["audio_correlation"] = {"seg1_seg2": round(corr_12, 4), "seg2_seg3": round(corr_23, 4)}
        print(f"[GROUP {group_id}] Audio corr: seg1→2={corr_12:.4f}, seg2→3={corr_23:.4f}", flush=True)
        
        # Final audio check
        final_aud = check_audio(final_path)
        group_log["final"] = {
            "path": str(final_path),
            "size_mb": round(os.path.getsize(final_path) / 1024 / 1024, 1) if os.path.exists(final_path) else 0,
            "audio_check": final_aud,
        }
        
        log["groups"][group_id] = group_log
        print(f"[GROUP {group_id}] Done! Final: {final_path}", flush=True)
    
    # ─── Save log ───
    log["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    log_path = BASE / "generation-log.json"
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n[DONE] Log saved to {log_path}", flush=True)
    
    # ─── Summary ───
    print("\n" + "="*60, flush=True)
    print("SUMMARY", flush=True)
    print("="*60, flush=True)
    for gid, gl in log["groups"].items():
        corr = gl.get("audio_correlation", {})
        final = gl.get("final", {})
        print(f"Group {gid} ({gl['desc']}): corr12={corr.get('seg1_seg2','N/A')}, corr23={corr.get('seg2_seg3','N/A')}, size={final.get('size_mb','N/A')}MB", flush=True)

if __name__ == "__main__":
    main()
