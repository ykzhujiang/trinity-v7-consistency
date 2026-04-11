#!/usr/bin/env python3 -u
"""V7-075: Medium complexity — single character + object interaction (book/letter)
Text-to-video Seg1 + extend Seg2/Seg3, audio strip, Genshin style.
Seg1 assumed already generating externally — this script waits for it, then continues.
"""
import os, sys, subprocess, json, time, numpy as np
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"

EXP_DIR = Path(__file__).parent / "exp-v7-075"
OUT_DIR = EXP_DIR / "output"
TOOLS = Path(__file__).parent.parent / "tools"
PROMPTS_FILE = EXP_DIR / "prompts.json"

with open(PROMPTS_FILE) as f:
    prompts_data = json.load(f)

PROMPTS = {k: prompts_data[k]["prompt"] for k in ["seg1", "seg2", "seg3"]}

def run_cmd(cmd, timeout=1800):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    return r

def audio_correlation(wav_paths):
    wavs = []
    for p in wav_paths:
        if os.path.exists(p):
            data = np.fromfile(p, dtype=np.int16)[22:]
            wavs.append(data.astype(float))
        else:
            wavs.append(None)
    results = {}
    for a in range(len(wavs)):
        for b in range(a+1, len(wavs)):
            if wavs[a] is not None and wavs[b] is not None:
                mn = min(len(wavs[a]), len(wavs[b]))
                if mn > 0:
                    r = float(np.corrcoef(wavs[a][:mn], wavs[b][:mn])[0, 1])
                else:
                    r = 0.0
                results[f"seg{a+1}_seg{b+1}"] = round(r, 4)
    return results

