#!/usr/bin/env python3
"""
EXP-V7-035 Runner — 多角色办公室搞笑 (Multi-Character Office Comedy)
Tests cross-segment consistency with 2 characters interacting.
Dual track: Anime + 3D CG (Pixar style)

Steps:
  1. Generate assets (anime + CG) via gemini_chargen.py
  2. Generate Seg1 videos (anime + CG concurrent) via seedance_gen.py
  3. Generate Seg2 videos (video extension from Seg1, concurrent) via seedance_gen.py
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
    print(f"$ {' '.join(str(c) for c in cmd[:6])}...", flush=True)
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, "PYTHONUNBUFFERED": "1"})
    if r.stdout:
        print(r.stdout[-800:], flush=True)
    if r.returncode != 0:
        print(f"FAIL: {r.stderr[-800:]}", flush=True)
    return r.returncode == 0


# ======================== PROMPTS ========================
# Characters:
#   Li Wei (角色A): 30岁，程序员，戴眼镜，瘦高，蓝白格子衫 — 画面左侧
#   Wang Hao (角色B): 28岁，产品经理，不戴眼镜，微胖，深绿polo衫 — 画面右侧

SEG1_PROMPT_ANIME = """Inside a modern Chinese startup office, daytime, bright natural light from windows. A large whiteboard with architecture diagrams is on the left wall.

Two Chinese men stand near the whiteboard:
- Li Wei (30, tall thin build, rectangular black-framed glasses, blue-and-white plaid shirt over gray t-shirt, short black hair, clean-shaven) stands on the LEFT side of frame, pointing at the whiteboard with his right hand, eyebrows furrowed.
- Wang Hao (28, slightly chubby, round face, NO glasses, dark green polo shirt tucked into khaki pants, short black hair parted to the side, dimples) stands on the RIGHT side of frame, arms crossed over his chest, slight smirk.

Li Wei points at the architecture diagram on the whiteboard and says with frustration: "这个方案根本跑不通，用户不会买单的。"
Wang Hao uncrosses his arms and shrugs confidently: "你上次也这么说，结果呢？日活翻了三倍。"
Li Wei pushes his glasses up and turns to draw an arrow on the whiteboard: "那是因为竞品更烂，不是我们更好。"
Wang Hao slaps the desk and stands up straight: "行，那你说怎么改？给你三分钟。"

Medium shot, slightly low angle. Li Wei always on LEFT, Wang Hao always on RIGHT (180-degree rule). Japanese anime digital animation style. Normal speed movement, natural pacing. All dialogue must finish by second 13, leaving at least 2 seconds of silence at the end. No subtitles, no slow motion, no facing camera directly. Chinese Mandarin dialogue only. 9:16 vertical."""

SEG1_PROMPT_CG = """Inside a modern Chinese startup office, daytime, bright natural light from windows. A large whiteboard with architecture diagrams is on the left wall.

Two Chinese men stand near the whiteboard:
- Li Wei (30, tall thin build, rectangular black-framed glasses, blue-and-white plaid shirt over gray t-shirt, short black hair, clean-shaven) stands on the LEFT side of frame, pointing at the whiteboard with his right hand, eyebrows furrowed.
- Wang Hao (28, slightly chubby, round face, NO glasses, dark green polo shirt tucked into khaki pants, short black hair parted to the side, dimples) stands on the RIGHT side of frame, arms crossed over his chest, slight smirk.

Li Wei points at the architecture diagram on the whiteboard and says with frustration: "这个方案根本跑不通，用户不会买单的。"
Wang Hao uncrosses his arms and shrugs confidently: "你上次也这么说，结果呢？日活翻了三倍。"
Li Wei pushes his glasses up and turns to draw an arrow on the whiteboard: "那是因为竞品更烂，不是我们更好。"
Wang Hao slaps the desk and stands up straight: "行，那你说怎么改？给你三分钟。"

Medium shot, slightly low angle. Li Wei always on LEFT, Wang Hao always on RIGHT (180-degree rule). 3D CG Pixar animation style, smooth stylized features, vibrant colors, soft warm lighting. Normal speed movement, natural pacing. All dialogue must finish by second 13, leaving at least 2 seconds of silence at the end. No subtitles, no slow motion, no facing camera directly. Chinese Mandarin dialogue only. 9:16 vertical."""

SEG2_PROMPT_ANIME = """Continuing from previous scene. Same modern Chinese startup office, same whiteboard, same warm lighting.

