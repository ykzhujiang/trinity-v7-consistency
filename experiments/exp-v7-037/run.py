#!/usr/bin/env python3
"""
EXP-V7-037 Runner — 2-Segment INDEPENDENT generation (no extend) consistency test
Story: 外卖王者 (Delivery King) — 李磊, 25yo delivery rider
Key test: Same assets, independent Seg1+Seg2 generation, then concat.

Steps:
  1. Generate assets (anime + realistic) via gemini_chargen.py
  2. Seg1 (anime + realistic concurrent) — normal generation with ref images
  3. Seg2 (anime + realistic concurrent) — INDEPENDENT generation with SAME ref images (NO video extension)
  4. Concat seg1+seg2 per style
  5. Audio integrity check per segment
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
# Character + Scene descriptions (reused verbatim in both segments)
# ============================================================
CHAR_DESC = "25-year-old Chinese man, round face, tanned skin, stocky build, yellow delivery uniform jacket, white helmet, riding an electric scooter"
SCENE_DESC = "night city street with street lamps, neon signs, delivery electric scooter parked nearby"

# ============================================================
# Seg1 Prompts — 接单之王
# ============================================================
SEG1_PROMPT_ANIME = (
    f"A {CHAR_DESC}, stands beside his electric scooter on a {SCENE_DESC}. "
    "He looks down at his phone with a surprised face. He mutters and shakes his head. "
    "He hangs a delivery bag on the scooter's back seat and taps his phone rapidly to accept orders. "
    "He swings his leg over the scooter, twists the throttle, headlight illuminates the road ahead. "
    "Neon lights reflect on his face as he grins excitedly. "
    "Camera: medium shot → medium to close push → side full shot scooter starting → side medium tracking. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera. 9:16 vertical."
)

SEG1_PROMPT_REAL = (
    f"A {CHAR_DESC}, stands beside his electric scooter on a {SCENE_DESC}. "
    "He looks down at his phone with a surprised face. He mutters and shakes his head. "
    "He hangs a delivery bag on the scooter's back seat and taps his phone rapidly to accept orders. "
    "He swings his leg over the scooter, twists the throttle, headlight illuminates the road ahead. "
    "Neon lights reflect on his face as he grins excitedly. "
    "Camera: medium shot → medium to close push → side full shot scooter starting → side medium tracking. "
    "DSLR photograph, 35mm lens, natural street lighting at night. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# Seg2 Prompts — 极速送达 (INDEPENDENT, same char/scene desc verbatim)
# ============================================================
SEG2_PROMPT_ANIME = (
    f"A {CHAR_DESC}, stops his electric scooter at a red traffic light on a {SCENE_DESC}. "
    "He breathes heavily and wipes sweat from his forehead with his right hand. "
    "His phone buzzes, he glances down and smirks — a new order on the way. "
    "The traffic light turns green. He twists the throttle hard, body leaning forward, scooter accelerates. "
    "Street lamp light flashes across his face rhythmically as he rides fast, determined and excited expression. "
    "Camera: close-up face → close-up face+phone → side full shot fast start → side medium tracking accelerating. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera. 9:16 vertical."
)

SEG2_PROMPT_REAL = (
    f"A {CHAR_DESC}, stops his electric scooter at a red traffic light on a {SCENE_DESC}. "
    "He breathes heavily and wipes sweat from his forehead with his right hand. "
    "His phone buzzes, he glances down and smirks — a new order on the way. "
    "The traffic light turns green. He twists the throttle hard, body leaning forward, scooter accelerates. "
    "Street lamp light flashes across his face rhythmically as he rides fast, determined and excited expression. "
    "Camera: close-up face → close-up face+phone → side full shot fast start → side medium tracking accelerating. "
    "DSLR photograph, 35mm lens, natural street lighting at night. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# TTS Dialogue (Chinese)
# ============================================================
DIALOGUE = {
    "seg1": [
        {"speaker": "李磊", "text": "又是五公里外的奶茶？这单谁敢接啊。"},
        {"speaker": "李磊", "text": "我接！五公里算什么，十公里我也冲。"},
        {"speaker": "李磊", "text": "老板们等着，外卖之神来了！"},
        {"speaker": "李磊", "text": "今晚必须破纪录，五十单！"},
    ],
    "seg2": [
        {"speaker": "李磊", "text": "还有八分钟……三公里……稳了稳了。"},
        {"speaker": "李磊", "text": "好家伙，顺路单！老天都帮我破纪录。"},
        {"speaker": "李磊", "text": "绿灯一亮我就是这条街最快的男人！"},
        {"speaker": "李磊", "text": "外卖王者，永不迟到！"},
    ],
}


def run(cmd, **kwargs):
    print(f"\n{'='*60}", flush=True)
    print(f"CMD: {' '.join(cmd[:5])}...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if r.returncode != 0:
        print(f"STDERR: {r.stderr[-500:]}", flush=True)
    return r


def main():
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(OUTPUT, exist_ok=True)

    gen_log = {"experiment": "EXP-V7-037", "method": "independent-concat", "steps": []}

    # ── Step 1: Generate Assets ──────────────────────────────
    print("\n[STEP 1] Generating reference assets...", flush=True)

    asset_specs_anime = [
        {"name": "lilei-anime", "type": "character",
         "desc": "25岁中国男性外卖骑手，圆脸，晒黑皮肤，壮实体型，穿黄色外卖工服夹克，戴白色头盔，站在夜晚街边",
         "style": "anime"},
        {"name": "street-night-anime", "type": "scene",
         "desc": "夜晚中国城市街道，路灯照亮人行道，霓虹灯招牌发光，外卖电动车停在路边，氛围温暖",
         "style": "anime"},
    ]
    asset_specs_real = [
        {"name": "lilei-real", "type": "character",
         "desc": "25岁中国男性外卖骑手，圆脸，晒黑皮肤，壮实体型，穿黄色外卖工服夹克，戴白色头盔，站在夜晚街边",
         "style": "realistic"},
        {"name": "street-night-real", "type": "scene",
         "desc": "夜晚中国城市街道，路灯照亮人行道，霓虹灯招牌发光，外卖电动车停在路边，氛围温暖",
         "style": "realistic"},
    ]

    # Write spec files
    anime_spec = EXP_DIR / "asset-specs-anime.json"
    real_spec = EXP_DIR / "asset-specs-real.json"
    anime_spec.write_text(json.dumps(asset_specs_anime, ensure_ascii=False, indent=2))
    real_spec.write_text(json.dumps(asset_specs_real, ensure_ascii=False, indent=2))

    # Generate anime assets
    r = run(["python3", "-u", str(TOOLS / "gemini_chargen.py"),
             "--specs", str(anime_spec), "--out-dir", str(ASSETS)])
    if r.returncode != 0:
        print(f"WARN: Anime asset gen failed: {r.stderr[-200:]}", flush=True)

    # Generate realistic assets
    r = run(["python3", "-u", str(TOOLS / "gemini_chargen.py"),
             "--specs", str(real_spec), "--out-dir", str(ASSETS)])
    if r.returncode != 0:
        print(f"WARN: Real asset gen failed: {r.stderr[-200:]}", flush=True)

    # Check assets
    anime_char = ASSETS / "char-lilei-anime.webp"
    anime_scene = ASSETS / "scene-street-night-anime.webp"
    real_char = ASSETS / "char-lilei-real.webp"
    real_scene = ASSETS / "scene-street-night-real.webp"

    for p in [anime_char, anime_scene, real_char, real_scene]:
        if p.exists():
            sz = p.stat().st_size
            print(f"  ✓ {p.name} ({sz//1024}KB)", flush=True)
        else:
            print(f"  ✗ MISSING: {p.name}", flush=True)

    gen_log["steps"].append({"step": "assets", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")})

    # ── Step 2: Seg1 (anime + realistic concurrent) ──────────
    print("\n[STEP 2] Generating Seg1 (anime + realistic concurrent)...", flush=True)

    seg1_batch = [
        {
            "id": "anime-seg1",
            "prompt": SEG1_PROMPT_ANIME,
            "images": [str(anime_char), str(anime_scene)],
            "out": "anime-seg1.mp4"
        },
        {
            "id": "real-seg1",
            "prompt": SEG1_PROMPT_REAL,
            "images": [str(real_scene)],  # scene-only for realistic (privacy filter)
            "out": "real-seg1.mp4"
        },
    ]

    seg1_json = EXP_DIR / "seg1-batch.json"
    seg1_json.write_text(json.dumps(seg1_batch, ensure_ascii=False, indent=2))

    r = run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
             "--batch", str(seg1_json), "--out-dir", str(OUTPUT)])
    print(f"Seg1 return code: {r.returncode}", flush=True)
    if r.stdout:
        print(r.stdout[-1000:], flush=True)

    gen_log["steps"].append({"step": "seg1", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                             "prompts": {"anime": SEG1_PROMPT_ANIME, "real": SEG1_PROMPT_REAL}})

    # ── Step 3: Seg2 INDEPENDENT (same assets, NO video extension) ──
    print("\n[STEP 3] Generating Seg2 INDEPENDENTLY (same assets, no extend)...", flush=True)

    seg2_batch = [
        {
            "id": "anime-seg2",
            "prompt": SEG2_PROMPT_ANIME,
            "images": [str(anime_char), str(anime_scene)],  # Same assets as Seg1
            "out": "anime-seg2.mp4"
        },
        {
            "id": "real-seg2",
            "prompt": SEG2_PROMPT_REAL,
            "images": [str(real_scene)],  # Same scene-only for realistic
            "out": "real-seg2.mp4"
        },
    ]

    seg2_json = EXP_DIR / "seg2-batch.json"
    seg2_json.write_text(json.dumps(seg2_batch, ensure_ascii=False, indent=2))

    r = run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
             "--batch", str(seg2_json), "--out-dir", str(OUTPUT)])
    print(f"Seg2 return code: {r.returncode}", flush=True)
    if r.stdout:
        print(r.stdout[-1000:], flush=True)

    gen_log["steps"].append({"step": "seg2-independent", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                             "method": "independent (no video extension)",
                             "prompts": {"anime": SEG2_PROMPT_ANIME, "real": SEG2_PROMPT_REAL}})

    # ── Step 4: Concat + Audio Check ─────────────────────────
    print("\n[STEP 4] Concatenating and checking audio...", flush=True)

    for style in ["anime", "real"]:
        seg1 = OUTPUT / f"{style}-seg1.mp4"
        seg2 = OUTPUT / f"{style}-seg2.mp4"
        final = OUTPUT / f"{style}-final-30s.mp4"

        if seg1.exists() and seg2.exists():
            r = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
                     "--inputs", str(seg1), str(seg2),
                     "--out", str(final), "--check-audio"])
            print(f"{style} concat: rc={r.returncode}", flush=True)
            if r.stdout:
                print(r.stdout[-500:], flush=True)
        else:
            print(f"SKIP {style} concat: seg1={seg1.exists()} seg2={seg2.exists()}", flush=True)

    gen_log["steps"].append({"step": "concat", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")})

    # ── Save generation log ──────────────────────────────────
    log_path = EXP_DIR / "generation-log.json"
    log_path.write_text(json.dumps(gen_log, ensure_ascii=False, indent=2))
    print(f"\nGeneration log: {log_path}", flush=True)

    # ── Summary ──────────────────────────────────────────────
    print("\n" + "="*60, flush=True)
    print("EXP-V7-037 COMPLETE", flush=True)
    for f in sorted(OUTPUT.iterdir()):
        sz = f.stat().st_size // 1024
        print(f"  {f.name} — {sz}KB", flush=True)


if __name__ == "__main__":
    main()