def main():
    print(f"=== V7-075: Medium Complexity Object Interaction ===", flush=True)
    print(f"Start: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    results = {
        "experiment_id": "V7-075",
        "desc": "Medium complexity — single character + book/letter object interaction",
        "style": "Genshin Impact anime, cel-shaded 3D",
        "strip_audio": True,
        "segments": {},
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    }
    
    seg1_path = str(OUT_DIR / "seg1.mp4")
    
    # Wait for seg1 (generated externally)
    print("Waiting for seg1.mp4...", flush=True)
    waited = 0
    while not os.path.exists(seg1_path) or os.path.getsize(seg1_path) < 100000:
        time.sleep(10)
        waited += 10
        if waited > 600:
            print("✗ Seg1 timeout after 600s", flush=True)
            results["status"] = "FAILED"
            results["error"] = "Seg1 generation timeout"
            with open(EXP_DIR / "results.json", "w") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return
        if waited % 60 == 0:
            print(f"  Still waiting... ({waited}s)", flush=True)
    
    # Small extra wait to ensure file is fully written
    time.sleep(5)
    print(f"✓ Seg1 ready ({os.path.getsize(seg1_path)/1024/1024:.1f}MB)", flush=True)
    results["segments"]["seg1"] = {"status": "OK"}
    
    seg_paths = {"seg1": seg1_path}
    
    # Seg2 & Seg3: extend
    for seg_num in [2, 3]:
        seg_key = f"seg{seg_num}"
        prev_key = f"seg{seg_num-1}"
        prev_path = seg_paths[prev_key]
        seg_path = str(OUT_DIR / f"{seg_key}.mp4")
        
        # Audio strip
        stripped = prev_path.replace(".mp4", "-noaudio.mp4")
        subprocess.run(
            ["ffmpeg", "-i", prev_path, "-an", "-c:v", "copy", "-y", stripped],
            capture_output=True, timeout=60
        )
        video_input = stripped if os.path.exists(stripped) and os.path.getsize(stripped) > 0 else prev_path
        
        cmd = [
            "python3", "-u", str(TOOLS / "seedance_gen.py"),
            "--prompt", PROMPTS[seg_key],
            "--video", video_input,
            "--out", seg_path,
            "--duration", "15",
            "--ratio", "9:16",
        ]
        
        print(f"\n[V7-075] {seg_key}: extend from {prev_key}...", flush=True)
        t0 = time.time()
        r = run_cmd(cmd, timeout=1800)
        elapsed = time.time() - t0
        
        if r.returncode != 0 or not os.path.exists(seg_path):
            err = r.stderr[-300:] if r.stderr else "unknown"
            print(f"  ✗ {seg_key} FAILED: {err[:200]}", flush=True)
            if "moderat" in err.lower() or "审核" in err or "block" in err.lower():
                results["status"] = "MODERATION_BLOCK"
                results["error"] = f"{seg_key} moderation block — abandoned"
                with open(EXP_DIR / "results.json", "w") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                return
            # Retry once
            print(f"  Retrying {seg_key}...", flush=True)
            t0 = time.time()
            r = run_cmd(cmd, timeout=1800)
            elapsed = time.time() - t0
            if r.returncode != 0 or not os.path.exists(seg_path):
                results["status"] = "FAILED"
                results["error"] = f"{seg_key} failed after retry"
                with open(EXP_DIR / "results.json", "w") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                return
        
        seg_paths[seg_key] = seg_path
        results["segments"][seg_key] = {"elapsed": round(elapsed, 1), "status": "OK"}
        print(f"  ✓ {seg_key} done ({elapsed:.0f}s)", flush=True)
    
    # Concat
    final_path = str(OUT_DIR / "final.mp4")
    print(f"\n[V7-075] Concatenating...", flush=True)
    r = run_cmd([
        "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
        "--inputs", seg_paths["seg1"], seg_paths["seg2"], seg_paths["seg3"],
        "--out", final_path,
        "--check-audio", "--check-per-segment"
    ], timeout=120)
    
    if not os.path.exists(final_path):
        results["status"] = "CONCAT_FAILED"
        with open(EXP_DIR / "results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return
    
    # Audio analysis
    print(f"\n[V7-075] Audio correlation analysis...", flush=True)
    wav_paths = []
    for i in [1, 2, 3]:
        wav_path = str(OUT_DIR / f"seg{i}.wav")
        subprocess.run([
            "ffmpeg", "-i", str(OUT_DIR / f"seg{i}.mp4"),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            "-y", wav_path
        ], capture_output=True, timeout=60)
        wav_paths.append(wav_path)
    
    corr = audio_correlation(wav_paths)
    max_r = max(corr.values()) if corr else 0.0
    results["audio_correlation"] = corr
    results["max_audio_r"] = max_r
    results["audio_verdict"] = "PASS" if max_r < 0.3 else ("BORDERLINE" if max_r < 0.6 else "FAIL")
    
    # Audio check per segment
    audio_check = {}
    for i in [1, 2, 3]:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
             "-of", "csv=p=0", str(OUT_DIR / f"seg{i}.mp4")],
            capture_output=True, text=True, timeout=30
        )
        audio_check[f"seg{i}"] = "audio" in probe.stdout
    results["audio_per_segment"] = audio_check
    
    # Final audio check
    final_check = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final_path],
        capture_output=True, text=True, timeout=30
    )
    
    size_mb = os.path.getsize(final_path) / 1024 / 1024
    results["status"] = "COMPLETE"
    results["final_path"] = final_path
    results["final_size_mb"] = round(size_mb, 1)
    results["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    with open(EXP_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Write delivery notice
    delivery_path = os.path.expanduser("~/.openclaw-trinity-v3/workspace-operator/shared/human/from-operator/cycle-924-v7-075-delivery.md")
    with open(delivery_path, "w") as f:
        f.write(f"""# 视频交付：V7-075 — 中复杂度物体交互 (书房密信)

**Agent**: Operator
**Cycle**: CYCLE-operator-924
**Experiment**: V7-075

## 视频信息
- **路径**: {final_path}
- **时长**: ~45s (3 Segments × 15s)
- **大小**: {size_mb:.1f}MB
- **音频检查**: max_r={max_r:.4f} → {results['audio_verdict']}

## 实验设计
**变量**: 中复杂度 — 单人物+物体交互（书房中发现古书→密信掉落→展信震惊）
**画风**: Genshin Impact / 原神风格 cel-shaded 3D
**音频剥离**: ON

## 请朱江 review
重点关注：物体交互自然度（翻书、信纸掉落）、角色一致性、场景一致性
""")
    
    print(f"\n✓ V7-075 COMPLETE: {final_path} ({size_mb:.1f}MB)", flush=True)
    print(f"  Audio: max_r={max_r:.4f} → {results['audio_verdict']}", flush=True)
    print(f"  Delivery notice written.", flush=True)

if __name__ == "__main__":
    main()
