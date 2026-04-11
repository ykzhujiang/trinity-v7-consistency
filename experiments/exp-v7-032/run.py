#!/usr/bin/env python3
"""
EXP-V7-032 Runner — Comedy Startup AI Assistant
Uses existing modular tools: gemini_chargen.py, seedance_gen.py, ffmpeg_concat.py

Steps:
  1. Generate assets (anime + realistic) via gemini_chargen.py --specs
  2. Generate Seg1 videos (anime + realistic concurrent) via seedance_gen.py --batch
  3. Generate Seg2 videos (video extension from Seg1, concurrent) via seedance_gen.py --batch
  4. Concat Seg1+Seg2 per style via ffmpeg_concat.py
  5. Audio check (ffprobe each segment)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).parent.parent.parent / "tools"
EXP_DIR = Path(__file__).parent
ASSETS = EXP_DIR / "assets"
OUTPUT = EXP_DIR / "output"


def run(cmd, timeout=1800):
    print(f"$ {' '.join(cmd[:6])}...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, "PYTHONUNBUFFERED": "1"})
    if r.stdout: print(r.stdout[-500:], flush=True)
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


# --- Seedance prompts ---
SEG1_PROMPT_ANIME = """A 28-year-old Chinese man (round face, black-framed glasses, plaid shirt, slightly overweight) sits alone at a desk in a dark startup office at night, typing on a keyboard. Multiple monitors glow blue-white. Scattered takeout boxes and coffee cups. He suddenly freezes, stares at the screen with a shocked expression, his hand knocking over a coffee cup. Coffee spills across the desk. The monitor shows a popup dialog box with text. His eyes go wide, jaw drops slightly, then he leans forward squinting at the screen in disbelief. Medium shot from the side, warm monitor light in dark room. Anime digital animation style. Normal speed movement, natural pacing. No subtitles, no slow motion, no facing camera. 9:16 vertical."""

SEG1_PROMPT_REAL = """A 28-year-old Chinese man (round face, black-framed glasses, plaid shirt, slightly overweight) sits alone at a desk in a dark startup office at night, typing on a keyboard. Multiple monitors glow blue-white. Scattered takeout boxes and coffee cups. He suddenly freezes, stares at the screen with a shocked expression, his hand knocking over a coffee cup. Coffee spills across the desk. The monitor shows a popup dialog box with text. His eyes go wide, jaw drops slightly, then he leans forward squinting at the screen in disbelief. Medium shot from the side, warm monitor light in dark room. Photorealistic cinematic style. Normal speed movement, natural pacing. No subtitles, no slow motion, no facing camera. 9:16 vertical."""

SEG2_PROMPT_ANIME = """Continuing from previous scene. Same 28-year-old Chinese man (round face, black-framed glasses, plaid shirt) now leaning towards his monitor with a curious, tentative expression. He speaks to the screen, gesturing with one hand. After a brief pause, the screen suddenly explodes with rapid lines of scrolling code — green and white text flying across the dark monitor. The man's expression shifts from cautious to amazed — eyes widening, mouth opening, slowly breaking into a huge excited grin. He pushes his glasses up and leans back in awe, watching the code pour across the screen. Same dark office, same desk, same monitor setup. Medium-wide shot. Anime digital animation style. Normal speed movement, natural pacing. No subtitles, no slow motion, no facing camera. 9:16 vertical."""

SEG2_PROMPT_REAL = """Continuing from previous scene. Same 28-year-old Chinese man (round face, black-framed glasses, plaid shirt) now leaning towards his monitor with a curious, tentative expression. He speaks to the screen, gesturing with one hand. After a brief pause, the screen suddenly explodes with rapid lines of scrolling code — green and white text flying across the dark monitor. The man's expression shifts from cautious to amazed — eyes widening, mouth opening, slowly breaking into a huge excited grin. He pushes his glasses up and leans back in awe, watching the code pour across the screen. Same dark office, same desk, same monitor setup. Medium-wide shot. Photorealistic cinematic style. Normal speed movement, natural pacing. No subtitles, no slow motion, no facing camera. 9:16 vertical."""


def step2_seg1():
    """Generate Seg1 (anime + realistic concurrent)."""
    os.makedirs(OUTPUT, exist_ok=True)
    anime_imgs = sorted((ASSETS / "anime").glob("*.webp"))[:3]
    real_imgs = sorted((ASSETS / "real").glob("*.webp"))[:3]

    batch = [
        {"id": "anime-seg1", "prompt": SEG1_PROMPT_ANIME,
         "images": [str(p) for p in anime_imgs], "out": "anime-seg1.mp4"},
        {"id": "real-seg1", "prompt": SEG1_PROMPT_REAL,
         "images": [str(p) for p in real_imgs], "out": "real-seg1.mp4"},
    ]
    batch_file = EXP_DIR / "seg1-batch.json"
    batch_file.write_text(json.dumps(batch, indent=2, ensure_ascii=False))

    return run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                "--batch", str(batch_file), "--out-dir", str(OUTPUT), "--concurrency", "2"])


def step3_seg2():
    """Generate Seg2 (video extension from Seg1, concurrent)."""
    batch = [
        {"id": "anime-seg2", "prompt": SEG2_PROMPT_ANIME,
         "video": str(OUTPUT / "anime-seg1.mp4"), "out": "anime-seg2.mp4"},
        {"id": "real-seg2", "prompt": SEG2_PROMPT_REAL,
         "video": str(OUTPUT / "real-seg1.mp4"), "out": "real-seg2.mp4"},
    ]
    batch_file = EXP_DIR / "seg2-batch.json"
    batch_file.write_text(json.dumps(batch, indent=2, ensure_ascii=False))

    return run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                "--batch", str(batch_file), "--out-dir", str(OUTPUT), "--concurrency", "2"])


def step4_concat():
    """Concat Seg1+Seg2 for each style."""
    ok1 = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
               str(OUTPUT / "anime-seg1.mp4"), str(OUTPUT / "anime-seg2.mp4"),
               "-o", str(OUTPUT / "anime-final.mp4")])
    ok2 = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
               str(OUTPUT / "real-seg1.mp4"), str(OUTPUT / "real-seg2.mp4"),
               "-o", str(OUTPUT / "real-final.mp4")])
    return ok1 and ok2


def step5_audio_check():
    """Check each segment has audio track."""
    all_ok = True
    for f in ["anime-seg1.mp4", "anime-seg2.mp4", "real-seg1.mp4", "real-seg2.mp4"]:
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


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["1", "2", "3", "4", "5", "all"], default="all")
    args = parser.parse_args()

    steps = {
        "1": ("Assets", step1_assets),
        "2": ("Seg1", step2_seg1),
        "3": ("Seg2", step3_seg2),
        "4": ("Concat", step4_concat),
        "5": ("Audio Check", step5_audio_check),
    }

    if args.step == "all":
        for k in ["1", "2", "3", "4", "5"]:
            name, fn = steps[k]
            print(f"\n{'='*40}\nStep {k}: {name}\n{'='*40}", flush=True)
            if not fn():
                print(f"Step {k} failed. Stopping.", flush=True)
                sys.exit(1)
        print("\n✅ All steps complete!", flush=True)
    else:
        name, fn = steps[args.step]
        print(f"Running Step {args.step}: {name}", flush=True)
        sys.exit(0 if fn() else 1)


if __name__ == "__main__":
    main()
