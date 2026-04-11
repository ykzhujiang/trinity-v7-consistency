#!/usr/bin/env python3 -u
"""
EXP-V7-055~058 Batch 1: Text-to-Video Game Style Horizontal Comparison
Pure text-to-video (no reference images). 3-Segment extend chain.

Styles: RPG CG, Japanese Action, Low-Poly Indie, Fighting Game
Same scene/story, only style keywords differ.
"""

import json
import os
import sys
import time
import concurrent.futures
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
TOOLS = REPO / "tools"
EXP_DIR = Path(__file__).resolve().parent
OUTPUT = EXP_DIR / "output"
OUTPUT.mkdir(exist_ok=True)

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

# ============================================================
# Shared scene/character/action descriptions (English for Seedance)
# ============================================================
CHAR = "a 25-year-old Chinese male programmer, short black hair, wearing a grey hoodie"
ROOM = "a small 10-sqm rented apartment room, single bed, folding desk with an old laptop, city neon lights outside the window at night, warm desk lamp light"

SEG1_ACTION = (
    f"{CHAR} sits at the desk typing on the laptop, then grabs his hair and sighs in frustration. "
    "He picks up a cup, tilts it — it's empty. He puts the cup down with a tired expression."
)
SEG2_ACTION = (
    f"{CHAR} stands up from the desk, walks to the window. He looks out at the city night view, takes a deep breath. "
    "He turns around and walks back to the desk, sits down again."
)
SEG3_ACTION = (
    f"{CHAR} sits at the desk typing code with focused intensity. His eyes suddenly light up. "
    "He slams the desk excitedly and laughs out loud with joy."
)

# Chinese dialogue per segment (must finish before second 12)
SEG1_DIALOGUE = (
    'Dialogue in Chinese Mandarin (must finish before second 12): '
    '"这个bug改了三天了……水都没了……" '
)
SEG2_DIALOGUE = (
    'Dialogue in Chinese Mandarin (must finish before second 12): '
    '"（看窗外）总会写出来的。" '
)
SEG3_DIALOGUE = (
    'Dialogue in Chinese Mandarin (must finish before second 12): '
    '"等等……我靠！通了！哈哈哈哈！" '
)

SUFFIX = (
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Character never faces camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

# ============================================================
# Style definitions
# ============================================================
STYLES = {
    "v7-055-rpg": {
        "id": "EXP-V7-055",
        "name": "RPG Game CG",
        "prefix": "RPG game cinematic cutscene, Unreal Engine 5 render, dramatic lighting, game CG quality. ",
    },
    "v7-056-jpaction": {
        "id": "EXP-V7-056",
        "name": "Japanese Action Game",
        "prefix": "Japanese action game style, cel-shaded anime, Persona 5 aesthetic, bold outlines, vibrant colors, stylized 3D. ",
    },
    "v7-057-lowpoly": {
        "id": "EXP-V7-057",
        "name": "Low-Poly Indie",
        "prefix": "Low-poly indie game style, geometric minimalist, soft pastel colors, cozy game aesthetic. ",
    },
    "v7-058-fighting": {
        "id": "EXP-V7-058",
        "name": "Fighting Game",
        "prefix": "Fighting game style, Street Fighter 6 quality, dynamic pose, dramatic backlight. ",
    },
}


def build_prompt(style_prefix, seg_action, seg_dialogue):
    """Build a Seedance prompt ≤800 chars."""
    prompt = f"{style_prefix}{ROOM}. {seg_action} {seg_dialogue}{SUFFIX}"
    if len(prompt) > 800:
        # Trim room description if needed
        prompt = f"{style_prefix}{seg_action} {seg_dialogue}{SUFFIX}"
    return prompt[:800]


def run_cmd(cmd, timeout=1800):
    import subprocess
    cmd_str = [str(c) for c in cmd]
    print(f"[CMD] {' '.join(cmd_str)}", flush=True)
    p = subprocess.run(cmd_str, capture_output=True, text=True, timeout=timeout)
    if p.stdout:
        print(p.stdout, flush=True)
    if p.stderr:
        print(f"[STDERR] {p.stderr}", flush=True)
    return p.returncode, p.stdout, p.stderr


def generate_experiment(style_key, style_info):
    """Run full 3-segment extend chain for one style. Returns dict."""
    prefix = style_info["prefix"]
    exp_id = style_info["id"]
    print(f"\n{'='*60}\n{exp_id}: {style_info['name']}\n{'='*60}", flush=True)

    seg_configs = [
        (1, SEG1_ACTION, SEG1_DIALOGUE),
        (2, SEG2_ACTION, SEG2_DIALOGUE),
        (3, SEG3_ACTION, SEG3_DIALOGUE),
    ]

    seg_paths = {}
    prev_video = None

    for seg_idx, action, dialogue in seg_configs:
        tag = f"{style_key}-seg{seg_idx}"
        prompt = build_prompt(prefix, action, dialogue)
        print(f"\n--- {tag} (prompt {len(prompt)} chars) ---", flush=True)

        item = {"id": tag, "prompt": prompt, "out": str(OUTPUT / f"{tag}.mp4")}
        if prev_video:
            item["video"] = prev_video
        # No --images for text-to-video!

        batch_path = EXP_DIR / f"{tag}_batch.json"
        batch_path.write_text(json.dumps([item], indent=2, ensure_ascii=False))

        rc, out, err = run_cmd([
            "python3", "-u", TOOLS / "seedance_gen.py",
            "--batch", batch_path, "--out-dir", OUTPUT,
        ], 1800)

        out_path = Path(item["out"])
        if out_path.exists() and out_path.stat().st_size > 10000:
            seg_paths[seg_idx] = str(out_path)
            prev_video = str(out_path)
            print(f"  ✅ {tag}: {out_path.stat().st_size // 1024}KB", flush=True)
        else:
            print(f"  ❌ {tag}: FAILED — aborting extend chain", flush=True)
            # Check if content moderation blocked it
            if err and ("content" in err.lower() or "审核" in err or "moderat" in err.lower()):
                print(f"  ⛔ CONTENT MODERATION BLOCK — abandoning {exp_id}", flush=True)
                return {"id": exp_id, "status": "blocked", "reason": "content_moderation", "segs": seg_paths}
            break

    # Concat if we have ≥2 segments
    valid_segs = [seg_paths[i] for i in sorted(seg_paths.keys())]
    final_path = str(OUTPUT / f"{style_key}-final.mp4")
    result = {"id": exp_id, "name": style_info["name"], "segs": len(valid_segs), "seg_paths": seg_paths}

    if len(valid_segs) >= 2:
        # Audio check per segment
        all_audio_ok = True
        for i, sp in enumerate(valid_segs, 1):
            rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-select_streams", "a",
                                   "-show_entries", "stream=codec_name", "-of", "csv=p=0", sp], 10)
            has_audio = rc == 0 and out.strip() != ""
            if not has_audio:
                print(f"  ⛔ {style_key} seg{i}: NO AUDIO!", flush=True)
                all_audio_ok = False

        rc, _, _ = run_cmd([
            "python3", "-u", TOOLS / "ffmpeg_concat.py",
            "--inputs", *valid_segs, "--out", final_path, "--check-audio",
        ], 60)

        if rc == 0 and Path(final_path).exists():
            result["final"] = final_path
            result["size_kb"] = Path(final_path).stat().st_size // 1024
            result["audio_ok"] = all_audio_ok
            result["status"] = "ok" if all_audio_ok else "no_audio"
            print(f"  ✅ {style_key} final: {result['size_kb']}KB, audio={'OK' if all_audio_ok else 'FAIL'}", flush=True)
        else:
            result["status"] = "concat_failed"
    else:
        result["status"] = "insufficient_segments"

    return result


