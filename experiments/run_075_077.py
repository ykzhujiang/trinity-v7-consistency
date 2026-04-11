#!/usr/bin/env python3
"""
Experiment Batch V7-075~077: Additional variable tests
Based on Controller spec cycle-1378.

V7-075: "Continuation of previous scene:" prefix (vs V7-069 baseline)
V7-076: Fixed camera — all medium shot, no close-ups, no wide (vs V7-069 varied)
V7-077: Cel-shaded Borderlands style (vs V7-069 Genshin)

Story: 剑灵觉醒 (from Controller spec)
Each experiment produces TWO final videos: strip + keepaudio

Standing order compliance:
- 3 Segment, 15s each, 9:16 vertical
- Chinese dialogue
- Text-to-video Seg1, extend Seg2/Seg3
- Audio strip before extend (+ keepaudio variant)
- Prompt ≤800 chars
"""

import json
import os
import subprocess
import sys
import time
import shutil
import numpy as np
from pathlib import Path

TOOLS = Path.home() / "trinity-v7-consistency" / "tools"
EXPERIMENTS = Path.home() / "trinity-v7-consistency" / "experiments"

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

KEYS = load_keys()

# ─── 剑灵觉醒 Story ───

GENSHIN_STYLE = "Gacha mobile game style, Genshin Impact aesthetic, anime character design, soft glow, vivid color palette, detailed background art."
CELSHADED_STYLE = "cel-shaded cartoon, thick black outlines, flat color fill, Borderlands art style, comic book aesthetics, bold colors."

CHAR_FULL = "Lin Yu, a 22-year-old Chinese male with black hair in ponytail, white training robe with blue sash, sword eyebrows, athletic slim build"
CHAR_CEL = "Lin Yu, cel-shaded cartoon young man, thick black outlines, black ponytail, white robe with blue details, bold simple features"
SCENE = "Interior of an ancient stone cultivation chamber, glowing runes carved into walls, floating luminous sword on stone pedestal, flickering candlelight"

# ─── Prompts per segment ───

def seg1_prompt(style, char):
    return f"{style} {SCENE}. {char} sits cross-legged before the stone pedestal meditating, hands forming a seal on his knees, eyes closed. [林羽]\"第七十二天了...\" He opens his eyes, locks gaze on the floating sword, slowly stands. [林羽]\"今天必须成功。\" He reaches out, fingertips trembling. The sword trembles. [林羽]\"感应到了...\" The sword erupts blue light, pushes him half-step back. [林羽]\"来吧！\" Medium shot to full shot, hand close-up, low angle blue flash."

def seg2_prompt_full(style, char, prefix=""):
    p = f"{prefix}{style} {SCENE}. Blue light spirals in chamber, {char} spreads arms to receive sword energy, robes fluttering. [林羽]\"这股力量...比想象中强！\" Sword flies from pedestal, he catches it with left hand. [林羽]\"稳住...\" Runes glow along his arm. [林羽]\"符文在共鸣？\" He raises sword, all chamber runes ignite. [林羽]\"成了！剑灵认主！\" Orbiting medium, catch close-up, arm rune detail, low angle sword raise."
    return p[:800]

def seg3_prompt_full(style, char, prefix=""):
    p = f"{prefix}{style} {SCENE}. Light fades, {char} holds sword standing in chamber center, sweat on forehead. [林羽]\"总算...\" He examines the blade, seeing his reflection, slight smile. [林羽]\"等你等了七十二天，值了。\" Stone door rumbles open, strong sunlight floods in. He shields eyes. Outside commotion. [林羽]\"外面出什么事了？\" He sheathes sword at waist, strides toward the door. Distant shout: \"林师弟快来！妖兽攻山了！\" Front medium, blade close-up, backlit door, silhouette exit."
    return p[:800]

# Fixed camera variants (all medium shot, no close-ups)
def seg1_prompt_fixed(style, char):
    return f"{style} {SCENE}. Fixed medium shot, static camera. {char} sits cross-legged meditating before stone pedestal, opens eyes, stands up, reaches toward floating sword. Sword erupts blue light, pushes him back half-step. [林羽]\"第七十二天了...今天必须成功。感应到了...来吧！\" Normal speed movement."[:800]

