#!/usr/bin/env python3
"""
EXP-V7-034 Runner — 融资路演翻车→意外救场 (Pitch Disaster → Comeback)
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
# Seg1: "翻车" — PPT crashes during pitch, Zhao Yang improvises
SEG1_PROMPT_ANIME = """A 26-year-old Chinese male startup founder Zhao Yang (tall, thin build, short neat black hair, dark navy blue suit with a slightly crooked tie) stands at the front of a high-end modern conference room giving a pitch presentation. He clicks a presentation remote. The large projection screen behind him shows a polished product demo slide. He speaks confidently: "各位老师好，我是赵阳，今天给大家看一个——". Suddenly the screen goes to a blue error screen (BSOD). Zhao Yang freezes, clicking the remote frantically. Five investors in suits sitting across the long table exchange glances. One investor checks his watch. Zhao Yang's forehead sweats, but then his mouth curls into a slight smirk. He tosses the remote onto the table decisively. He says boldly: "行，PPT死了，但我的产品没死。" He pulls out his smartphone from his pocket and holds it up, saying with a mix of confidence and self-deprecating humor: "各位，我现场演示——如果我的产品也崩了，那我今天就不是来融资的，是来表演脱口秀的。" The investors chuckle. Shot from his left side, medium shot. Warm conference room lighting. Anime digital animation style. Normal speed movement, natural pacing. All dialogue must finish by second 14, leaving at least 1 second of silence at the end. No subtitles, no slow motion, no facing camera directly. 9:16 vertical."""

SEG1_PROMPT_REAL = """A 26-year-old Chinese male startup founder Zhao Yang (tall, thin build, short neat black hair, dark navy blue suit with a slightly crooked tie) stands at the front of a high-end modern conference room giving a pitch presentation. He clicks a presentation remote. The large projection screen behind him shows a polished product demo slide. He speaks confidently: "各位老师好，我是赵阳，今天给大家看一个——". Suddenly the screen goes to a blue error screen (BSOD). Zhao Yang freezes, clicking the remote frantically. Five investors in suits sitting across the long table exchange glances. One investor checks his watch. Zhao Yang's forehead sweats, but then his mouth curls into a slight smirk. He tosses the remote onto the table decisively. He says boldly: "行，PPT死了，但我的产品没死。" He pulls out his smartphone from his pocket and holds it up, saying with a mix of confidence and self-deprecating humor: "各位，我现场演示——如果我的产品也崩了，那我今天就不是来融资的，是来表演脱口秀的。" The investors chuckle. Shot from his left side, medium shot. Warm conference room lighting. Professional DSLR photograph quality, real person, photorealistic cinematic. Normal speed movement, natural pacing. All dialogue must finish by second 14, leaving at least 1 second of silence at the end. No subtitles, no slow motion, no facing camera directly. NOT anime, NOT 3D, NOT cartoon, NOT Pixar. 9:16 vertical."""

# Seg2: "救场" — Live demo wins investors, cliffhanger ending
SEG2_PROMPT_ANIME = """Continuing from previous scene. Same high-end conference room, same lighting and furniture. The same 26-year-old Chinese male startup founder Zhao Yang (tall, thin, short black hair, same dark navy blue suit with crooked tie, but now his sleeves are unconsciously rolled up slightly — showing battle mode) hands his smartphone to the nearest investor. Zhao Yang says: "您试试，随便用。" The investor (50s Chinese male, silver-streaked hair, expensive suit) takes the phone curiously and starts swiping the screen. His eyebrows first furrow then rise with interest as he explores the app. The investor next to him leans over to look. Zhao Yang stands with hands casually in his pockets, trying to look relaxed, but we can see his fist clenched tight in his pocket from the side angle. The lead investor looks up from the phone: "这个推荐算法……是你们自己做的？" Zhao Yang nods: "三个人，六个月，全部自研。" The investors begin whispering to each other with impressed expressions. The lead investor puts the phone down and looks at Zhao Yang: "PPT崩了反而让我看到了真东西。你的技术很扎实。" He pauses, then: "但是——" The frame freezes on Zhao Yang's tense side profile, eyes widening. Cliffhanger. Shot from his left side, medium to medium-wide. Same warm conference room lighting. Anime digital animation style. Normal speed movement, natural pacing. All dialogue must finish by second 14, leaving at least 1 second of silence at the end. No subtitles, no slow motion, no facing camera directly. 9:16 vertical."""

SEG2_PROMPT_REAL = """Continuing from previous scene. Same high-end conference room, same lighting and furniture. The same 26-year-old Chinese male startup founder Zhao Yang (tall, thin, short black hair, same dark navy blue suit with crooked tie, but now his sleeves are unconsciously rolled up slightly — showing battle mode) hands his smartphone to the nearest investor. Zhao Yang says: "您试试，随便用。" The investor (50s Chinese male, silver-streaked hair, expensive suit) takes the phone curiously and starts swiping the screen. His eyebrows first furrow then rise with interest as he explores the app. The investor next to him leans over to look. Zhao Yang stands with hands casually in his pockets, trying to look relaxed, but we can see his fist clenched tight in his pocket from the side angle. The lead investor looks up from the phone: "这个推荐算法……是你们自己做的？" Zhao Yang nods: "三个人，六个月，全部自研。" The investors begin whispering to each other with impressed expressions. The lead investor puts the phone down and looks at Zhao Yang: "PPT崩了反而让我看到了真东西。你的技术很扎实。" He pauses, then: "但是——" The frame freezes on Zhao Yang's tense side profile, eyes widening. Cliffhanger. Shot from his left side, medium to medium-wide. Same warm conference room lighting. Professional DSLR photograph quality, real person, photorealistic cinematic. Normal speed movement, natural pacing. All dialogue must finish by second 14, leaving at least 1 second of silence at the end. No subtitles, no slow motion, no facing camera directly. NOT anime, NOT 3D, NOT cartoon, NOT Pixar. 9:16 vertical."""


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
    print("\n✅ V7-034 COMPLETE", flush=True)


if __name__ == "__main__":
    main()
