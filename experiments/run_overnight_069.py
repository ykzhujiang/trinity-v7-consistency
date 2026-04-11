#!/usr/bin/env python3
"""
Overnight Experiment V7-069~074: Best Practice Exploration
Text-to-video + extend, 3-Segment, Genshin baseline style

Test matrix:
- V7-069: Genshin, same-scene, with audio strip (BASELINE)
- V7-070: Genshin, same-scene, WITHOUT audio strip (control)
- V7-071: Genshin, same-scene, minimal seg2/3 prompt (~200 chars, V7-051 style)
- V7-072: Genshin, same-scene, NO character re-description in seg2/3
- V7-073: Genshin, diff-scene (3-act), with audio strip
- V7-074: RPG/UE5, same-scene, with audio strip (style comparison)

All: 9:16, 15s per seg, Chinese dialogue, text-to-video seg1, extend seg2/3
"""

import json
import os
import subprocess
import sys
import time
import numpy as np
from pathlib import Path

TOOLS = Path.home() / "trinity-v7-consistency" / "tools"
EXPERIMENTS = Path.home() / "trinity-v7-consistency" / "experiments"

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

KEYS = load_keys()

# ─── Prompt templates ───

GENSHIN_STYLE = "Gacha mobile game style, Genshin Impact aesthetic, anime character design, soft glow, vivid color palette, detailed background art."
RPG_STYLE = "RPG game cinematic cutscene, Unreal Engine 5 render, dramatic cinematic lighting, game CG quality, detailed environment."

CHAR_FULL = "A 22-year-old Chinese male college student with messy black hair, wearing a faded blue hoodie and jeans, slim build, tired eyes"
CHAR_SHORT = "the young man in blue hoodie"

SCENE_ROOM = "Interior of a cramped 8-square-meter dorm room, single bed with messy blankets, small desk cluttered with textbooks and energy drink cans, blue-white LED desk lamp, rain hitting the window"
SCENE_CAFE = "Interior of a quiet late-night campus café, warm orange pendant lights, wooden tables, steaming coffee cups, soft jazz playing"
SCENE_ROOFTOP = "Exterior rooftop of a university building at dawn, city skyline in distance, wind blowing, golden hour light breaking through clouds"

