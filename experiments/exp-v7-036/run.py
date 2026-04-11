#!/usr/bin/env python3
"""
EXP-V7-036 Runner — 3-Segment extend consistency test (深夜代码觉醒)
Single character (赵阳), anime + realistic dual-track.

V7-032 Template Enforced:
  - Seg2/Seg3 prompts copy Seg1 character description verbatim
  - Seg2/Seg3 also receive character reference images (not just video_ref)
  - Prompt ≤800 chars per segment
  - Single character, single scene

Steps:
  1. Generate assets (anime + realistic) via gemini_chargen.py
  2. Seg1 (anime + realistic concurrent)
  3. Seg2 video extension from Seg1 (anime + realistic concurrent)
  4. Seg3 video extension from Seg2 (anime + realistic concurrent)
  5. Concat seg1+seg2+seg3 per style
  6. Audio integrity check
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
EXP_DIR = Path(__file__).resolve().parent
ASSETS = EXP_DIR / "assets"
OUTPUT = EXP_DIR / "output"

# ============================================================
# V7-032 Template: Character + Scene descriptions (reused verbatim)
# ============================================================
CHAR_DESC = "28-year-old Chinese man, thin build, messy black hair, dark circles under eyes, black hoodie"
SCENE_DESC = "dark startup office at night, only blue-white monitor glow, cluttered desk with takeout boxes and coffee cups"

# ============================================================
# Seg1 Prompts (≤800 chars each)
# ============================================================
SEG1_PROMPT_ANIME = (
    f"A {CHAR_DESC}, sits at a desk in a {SCENE_DESC}. "
    "He rubs his temples staring at code on screen, mutters tiredly. "
    "He gulps cold coffee and grimaces. Screen pops up an unusual dialog box. "
    "He leans forward squinting at the screen, surprised. He clicks 'Yes' on the popup. "
    "Camera: medium side shot → face closeup → screen closeup → finger clicking closeup. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera. 9:16 vertical."
)

SEG1_PROMPT_REAL = (
    f"A {CHAR_DESC}, sits at a desk in a {SCENE_DESC}. "
    "He rubs his temples staring at code on screen, mutters tiredly. "
    "He gulps cold coffee and grimaces. Screen pops up an unusual dialog box. "
    "He leans forward squinting at the screen, surprised. He clicks 'Yes' on the popup. "
    "Camera: medium side shot → face closeup → screen closeup → finger clicking closeup. "
    "DSLR photograph, 35mm lens, natural lighting. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# Seg2 Prompts — V7-032 template: copy Seg1 char/scene desc verbatim
# ============================================================
SEG2_PROMPT_ANIME = (
    f"Same {CHAR_DESC}. Continuing in the same {SCENE_DESC}. "
    "Golden light bursts from the screen, engulfing him. He recoils in shock. "
    "He looks down at his hands — golden data streams dance on his fingers. "
    "He turns back to the screen, eyes reflecting golden code structure, the bug highlighted. "
    "He grins and starts typing furiously, code scrolling rapidly. "
    "Camera: low angle light burst → hand closeup → eye closeup → side medium typing. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera. 9:16 vertical."
)

SEG2_PROMPT_REAL = (
    f"Same {CHAR_DESC}. Continuing in the same {SCENE_DESC}. "
    "Golden light bursts from the screen, engulfing him. He recoils in shock. "
    "He looks down at his hands — golden data streams dance on his fingers. "
    "He turns back to the screen, eyes reflecting golden code structure, the bug highlighted. "
    "He grins and starts typing furiously, code scrolling rapidly. "
    "Camera: low angle light burst → hand closeup → eye closeup → side medium typing. "
    "DSLR photograph, 35mm lens, natural lighting. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# Seg3 Prompts — V7-032 template: copy Seg1 char/scene desc verbatim
# ============================================================
SEG3_PROMPT_ANIME = (
    f"Same {CHAR_DESC}. Continuing in the same {SCENE_DESC}, golden glow fading, dawn through window. "
    "He leans back exhaling with relief, screen shows '0 errors'. "
    "He stands stretching, looks out window at dawn sky. "
    "Phone buzzes — popup: 'Level 2: refactor entire backend'. "
    "He grins, sits back down, hands on keyboard with excitement. "
    "Camera: overhead wide → window far → phone closeup → medium shot smiling (eyes on screen). "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera. 9:16 vertical."
)

SEG3_PROMPT_REAL = (
    f"Same {CHAR_DESC}. Continuing in the same {SCENE_DESC}, golden glow fading, dawn through window. "
    "He leans back exhaling with relief, screen shows '0 errors'. "
    "He stands stretching, looks out window at dawn sky. "
    "Phone buzzes — popup: 'Level 2: refactor entire backend'. "
    "He grins, sits back down, hands on keyboard with excitement. "
    "Camera: overhead wide → window far → phone closeup → medium shot smiling (eyes on screen). "
    "DSLR photograph, 35mm lens, natural lighting. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera, no 3D, no CG, no Pixar. 9:16 vertical."
)


def run(cmd, timeout=1800):
    print(f"\n$ {' '.join(cmd[:8])}...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, "PYTHONUNBUFFERED": "1"})
    if r.stdout:
        print(r.stdout[-800:], flush=True)
    if r.returncode != 0:
        print(f"FAIL: {r.stderr[-500:]}", flush=True)
    return r.returncode == 0


def step1_assets():
    """Generate character/scene reference images."""
    os.makedirs(ASSETS / "anime", exist_ok=True)
    os.makedirs(ASSETS / "real", exist_ok=True)

    ok1 = run(["python3", "-u", str(TOOLS / "gemini_chargen.py"),
               "--specs", str(EXP_DIR / "asset-specs-anime.json"),
               "--out-dir", str(ASSETS / "anime")])
    ok2 = run(["python3", "-u", str(TOOLS / "gemini_chargen.py"),
               "--specs", str(EXP_DIR / "asset-specs-real.json"),
               "--out-dir", str(ASSETS / "real")])
    return ok1 and ok2


def _anime_images():
    return [str(p) for p in sorted((ASSETS / "anime").glob("*.webp"))[:3]]


def _real_images():
    # Realistic: scene only (no character portraits due to Seedance privacy filter)
    return [str(p) for p in sorted((ASSETS / "real").glob("*.webp"))[:1]]


def step2_seg1():
    """Seg1: independent generation (anime + realistic concurrent)."""
    os.makedirs(OUTPUT, exist_ok=True)
    batch = [
        {"id": "anime-seg1", "prompt": SEG1_PROMPT_ANIME,
         "images": _anime_images(), "out": "anime-seg1.mp4"},
        {"id": "real-seg1", "prompt": SEG1_PROMPT_REAL,
         "images": _real_images(), "out": "real-seg1.mp4"},
    ]
    (EXP_DIR / "seg1-batch.json").write_text(json.dumps(batch, indent=2, ensure_ascii=False))
    return run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                "--batch", str(EXP_DIR / "seg1-batch.json"),
                "--out-dir", str(OUTPUT), "--concurrency", "2"])


def step3_seg2():
    """Seg2: video extension from Seg1 + character reference images."""
    batch = [
        {"id": "anime-seg2", "prompt": SEG2_PROMPT_ANIME,
         "video": str(OUTPUT / "anime-seg1.mp4"),
         "images": _anime_images(), "out": "anime-seg2.mp4"},
        {"id": "real-seg2", "prompt": SEG2_PROMPT_REAL,
         "video": str(OUTPUT / "real-seg1.mp4"),
         "images": _real_images(), "out": "real-seg2.mp4"},
    ]
    (EXP_DIR / "seg2-batch.json").write_text(json.dumps(batch, indent=2, ensure_ascii=False))
    return run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                "--batch", str(EXP_DIR / "seg2-batch.json"),
                "--out-dir", str(OUTPUT), "--concurrency", "2"])


def step4_seg3():
    """Seg3: video extension from Seg2 + character reference images."""
    batch = [
        {"id": "anime-seg3", "prompt": SEG3_PROMPT_ANIME,
         "video": str(OUTPUT / "anime-seg2.mp4"),
         "images": _anime_images(), "out": "anime-seg3.mp4"},
        {"id": "real-seg3", "prompt": SEG3_PROMPT_REAL,
         "video": str(OUTPUT / "real-seg2.mp4"),
         "images": _real_images(), "out": "real-seg3.mp4"},
    ]
    (EXP_DIR / "seg3-batch.json").write_text(json.dumps(batch, indent=2, ensure_ascii=False))
    return run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                "--batch", str(EXP_DIR / "seg3-batch.json"),
                "--out-dir", str(OUTPUT), "--concurrency", "2"])


def step5_concat():
    """Concat seg1+seg2+seg3 for each style."""
    ok1 = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
               "--inputs",
               str(OUTPUT / "anime-seg1.mp4"),
               str(OUTPUT / "anime-seg2.mp4"),
               str(OUTPUT / "anime-seg3.mp4"),
               "--out", str(OUTPUT / "anime-final.mp4"),
               "--check-audio"])
    ok2 = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
               "--inputs",
               str(OUTPUT / "real-seg1.mp4"),
               str(OUTPUT / "real-seg2.mp4"),
               str(OUTPUT / "real-seg3.mp4"),
               "--out", str(OUTPUT / "real-final.mp4"),
               "--check-audio"])
    return ok1 and ok2


def step6_audio_check():
    """Check every segment has audio."""
    all_ok = True
    for f in ["anime-seg1.mp4", "anime-seg2.mp4", "anime-seg3.mp4",
              "real-seg1.mp4", "real-seg2.mp4", "real-seg3.mp4"]:
        path = OUTPUT / f
        if not path.exists():
            print(f"⛔ MISSING: {f}", flush=True)
            all_ok = False
            continue
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                           "-show_entries", "stream=codec_name", "-of", "csv=p=0",
                           str(path)], capture_output=True, text=True)
        if not r.stdout.strip():
            print(f"⛔ NO AUDIO: {f}", flush=True)
            all_ok = False
        else:
            print(f"✓ Audio OK: {f} ({r.stdout.strip()})", flush=True)
    return all_ok


def log_generation(step_name, t0, success):
    """Append to generation-log.json."""
    log_path = EXP_DIR / "generation-log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else []
    log.append({
        "step": step_name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "duration_s": round(time.time() - t0, 1),
        "success": success
    })
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["1", "2", "3", "4", "5", "6", "all"], default="all")
    args = parser.parse_args()

    steps = {
        "1": ("Assets", step1_assets),
        "2": ("Seg1", step2_seg1),
        "3": ("Seg2 extend", step3_seg2),
        "4": ("Seg3 extend", step4_seg3),
        "5": ("Concat", step5_concat),
        "6": ("Audio Check", step6_audio_check),
    }

    if args.step == "all":
        for k in ["1", "2", "3", "4", "5", "6"]:
            name, fn = steps[k]
            print(f"\n{'='*50}\nStep {k}: {name}\n{'='*50}", flush=True)
            t0 = time.time()
            ok = fn()
            log_generation(f"step{k}_{name}", t0, ok)
            if not ok:
                print(f"Step {k} failed. Stopping.", flush=True)
                sys.exit(1)
        print("\n✅ All 6 steps complete! 3-segment videos ready.", flush=True)
    else:
        name, fn = steps[args.step]
        print(f"Running Step {args.step}: {name}", flush=True)
        t0 = time.time()
        ok = fn()
        log_generation(f"step{args.step}_{name}", t0, ok)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