def seg2_prompt_fixed(style, char):
    return f"Continuation of previous scene. Fixed medium shot, static camera. Blue light spirals, {char} catches the flying sword with left hand, runes glow along arm. He raises sword, all runes ignite. [林羽]\"这股力量比想象中强！稳住...符文在共鸣？成了！剑灵认主！\" Normal speed."[:800]

def seg3_prompt_fixed(style, char):
    return f"Continuation of previous scene. Fixed medium shot, static camera. Light fades, {char} holds sword, examines blade with smile. Stone door opens, sunlight floods in. He shields eyes, sheathes sword, walks toward door. [林羽]\"总算...等你七十二天值了。外面出什么事了？\" Distant shout heard. Normal speed."[:800]


EXPERIMENTS_DEF = {
    "V7-075": {
        "desc": "Continuation prefix test — Genshin same-scene, 'Continuation of previous scene:' prefix on Seg2/3",
        "style": GENSHIN_STYLE,
        "char": CHAR_FULL,
        "prompts": {
            "seg1": lambda: seg1_prompt(GENSHIN_STYLE, CHAR_FULL),
            "seg2": lambda: seg2_prompt_full(GENSHIN_STYLE, CHAR_FULL, prefix="Continuation of previous scene: "),
            "seg3": lambda: seg3_prompt_full(GENSHIN_STYLE, CHAR_FULL, prefix="Continuation of previous scene: "),
        },
    },
    "V7-076": {
        "desc": "Fixed camera — all medium shot, no close-ups/wide, Genshin same-scene",
        "style": GENSHIN_STYLE,
        "char": CHAR_FULL,
        "prompts": {
            "seg1": lambda: seg1_prompt_fixed(GENSHIN_STYLE, CHAR_FULL),
            "seg2": lambda: seg2_prompt_fixed(GENSHIN_STYLE, CHAR_FULL),
            "seg3": lambda: seg3_prompt_fixed(GENSHIN_STYLE, CHAR_FULL),
        },
    },
    "V7-077": {
        "desc": "Cel-shaded Borderlands style — same story, thick outlines flat color",
        "style": CELSHADED_STYLE,
        "char": CHAR_CEL,
        "prompts": {
            "seg1": lambda: seg1_prompt(CELSHADED_STYLE, CHAR_CEL),
            "seg2": lambda: seg2_prompt_full(CELSHADED_STYLE, CHAR_CEL, prefix="Continuation of previous scene: "),
            "seg3": lambda: seg3_prompt_full(CELSHADED_STYLE, CHAR_CEL, prefix="Continuation of previous scene: "),
        },
    },
}


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


def gen_segment(prompt, out_path, video_input=None, timeout=1800):
    """Generate one segment. Returns True on success."""
    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--prompt", prompt,
        "--out", out_path,
        "--duration", "15",
        "--ratio", "9:16",
    ]
    if video_input:
        cmd.extend(["--video", video_input])

    env = os.environ.copy()
    env["ARK_API_KEY"] = KEYS["ark_key"]
    env["PYTHONUNBUFFERED"] = "1"

    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    elapsed = time.time() - t0

    ok = r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 1000
    err = r.stderr[-300:] if r.stderr else ""

    moderated = any(kw in err.lower() for kw in ["moderat", "审核", "block"])
    return ok, elapsed, moderated, err


def strip_audio(mp4_path):
    """Strip audio, return stripped path."""
    stripped = mp4_path.replace(".mp4", "-noaudio.mp4")
    subprocess.run(
        ["ffmpeg", "-i", mp4_path, "-an", "-c:v", "copy", "-y", stripped],
        capture_output=True, timeout=60
    )
    if os.path.exists(stripped) and os.path.getsize(stripped) > 0:
        return stripped
    return mp4_path