def main():
    keys = load_keys()
    os.environ.setdefault("ARK_API_KEY", keys.get("ark_key") or "")
    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        try:
            sv = cfg["skills"]["entries"]["seedance-video"]["env"]
            os.environ.setdefault("VOLCANO_ACCESS_KEY", sv.get("VOLCANO_ACCESS_KEY", ""))
            os.environ.setdefault("VOLCANO_ACCESS_SECRET", sv.get("VOLCANO_ACCESS_SECRET", ""))
        except (KeyError, TypeError):
            pass

    t0 = time.time()

    # Run 4 experiments. Seg1 of all 4 can be parallel, but Seg2/3 depend on previous.
    # Strategy: run experiments 2 at a time (each is sequential internally)
    all_results = {}

    style_keys = list(STYLES.keys())
    # Batch A: first 2 experiments in parallel
    print("\n*** BATCH A: V7-055 (RPG) + V7-056 (JP Action) ***\n", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(generate_experiment, k, STYLES[k]): k for k in style_keys[:2]}
        for f in concurrent.futures.as_completed(futures):
            key = futures[f]
            all_results[key] = f.result()

    # Batch B: next 2 experiments in parallel
    print("\n*** BATCH B: V7-057 (Low-Poly) + V7-058 (Fighting) ***\n", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(generate_experiment, k, STYLES[k]): k for k in style_keys[2:]}
        for f in concurrent.futures.as_completed(futures):
            key = futures[f]
            all_results[key] = f.result()

    elapsed = time.time() - t0

    # Write generation log
    log = {
        "batch": "V7-055~058 (Game Styles Batch 1)",
        "method": "Pure text-to-video, 3-seg extend chain, no reference images",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "elapsed_seconds": round(elapsed),
        "results": all_results,
    }
    log_path = EXP_DIR / "generation-log-batch1.json"
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))

    # Summary
    print(f"\n{'='*60}", flush=True)
    print(f"BATCH 1 SUMMARY (elapsed: {elapsed:.0f}s)", flush=True)
    print(f"{'='*60}", flush=True)
    for key in style_keys:
        r = all_results.get(key, {})
        status = r.get("status", "unknown")
        segs = r.get("segs", 0)
        size = r.get("size_kb", 0)
        audio = "✅" if r.get("audio_ok") else "⛔"
        print(f"  {r.get('id','?')} ({r.get('name','?')}): {status} | {segs} segs | {size}KB | audio {audio}", flush=True)


if __name__ == "__main__":
    main()