EXPERIMENTS_DEF = {
    "V7-069": {
        "desc": "Genshin same-scene, audio strip ON (baseline)",
        "style": GENSHIN_STYLE,
        "strip_audio": True,
        "seg1": {
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits hunched at the desk staring at a rejection email on the laptop screen, slowly clenches his fists, mutters",
            "dialogue": '"又失败了……第八次了。" He rubs his eyes, pushes back from the desk.',
        },
        "seg2": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} stands up abruptly, knocking the chair back, grabs his phone from the desk, paces the tiny room",
            "dialogue": '"不行，我不能这样下去。" He stops at the window, looks out at the rain, takes a deep breath.',
        },
        "seg3": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits back down with determination, opens a new browser tab, starts typing rapidly with both hands",
            "dialogue": '"从头来。这次一定行。" A faint smile appears on his face as code fills the screen.',
        },
    },
    "V7-070": {
        "desc": "Genshin same-scene, audio strip OFF (control)",
        "style": GENSHIN_STYLE,
        "strip_audio": False,
        "seg1": {  # same as V7-069
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits hunched at the desk staring at a rejection email on the laptop screen, slowly clenches his fists, mutters",
            "dialogue": '"又失败了……第八次了。" He rubs his eyes, pushes back from the desk.',
        },
        "seg2": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} stands up abruptly, knocking the chair back, grabs his phone from the desk, paces the tiny room",
            "dialogue": '"不行，我不能这样下去。" He stops at the window, looks out at the rain, takes a deep breath.',
        },
        "seg3": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits back down with determination, opens a new browser tab, starts typing rapidly with both hands",
            "dialogue": '"从头来。这次一定行。" A faint smile appears on his face as code fills the screen.',
        },
    },
    "V7-071": {
        "desc": "Genshin same-scene, MINIMAL seg2/3 prompt (~200 chars)",
        "style": GENSHIN_STYLE,
        "strip_audio": True,
        "seg1": {
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits hunched at the desk staring at a rejection email on the laptop screen, slowly clenches his fists, mutters",
            "dialogue": '"又失败了……第八次了。" He rubs his eyes, pushes back from the desk.',
        },
        "seg2": {
            "prompt_override": f'Continuation of previous scene. {CHAR_SHORT} stands up, knocks the chair back, grabs phone, paces the room. "不行，我不能这样下去。" Stops at window, looks at rain, deep breath.',
        },
        "seg3": {
            "prompt_override": f'Continuation of previous scene. {CHAR_SHORT} sits back down, opens laptop, types rapidly. "从头来。这次一定行。" Faint smile, code fills screen.',
        },
    },
    "V7-072": {
        "desc": "Genshin same-scene, NO character re-description in seg2/3",
        "style": GENSHIN_STYLE,
        "strip_audio": True,
        "seg1": {
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits hunched at the desk staring at a rejection email on the laptop screen, slowly clenches his fists, mutters",
            "dialogue": '"又失败了……第八次了。" He rubs his eyes, pushes back from the desk.',
        },
        "seg2": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOM,
            "action": "He stands up abruptly, knocking the chair back, grabs his phone from the desk, paces the tiny room",
            "dialogue": '"不行，我不能这样下去。" He stops at the window, looks out at the rain, takes a deep breath.',
        },
        "seg3": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOM,
            "action": "He sits back down with determination, opens a new browser tab, starts typing rapidly with both hands",
            "dialogue": '"从头来。这次一定行。" A faint smile appears on his face as code fills the screen.',
        },
    },
    "V7-073": {
        "desc": "Genshin diff-scene 3-act, audio strip ON",
        "style": GENSHIN_STYLE,
        "strip_audio": True,
        "seg1": {
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits at the desk, stares at rejection email, slams laptop shut in frustration",
            "dialogue": '"又失败了……" He grabs his jacket and storms out of the room.',
        },
        "seg2": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_CAFE,
            "action": f"{CHAR_FULL} sits alone at a corner table, stirring coffee absently, staring at the rain outside the window",
            "dialogue": '"到底哪里出了问题？" He pulls out his phone, scrolls through job listings, sighs deeply.',
        },
        "seg3": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOFTOP,
            "action": f"{CHAR_FULL} stands at the rooftop railing, wind blowing his hair, golden dawn light on his face, he spreads his arms",
            "dialogue": '"管他的，再来一次。" He smiles, turns around and walks toward the stairwell with purpose.',
        },
    },
    "V7-074": {
        "desc": "RPG/UE5 same-scene, audio strip ON (style comparison)",
        "style": RPG_STYLE,
        "strip_audio": True,
        "seg1": {
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits hunched at the desk staring at a rejection email on the laptop screen, slowly clenches his fists, mutters",
            "dialogue": '"又失败了……第八次了。" He rubs his eyes, pushes back from the desk.',
        },
        "seg2": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} stands up abruptly, knocking the chair back, grabs his phone from the desk, paces the tiny room",
            "dialogue": '"不行，我不能这样下去。" He stops at the window, looks out at the rain, takes a deep breath.',
        },
        "seg3": {
            "prefix": "Continuation of previous scene.",
            "scene": SCENE_ROOM,
            "action": f"{CHAR_FULL} sits back down with determination, opens a new browser tab, starts typing rapidly with both hands",
            "dialogue": '"从头来。这次一定行。" A faint smile appears on his face as code fills the screen.',
        },
    },
}


def build_prompt(style, seg_def):
    """Build a full prompt from segment definition."""
    if "prompt_override" in seg_def:
        return seg_def["prompt_override"]
    
    parts = []
    if "prefix" in seg_def:
        parts.append(seg_def["prefix"])
    parts.append(style)
    if "scene" in seg_def:
        parts.append(seg_def["scene"])
    if "action" in seg_def:
        parts.append(seg_def["action"])
    if "dialogue" in seg_def:
        parts.append(seg_def["dialogue"])
    
    prompt = " ".join(parts)
    # Enforce ≤800 char limit
    if len(prompt) > 800:
        prompt = prompt[:797] + "..."
    return prompt


