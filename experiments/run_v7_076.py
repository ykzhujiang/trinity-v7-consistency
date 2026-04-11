#!/usr/bin/env python3 -u
"""V7-076: High complexity — dual character + object interaction (tavern gift scene)
Text-to-video Seg1 + extend Seg2/Seg3, audio strip, Genshin style.
Seg1 assumed already generating externally.
"""
import os, sys, subprocess, json, time, numpy as np
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"

EXP_DIR = Path(__file__).parent / "exp-v7-076"
OUT_DIR = EXP_DIR / "output"
TOOLS = Path(__file__).parent.parent / "tools"
PROMPTS_FILE = EXP_DIR / "prompts.json"

with open(PROMPTS_FILE) as f:
    prompts_data = json.load(f)

PROMPTS = {k: prompts_data[k]["prompt"] for k in ["seg1", "seg2", "seg3"]}

def run_cmd(cmd, timeout=1800):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)

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
    print(f"=== V7-076: High Complexity Dual Character ===", flush=True)
    print(f"Start: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    results = {
        "experiment_id": "V7-076",
        "desc": "High complexity — dual character + object interaction (tavern gift)",
        "style": "Genshin Impact anime, cel-shaded 3D",
        "strip_audio": True,
        "segments": {},
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    }
    
    seg1_path = str(OUT_DIR / "seg1.mp4")
    
    # Wait for seg1
    print("Waiting for seg1.mp4...", flush=True)
    waited = 0
    while not os.path.exists(seg1_path) or os.path.getsize(seg1_path) < 100000:
        time.sleep(10)
        waited += 10
        if waited > 600:
            print("✗ Seg1 timeout", flush=True)
            results["status"] = "FAILED"
            results["error"] = "Seg1 timeout"
            with open(EXP_DIR / "results.json", "w") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return
        if waited % 60 == 0:
            print(f"  Still waiting... ({waited}s)", flush=True)
    
    time.sleep(5)
    print(f"✓ Seg1 ready ({os.path.getsize(seg1_path)/1024/1024:.1f}MB)", flush=True)
    results["segments"]["seg1"] = {"status": "OK"}
    
    seg_paths = {"seg1": seg1_path}
    
    for seg_num in [2, 3]:
        seg_key = f"seg{seg_num}"
        prev_key = f"seg{seg_num-1}"
        prev_path = seg_paths[prev_key]
        seg_path = str(OUT_DIR / f"{seg_key}.mp4")
        
        stripped = prev_path.replace(".mp4", "-noaudio.mp4")
        subprocess.run(["ffmpeg", "-i", prev_path, "-an", "-c:v", "copy", "-y", stripped],
                      capture_output=True, timeout=60)
        video_input = stripped if os.path.exists(stripped) and os.path.getsize(stripped) > 0 else prev_path
        
        cmd = ["python3", "-u", str(TOOLS / "seedance_gen.py"),
               "--prompt", PROMPTS[seg_key], "--video", video_input,
               "--out", seg_path, "--duration", "15", "--ratio", "9:16"]
        
        print(f"\n[V7-076] {seg_key}: extend...", flush=True)
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
    print(f"\n[V7-076] Concatenating...", flush=True)
    run_cmd(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
             "--inputs", seg_paths["seg1"], seg_paths["seg2"], seg_paths["seg3"],
             "--out", final_path, "--check-audio", "--check-per-segment"], timeout=120)
    
    if not os.path.exists(final_path):
        results["status"] = "CONCAT_FAILED"
        with open(EXP_DIR / "results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return
    
    # Audio analysis
    wav_paths = []
    for i in [1, 2, 3]:
        wav_path = str(OUT_DIR / f"seg{i}.wav")
        subprocess.run(["ffmpeg", "-i", str(OUT_DIR / f"seg{i}.mp4"),
                       "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", wav_path],
                      capture_output=True, timeout=60)
        wav_paths.append(wav_path)
    
    corr = audio_correlation(wav_paths)
    max_r = max(corr.values()) if corr else 0.0
    results["audio_correlation"] = corr
    results["max_audio_r"] = max_r
    results["audio_verdict"] = "PASS" if max_r < 0.3 else ("BORDERLINE" if max_r < 0.6 else "FAIL")
    
    size_mb = os.path.getsize(final_path) / 1024 / 1024
    results["status"] = "COMPLETE"
    results["final_path"] = final_path
    results["final_size_mb"] = round(size_mb, 1)
    results["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    with open(EXP_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Delivery notice
    delivery_path = os.path.expanduser("~/.openclaw-trinity-v3/workspace-operator/shared/human/from-operator/cycle-924-v7-076-delivery.md")
    with open(delivery_path, "w") as f:
        f.write(f"""# 视频交付：V7-076 — 高复杂度双人物体交互 (酒馆赠礼)

**Agent**: Operator
**Cycle**: CYCLE-operator-924
**Experiment**: V7-076

## 视频信息
- **路径**: {final_path}
- **时长**: ~45s (3 Segments × 15s)
- **大小**: {size_mb:.1f}MB
- **音频检查**: max_r={max_r:.4f} → {results['audio_verdict']}

## 实验设计
**变量**: 高复杂度 — 双人物+物体交互（酒馆中推盒→开盒发光→对视碰杯）
**画风**: Genshin Impact / 原神风格 cel-shaded 3D
**音频剥离**: ON

## 请朱江 review
重点关注：双人物一致性、空间关系稳定性、物体交互、表情变化
""")
    
    print(f"\n✓ V7-076 COMPLETE: {final_path} ({size_mb:.1f}MB)", flush=True)
    print(f"  Audio: max_r={max_r:.4f} → {results['audio_verdict']}", flush=True)

if __name__ == "__main__":
    main()