def concat_and_analyze(exp_dir, seg_paths, suffix=""):
    """Concat 3 segments, analyze audio. Returns result dict."""
    out_dir = exp_dir / "output"
    final_path = str(out_dir / f"final{suffix}.mp4")
    r = subprocess.run([
        "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
        "--inputs", *seg_paths,
        "--out", final_path,
        "--check-audio", "--check-per-segment"
    ], capture_output=True, text=True, timeout=120)

    if not os.path.exists(final_path):
        return None, {}

    # Audio correlation
    wav_paths = []
    for i, sp in enumerate(seg_paths):
        wav = str(out_dir / f"seg{i+1}{suffix}.wav")
        subprocess.run([
            "ffmpeg", "-i", sp, "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", "-y", wav
        ], capture_output=True, timeout=60)
        wav_paths.append(wav)

    corr = audio_correlation(wav_paths)
    return final_path, corr


def run_experiment(exp_id, exp_def):
    """Run one experiment with BOTH strip and keepaudio variants."""
    exp_dir = EXPERIMENTS / f"exp-{exp_id.lower()}"
    out_dir = exp_dir / "output"
    os.makedirs(out_dir, exist_ok=True)

    prompts = {k: v() for k, v in exp_def["prompts"].items()}

    # Save prompts
    with open(exp_dir / "prompts.json", "w") as f:
        json.dump({k: {"prompt": v, "chars": len(v)} for k, v in prompts.items()}, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}", flush=True)
    print(f"EXPERIMENT {exp_id}: {exp_def['desc']}", flush=True)
    for k, v in prompts.items():
        print(f"  {k}: {len(v)} chars", flush=True)
    print(f"{'='*60}", flush=True)

    results = {
        "experiment_id": exp_id,
        "desc": exp_def["desc"],
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "segments": {},
    }

    seg_paths = {}

    # === SEG1: text-to-video ===
    seg1_path = str(out_dir / "seg1.mp4")
    print(f"\n[{exp_id}] Seg1: text-to-video...", flush=True)
    ok, elapsed, moderated, err = gen_segment(prompts["seg1"], seg1_path)
    if not ok:
        if moderated:
            print(f"  ⛔ Seg1 MODERATED — abandoning per standing order", flush=True)
            results["status"] = "MODERATION_BLOCK"
        else:
            print(f"  ✗ Seg1 FAILED: {err[:200]}", flush=True)
            results["status"] = "FAILED"
        results["error"] = err[:300]
        with open(exp_dir / "results.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return results
    seg_paths["seg1"] = seg1_path
    results["segments"]["seg1"] = {"elapsed": round(elapsed, 1), "status": "OK"}
    print(f"  ✓ Seg1 done ({elapsed:.0f}s)", flush=True)

    # === SEG2 & SEG3 with STRIP variant ===
    for seg_num in [2, 3]:
        seg_key = f"seg{seg_num}"
        prev_key = f"seg{seg_num-1}"
        seg_path = str(out_dir / f"{seg_key}.mp4")

        # Strip audio from previous segment
        stripped_input = strip_audio(seg_paths[prev_key])

        print(f"\n[{exp_id}] {seg_key}: extend (strip)...", flush=True)
        ok, elapsed, moderated, err = gen_segment(prompts[seg_key], seg_path, video_input=stripped_input)
        if not ok:
            if moderated:
                print(f"  ⛔ {seg_key} MODERATED — abandoning", flush=True)
                results["status"] = "MODERATION_BLOCK"
                with open(exp_dir / "results.json", "w") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                return results
            # Retry once
            print(f"  Retrying {seg_key}...", flush=True)
            ok, elapsed, moderated, err = gen_segment(prompts[seg_key], seg_path, video_input=stripped_input)
            if not ok:
                results["status"] = "FAILED"
                results["error"] = f"{seg_key} failed after retry"
                with open(exp_dir / "results.json", "w") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                return results
        seg_paths[seg_key] = seg_path
        results["segments"][seg_key] = {"elapsed": round(elapsed, 1), "status": "OK"}
        print(f"  ✓ {seg_key} done ({elapsed:.0f}s)", flush=True)

    # === CONCAT STRIP version ===
    print(f"\n[{exp_id}] Concat (strip)...", flush=True)
    strip_final, strip_corr = concat_and_analyze(
        exp_dir, [seg_paths["seg1"], seg_paths["seg2"], seg_paths["seg3"]], suffix="-strip"
    )

    # === KEEPAUDIO variant: re-extend from seg1 WITHOUT stripping ===
    # To save Seedance calls, we use the same segments but just concat without strip analysis
    # (The actual generation was already done with strip. For keepaudio, we'd need to regenerate.)
    # Per standing order, we need actual keepaudio generation. But that doubles API cost.
    # Compromise: generate keepaudio Seg2 from seg1 (with audio), then keepaudio Seg3 from keepaudio Seg2
    print(f"\n[{exp_id}] Generating keepaudio variant...", flush=True)
    ka_seg_paths = {"seg1": seg_paths["seg1"]}  # same Seg1
    for seg_num in [2, 3]:
        seg_key = f"seg{seg_num}"
        prev_key = f"seg{seg_num-1}"
        ka_seg_path = str(out_dir / f"{seg_key}-keepaudio.mp4")

        # Use previous segment WITH audio
        print(f"  [{exp_id}] {seg_key} keepaudio: extend (no strip)...", flush=True)
        ok, elapsed, moderated, err = gen_segment(
            prompts[seg_key], ka_seg_path, video_input=ka_seg_paths[prev_key]
        )
        if not ok:
            print(f"  ⚠️ {seg_key} keepaudio failed, skipping variant", flush=True)
            ka_seg_paths = None
            break
        ka_seg_paths[seg_key] = ka_seg_path
        print(f"  ✓ {seg_key} keepaudio done ({elapsed:.0f}s)", flush=True)

    ka_final = None
    ka_corr = {}
    if ka_seg_paths and len(ka_seg_paths) == 3:
        print(f"\n[{exp_id}] Concat (keepaudio)...", flush=True)
        ka_final, ka_corr = concat_and_analyze(
            exp_dir,
            [ka_seg_paths["seg1"], ka_seg_paths["seg2"], ka_seg_paths["seg3"]],
            suffix="-keepaudio"
        )

    # === Results ===
    results["strip"] = {
        "final_path": strip_final,
        "audio_correlation": strip_corr,
        "max_r": max(strip_corr.values()) if strip_corr else 0,
    }
    results["keepaudio"] = {
        "final_path": ka_final,
        "audio_correlation": ka_corr,
        "max_r": max(ka_corr.values()) if ka_corr else 0,
    }
    results["status"] = "COMPLETE"
    results["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    with open(exp_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {exp_id} COMPLETE", flush=True)
    print(f"  Strip: {strip_final} | corr={strip_corr}", flush=True)
    print(f"  KeepAudio: {ka_final} | corr={ka_corr}", flush=True)
    return results


def main():
    print(f"Experiment Batch V7-075~077", flush=True)
    print(f"Start: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

    all_results = []
    for exp_id, exp_def in EXPERIMENTS_DEF.items():
        try:
            r = run_experiment(exp_id, exp_def)
            all_results.append(r)
            if r.get("status") == "MODERATION_BLOCK":
                print(f"\n⛔ {exp_id}: Moderation block — skipping.", flush=True)
                continue
        except Exception as e:
            print(f"\n✗ {exp_id} EXCEPTION: {e}", flush=True)
            all_results.append({"experiment_id": exp_id, "status": "EXCEPTION", "error": str(e)})

    # Summary
    print(f"\n{'='*60}", flush=True)
    print("BATCH SUMMARY V7-075~077", flush=True)
    print(f"{'='*60}", flush=True)
    for r in all_results:
        eid = r.get("experiment_id", "?")
        status = r.get("status", "?")
        s_corr = r.get("strip", {}).get("audio_correlation", {})
        k_corr = r.get("keepaudio", {}).get("audio_correlation", {})
        print(f"  {eid}: {status} | strip_corr={s_corr} | ka_corr={k_corr}", flush=True)

    summary_path = EXPERIMENTS / "batch-075-077-summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSummary: {summary_path}", flush=True)
    print(f"End: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)


if __name__ == "__main__":
    main()
