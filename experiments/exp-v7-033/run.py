#!/usr/bin/env python3
"""
EXP-V7-033 Runner — 修仙系统觉醒 (Xiuxian System Awakening)
Uses modular tools: gemini_chargen.py, seedance_gen.py, ffmpeg_concat.py

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

TOOLS = Path(__file__).parent.parent / "tools"
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
SEG1_PROMPT_ANIME = """A 28-year-old Chinese male programmer (thin build, short messy black hair, black-framed rectangular glasses, blue-and-white plaid flannel shirt, dark circles under eyes) is slumped asleep on his keyboard in a dark office at night. Only his desk lamp is on. Dual monitors glow blue. Takeout boxes and a coffee cup on the desk. He suddenly jerks awake, lifting his head — keyboard key marks on his cheek. He rubs his eyes, then freezes as a translucent blue holographic panel materializes in front of him. His eyes widen in disbelief. He hesitantly pokes the floating panel with one finger. A faint blue glow flows from the panel through his hand. The coffee cup on the desk slowly levitates about 10 centimeters off the surface. His jaw drops, eyes bulging. He grabs the cup and pushes it back down, looking around frantically. He whispers to himself with a shaky voice. Medium shot from his left side, warm desk lamp light contrasting cold monitor glow. Anime digital animation style. Normal speed movement, natural pacing. No subtitles, no slow motion, no facing camera. 9:16 vertical."""

SEG1_PROMPT_REAL = """A 28-year-old Chinese male programmer (thin build, short messy black hair, black-framed rectangular glasses, blue-and-white plaid flannel shirt, dark circles under eyes) is slumped asleep on his keyboard in a dark office at night. Only his desk lamp is on. Dual monitors glow blue. Takeout boxes and a coffee cup on the desk. He suddenly jerks awake, lifting his head — keyboard key marks on his cheek. He rubs his eyes, then freezes as a translucent blue holographic panel materializes in front of him. His eyes widen in disbelief. He hesitantly pokes the floating panel with one finger. A faint blue glow flows from the panel through his hand. The coffee cup on the desk slowly levitates about 10 centimeters off the surface. His jaw drops, eyes bulging. He grabs the cup and pushes it back down, looking around frantically. He whispers to himself with a shaky voice. Medium shot from his left side, warm desk lamp light contrasting cold monitor glow. Photorealistic cinematic style, DSLR quality. Normal speed movement, natural pacing. No subtitles, no slow motion, no facing camera. 9:16 vertical."""

SEG2_PROMPT_ANIME = """Continuing from previous scene. Same 28-year-old Chinese male programmer (thin build, short messy black hair, black-framed rectangular glasses, same blue-and-white plaid flannel shirt) now sitting at the same desk in the same office but daytime — all lights on, other desks occupied. He sneaks his hands under the desk and closes his eyes, concentrating. His hands emit a faint blue glow. Suddenly the monitor of the woman sitting next to him (25-year-old Chinese female, ponytail, white t-shirt) flickers with static. She turns to look at him. He yanks his hands up to the keyboard and pretends to type, forcing an awkward smile. A translucent blue holographic panel pops up again in front of him (only he can see it). He reads it, then his eyes shift to see his boss (45-year-old Chinese male, slightly overweight, suit, stern face) walking towards him from across the office. His expression shifts from smug to panicked, swallowing hard. Medium-wide shot from his left side. Anime digital animation style. Normal speed movement, natural pacing. No subtitles, no slow motion, no facing camera. 9:16 vertical."""

SEG2_PROMPT_REAL = """Continuing from previous scene. Same 28-year-old Chinese male programmer (thin build, short messy black hair, black-framed rectangular glasses, same blue-and-white plaid flannel shirt) now sitting at the same desk in the same office but daytime — all lights on, other desks occupied. He sneaks his hands under the desk and closes his eyes, concentrating. His hands emit a faint blue glow. Suddenly the monitor of the woman sitting next to him (25-year-old Chinese female, ponytail, white t-shirt) flickers with static. She turns to look at him. He yanks his hands up to the keyboard and pretends to type, forcing an awkward smile. A translucent blue holographic panel pops up again in front of him (only he can see it). He reads it, then his eyes shift to see his boss (45-year-old Chinese male, slightly overweight, suit, stern face) walking towards him from across the office. His expression shifts from smug to panicked, swallowing hard. Medium-wide shot from his left side. Photorealistic cinematic style, DSLR quality. Normal speed movement, natural pacing. No subtitles, no slow motion, no facing camera. 9:16 vertical."""


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
         "video_ref": str(OUTPUT / "anime-seg1.mp4"), "out": "anime-seg2.mp4"},
        {"id": "real-seg2", "prompt": SEG2_PROMPT_REAL,
         "video_ref": str(OUTPUT / "real-seg1.mp4"), "out": "real-seg2.mp4"},
    ]
    batch_file = EXP_DIR / "seg2-batch.json"
    batch_file.write_text(json.dumps(batch, indent=2, ensure_ascii=False))

    return run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                "--batch", str(batch_file), "--out-dir", str(OUTPUT), "--concurrency", "2"])


def step4_concat():
    """Concat Seg1+Seg2 per style."""
    ok1 = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
               str(OUTPUT / "anime-seg1.mp4"), str(OUTPUT / "anime-seg2.mp4"),
               "-o", str(OUTPUT / "final-anime.mp4")])
    ok2 = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
               str(OUTPUT / "real-seg1.mp4"), str(OUTPUT / "real-seg2.mp4"),
               "-o", str(OUTPUT / "final-real.mp4")])
    return ok1 and ok2


def step5_audio_check():
    """Check all segments have audio."""
    all_ok = True
    for f in ["anime-seg1.mp4", "anime-seg2.mp4", "real-seg1.mp4", "real-seg2.mp4",
              "final-anime.mp4", "final-real.mp4"]:
        path = OUTPUT / f
        if not path.exists():
            print(f"MISSING: {f}", flush=True)
            all_ok = False
            continue
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=codec_type", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True)
        has_audio = "audio" in r.stdout
        status = "✓ audio" if has_audio else "⛔ NO AUDIO"
        sz = path.stat().st_size / 1024 / 1024
        print(f"  {f}: {sz:.1f}MB {status}", flush=True)
        if not has_audio:
            all_ok = False
    return all_ok


def main():
    steps = [
        ("Step 1: Generate Assets", step1_assets),
        ("Step 2: Generate Seg1 (concurrent)", step2_seg1),
        ("Step 3: Generate Seg2 (concurrent)", step3_seg2),
        ("Step 4: Concat", step4_concat),
        ("Step 5: Audio Check", step5_audio_check),
    ]
    for name, fn in steps:
        print(f"\n{'='*60}\n{name}\n{'='*60}", flush=True)
        if not fn():
            print(f"\n⛔ FAILED at: {name}", flush=True)
            sys.exit(1)
    print("\n✅ V7-033 COMPLETE", flush=True)


if __name__ == "__main__":
    main()