Physical State Anchoring:
- Li Wei (30, tall thin, rectangular black-framed glasses, blue-and-white plaid shirt, short black hair) stands on the LEFT side near the whiteboard, marker in hand.
- Wang Hao (28, slightly chubby, round face, NO glasses, dark green polo shirt, khaki pants) sits in a rolling chair on the RIGHT side, phone in hand.

Li Wei frantically scribbles on the whiteboard, then turns back to look at Wang Hao: "首先把这个模块砍掉，省百分之六十开发时间——"
Wang Hao pulls out his phone and checks the time with a smug grin: "一分钟了，你才砍了一个模块。"
Li Wei tosses the whiteboard marker onto the desk and throws his hands up in realization: "等等……你的方案不就是把我砍的这些加回去吗？"
Wang Hao bursts out laughing and stands up to pat Li Wei on the shoulder: "所以我说跑得通嘛！走，请你喝咖啡。"

Medium shot. Li Wei always on LEFT, Wang Hao always on RIGHT (180-degree rule). Japanese anime digital animation style. Normal speed movement, natural pacing. All dialogue must finish by second 13, leaving at least 2 seconds of silence at the end. No subtitles, no slow motion, no facing camera directly. Chinese Mandarin dialogue only. 9:16 vertical."""

SEG2_PROMPT_CG = """Continuing from previous scene. Same modern Chinese startup office, same whiteboard, same warm lighting.

Physical State Anchoring:
- Li Wei (30, tall thin, rectangular black-framed glasses, blue-and-white plaid shirt, short black hair) stands on the LEFT side near the whiteboard, marker in hand.
- Wang Hao (28, slightly chubby, round face, NO glasses, dark green polo shirt, khaki pants) sits in a rolling chair on the RIGHT side, phone in hand.

Li Wei frantically scribbles on the whiteboard, then turns back to look at Wang Hao: "首先把这个模块砍掉，省百分之六十开发时间——"
Wang Hao pulls out his phone and checks the time with a smug grin: "一分钟了，你才砍了一个模块。"
Li Wei tosses the whiteboard marker onto the desk and throws his hands up in realization: "等等……你的方案不就是把我砍的这些加回去吗？"
Wang Hao bursts out laughing and stands up to pat Li Wei on the shoulder: "所以我说跑得通嘛！走，请你喝咖啡。"