def audio_correlation(wav_paths):
    """Compute pairwise audio correlation."""
    wavs = []
    for p in wav_paths:
        if os.path.exists(p):
            data = np.fromfile(p, dtype=np.int16)[22:]  # skip wav header
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


def run_experiment(exp_id, exp_def):
    """Run a single 3-segment experiment."""
    exp_dir = EXPERIMENTS / f"exp-{exp_id.lower()}"
    out_dir = exp_dir / "output"
    os.makedirs(out_dir, exist_ok=True)
    
    style = exp_def["style"]
    strip = exp_def.get("strip_audio", True)
    
    # Build prompts
    prompts = {}
    for seg_key in ["seg1", "seg2", "seg3"]:
        prompts[seg_key] = build_prompt(style, exp_def[seg_key])
    
    # Save prompts
    with open(exp_dir / "prompts.json", "w") as f:
        json.dump({k: {"prompt": v, "chars": len(v)} for k, v in prompts.items()}, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}", flush=True)
    print(f"EXPERIMENT {exp_id}: {exp_def['desc']}", flush=True)
    print(f"Audio strip: {strip}", flush=True)
    for k, v in prompts.items():
        print(f"  {k}: {len(v)} chars", flush=True)
    print(f"{'='*60}", flush=True)
    
    results = {
        "experiment_id": exp_id,
        "desc": exp_def["desc"],
        "style": style[:50],
        "strip_audio": strip,
        "segments": {},
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    }
    
    seg_paths = {}
    
    # === SEG1: text-to-video ===
    seg1_path = str(out_dir / "seg1.mp4")
    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--prompt", prompts["seg1"],
        "--out", seg1_path,
        "--duration", "15",
        "--ratio", "9:16",
    ]
    env = os.environ.copy()
    env["ARK_API_KEY"] = KEYS["ark_key"]
    env["PYTHONUNBUFFERED"] = "1"
    
    print(f"\n[{exp_id}] Seg1: text-to-video...", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    elapsed = time.time() - t0
    
    if r.returncode != 0 or not os.path.exists(seg1_path):
        err = r.stderr[-300:] if r.stderr else "unknown"
        print(f"  ✗ Seg1 FAILED: {err[:200]}", flush=True)
        if "moderat" in err.lower() or "审核" in err or "block" in err.lower():
            results["status"] = "MODERATION_BLOCK"
            results["error"] = "Seg1 content moderation block"
        else:
            results["status"] = "FAILED"
            results["error"] = err[:300]
        with open(exp_dir / "results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return results
    
    seg_paths["seg1"] = seg1_path
    results["segments"]["seg1"] = {"elapsed": round(elapsed, 1), "status": "OK"}
    print(f"  ✓ Seg1 done ({elapsed:.0f}s)", flush=True)
    
    # === SEG2 & SEG3: extend ===
    for seg_num in [2, 3]:
        seg_key = f"seg{seg_num}"
        prev_key = f"seg{seg_num-1}"
        prev_path = seg_paths[prev_key]
        seg_path = str(out_dir / f"{seg_key}.mp4")
        
        # Audio strip if needed
        video_input = prev_path
        if strip:
            stripped = prev_path.replace(".mp4", "-noaudio.mp4")
            subprocess.run(
                ["ffmpeg", "-i", prev_path, "-an", "-c:v", "copy", "-y", stripped],
                capture_output=True, timeout=60
            )
            if os.path.exists(stripped) and os.path.getsize(stripped) > 0:
                video_input = stripped
        
        cmd = [
            "python3", "-u", str(TOOLS / "seedance_gen.py"),
            "--prompt", prompts[seg_key],
            "--video", video_input,
            "--out", seg_path,
            "--duration", "15",
            "--ratio", "9:16",
        ]
        
        print(f"\n[{exp_id}] {seg_key}: extend from {prev_key} (strip={strip})...", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
        elapsed = time.time() - t0
        
        if r.returncode != 0 or not os.path.exists(seg_path):
            err = r.stderr[-300:] if r.stderr else "unknown"
            print(f"  ✗ {seg_key} FAILED: {err[:200]}", flush=True)
            if "moderat" in err.lower() or "审核" in err or "block" in err.lower():
                results["status"] = "MODERATION_BLOCK"
                results["error"] = f"{seg_key} moderation block — abandoning per standing order"
                with open(exp_dir / "results.json", "w") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                return results
            # Retry once
            print(f"  Retrying {seg_key}...", flush=True)
            t0 = time.time()
            r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
            elapsed = time.time() - t0
            if r.returncode != 0 or not os.path.exists(seg_path):
                results["status"] = "FAILED"
                results["error"] = f"{seg_key} failed after retry"
                with open(exp_dir / "results.json", "w") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                return results
        
        seg_paths[seg_key] = seg_path
        results["segments"][seg_key] = {"elapsed": round(elapsed, 1), "status": "OK"}
        print(f"  ✓ {seg_key} done ({elapsed:.0f}s)", flush=True)
    
    # === CONCAT ===
    final_path = str(out_dir / "final.mp4")
    print(f"\n[{exp_id}] Concatenating...", flush=True)
    r = subprocess.run([
        "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
        "--inputs", seg_paths["seg1"], seg_paths["seg2"], seg_paths["seg3"],
        "--out", final_path,
        "--check-audio", "--check-per-segment"
    ], capture_output=True, text=True, timeout=120)
    
    if not os.path.exists(final_path):
        results["status"] = "CONCAT_FAILED"
        with open(exp_dir / "results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return results
    
    # === AUDIO ANALYSIS ===
    print(f"\n[{exp_id}] Audio correlation analysis...", flush=True)
    wav_paths = []
    for i in [1, 2, 3]:
        wav_path = str(out_dir / f"seg{i}.wav")
        subprocess.run([
            "ffmpeg", "-i", str(out_dir / f"seg{i}.mp4"),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            "-y", wav_path
        ], capture_output=True, timeout=60)
        wav_paths.append(wav_path)
    
    corr = audio_correlation(wav_paths)
    max_r = max(corr.values()) if corr else 0.0
    results["audio_correlation"] = corr
    results["max_audio_r"] = max_r
    results["audio_verdict"] = "PASS" if max_r < 0.3 else ("BORDERLINE" if max_r < 0.6 else "FAIL")
    
    print(f"  Audio correlation: {corr}", flush=True)
    print(f"  Max r: {max_r:.4f} → {results['audio_verdict']}", flush=True)
    
    # Final
    size_mb = os.path.getsize(final_path) / 1024 / 1024
    results["status"] = "COMPLETE"
    results["final_path"] = final_path
    results["final_size_mb"] = round(size_mb, 1)
    results["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    with open(exp_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ {exp_id} COMPLETE: {final_path} ({size_mb:.1f}MB)", flush=True)
    return results


def main():
    print(f"Overnight Experiment Batch: V7-069~074", flush=True)
    print(f"Start: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    all_results = []
    
    for exp_id, exp_def in EXPERIMENTS_DEF.items():
        try:
            r = run_experiment(exp_id, exp_def)
            all_results.append(r)
            
            # If moderation block, skip per standing order
            if r.get("status") == "MODERATION_BLOCK":
                print(f"\n⛔ {exp_id}: Moderation block. Skipping per standing order.", flush=True)
                continue
                
        except Exception as e:
            print(f"\n✗ {exp_id} EXCEPTION: {e}", flush=True)
            all_results.append({"experiment_id": exp_id, "status": "EXCEPTION", "error": str(e)})
    
    # Summary
    print(f"\n{'='*60}", flush=True)
    print(f"OVERNIGHT BATCH SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    
    for r in all_results:
        eid = r.get("experiment_id", "?")
        status = r.get("status", "?")
        audio = r.get("audio_verdict", "N/A")
        max_r = r.get("max_audio_r", "N/A")
        print(f"  {eid}: {status} | audio={audio} (max_r={max_r})", flush=True)
    
    # Save summary
    summary_path = EXPERIMENTS / "overnight-069-074-summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSummary saved: {summary_path}", flush=True)
    print(f"End: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)


if __name__ == "__main__":
    main()