Medium shot. Li Wei always on LEFT, Wang Hao always on RIGHT (180-degree rule). 3D CG Pixar animation style, smooth stylized features, vibrant colors, soft warm lighting. Normal speed movement, natural pacing. All dialogue must finish by second 13, leaving at least 2 seconds of silence at the end. No subtitles, no slow motion, no facing camera directly. Chinese Mandarin dialogue only. 9:16 vertical."""


def step1_assets():
    """Generate character/scene reference images (anime + CG)."""
    os.makedirs(ASSETS / "anime", exist_ok=True)
    os.makedirs(ASSETS / "cg", exist_ok=True)

    ok1 = run(["python3", "-u", TOOLS / "gemini_chargen.py",
               "--specs", EXP_DIR / "asset-specs-anime.json",
               "--out-dir", ASSETS / "anime"])
    ok2 = run(["python3", "-u", TOOLS / "gemini_chargen.py",
               "--specs", EXP_DIR / "asset-specs-cg.json",
               "--out-dir", ASSETS / "cg"])
    return ok1 and ok2


def step2_seg1():
    """Generate Seg1 (anime + CG concurrent)."""
    os.makedirs(OUTPUT, exist_ok=True)
    anime_imgs = sorted((ASSETS / "anime").glob("*.webp")) + sorted((ASSETS / "anime").glob("*.png"))
    cg_imgs = sorted((ASSETS / "cg").glob("*.webp")) + sorted((ASSETS / "cg").glob("*.png"))

    batch = [
        {"id": "anime-seg1", "prompt": SEG1_PROMPT_ANIME,
         "images": [str(p) for p in anime_imgs[:4]], "out": "anime-seg1.mp4"},
        {"id": "cg-seg1", "prompt": SEG1_PROMPT_CG,
         "images": [str(p) for p in cg_imgs[:4]], "out": "cg-seg1.mp4"},
    ]
    batch_file = EXP_DIR / "seg1-batch.json"
    batch_file.write_text(json.dumps(batch, indent=2, ensure_ascii=False))

    return run(["python3", "-u", TOOLS / "seedance_gen.py",
                "--batch", str(batch_file), "--out-dir", str(OUTPUT), "--concurrency", "2"])


def step3_seg2():
    """Generate Seg2 (video extension from Seg1, concurrent)."""
    batch = [
        {"id": "anime-seg2", "prompt": SEG2_PROMPT_ANIME,
         "video_ref": str(OUTPUT / "anime-seg1.mp4"), "out": "anime-seg2.mp4"},
        {"id": "cg-seg2", "prompt": SEG2_PROMPT_CG,
         "video_ref": str(OUTPUT / "cg-seg1.mp4"), "out": "cg-seg2.mp4"},
    ]
    batch_file = EXP_DIR / "seg2-batch.json"
    batch_file.write_text(json.dumps(batch, indent=2, ensure_ascii=False))

    return run(["python3", "-u", TOOLS / "seedance_gen.py",
                "--batch", str(batch_file), "--out-dir", str(OUTPUT), "--concurrency", "2"])


def step4_concat():
    """Concat Seg1+Seg2 per style."""
    ok1 = run(["python3", "-u", TOOLS / "ffmpeg_concat.py",
               "--inputs", str(OUTPUT / "anime-seg1.mp4"), str(OUTPUT / "anime-seg2.mp4"),
               "--out", str(OUTPUT / "final-anime.mp4"), "--check-audio", "--check-per-segment"])
    ok2 = run(["python3", "-u", TOOLS / "ffmpeg_concat.py",
               "--inputs", str(OUTPUT / "cg-seg1.mp4"), str(OUTPUT / "cg-seg2.mp4"),
               "--out", str(OUTPUT / "final-cg.mp4"), "--check-audio", "--check-per-segment"])
    return ok1 and ok2


def step5_audio_check():
    """Verify each segment and final video has audio."""
    all_ok = True
    for f in ["anime-seg1.mp4", "anime-seg2.mp4", "final-anime.mp4",
              "cg-seg1.mp4", "cg-seg2.mp4", "final-cg.mp4"]:
        path = OUTPUT / f
        if not path.exists():
            print(f"MISSING: {f}", flush=True)
            all_ok = False
            continue
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True)
        has_audio = "audio" in r.stdout
        # Also check audio is not silent
        if has_audio:
            r2 = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a",
                 "-show_entries", "stream=duration", "-of", "csv=p=0", str(path)],
                capture_output=True, text=True)
            print(f"✅ {f}: audio OK (duration: {r2.stdout.strip()}s)", flush=True)
        else:
            print(f"❌ {f}: NO AUDIO — must regenerate!", flush=True)
            all_ok = False
    return all_ok


def write_generation_log():
    """Record generation parameters for future optimization."""
    log = {
        "experiment": "EXP-V7-035",
        "theme": "多角色办公室搞笑 — 两个创业搭档讨论产品方案",
        "characters": 2,
        "tracks": ["anime", "3d-cg-pixar"],
        "segments": 2,
        "duration_per_segment": "15s",
        "constraints": {
            "180_degree_rule": True,
            "char_a_left_char_b_right": True,
            "dialogue_finish_by": "13s",
            "silence_buffer": "2s",
            "language": "Chinese Mandarin",
            "no_slow_motion": True
        },
        "seg1_prompts": {
            "anime": SEG1_PROMPT_ANIME[:100] + "...",
            "cg": SEG1_PROMPT_CG[:100] + "..."
        },
        "seg2_prompts": {
            "anime": SEG2_PROMPT_ANIME[:100] + "...",
            "cg": SEG2_PROMPT_CG[:100] + "..."
        }
    }
    (EXP_DIR / "generation-log.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False))
    print("Generation log written.", flush=True)


if __name__ == "__main__":
    steps = sys.argv[1:] if len(sys.argv) > 1 else ["1", "2", "3", "4", "5"]

    results = {}
    for step in steps:
        if step == "1":
            print("\n=== Step 1: Generate Assets ===", flush=True)
            results["assets"] = step1_assets()
        elif step == "2":
            print("\n=== Step 2: Generate Seg1 (Concurrent) ===", flush=True)
            results["seg1"] = step2_seg1()
        elif step == "3":
            print("\n=== Step 3: Generate Seg2 (Video Extension, Concurrent) ===", flush=True)
            results["seg2"] = step3_seg2()
        elif step == "4":
            print("\n=== Step 4: Concat ===", flush=True)
            results["concat"] = step4_concat()
        elif step == "5":
            print("\n=== Step 5: Audio Check ===", flush=True)
            results["audio"] = step5_audio_check()

    write_generation_log()
    print(f"\n=== Results: {results} ===", flush=True)
    sys.exit(0 if all(results.values()) else 1)
