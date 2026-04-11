#!/usr/bin/env python3 -u
"""
EXP-V7-039 Runner — 3-Segment Cross-Scene Single-Character Consistency Test
Story: 都市逆袭 — 林浩, 28yo programmer
Key tests:
  1. 3 segments × 3 different scenes (网吧→天台→出租屋)
  2. Same character description + reference image across all 3 segments
  3. Video extension chain: Seg1 → Seg2 → Seg3
  4. Dialogue ends by ~12s (3s buffer per segment)
  5. Anime + Realistic dual track, concurrent where possible

Scenes:
  Seg1: 深夜网吧 — 接电话得知公司倒闭
  Seg2: 城市天台 — 白天，下定决心重来
  Seg3: 简陋出租屋 — 夜晚，开始写新项目
"""

import json
import os
import subprocess
import sys
import time
import concurrent.futures
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
EXP_DIR = Path(__file__).resolve().parent
ASSETS = EXP_DIR / "assets"
OUTPUT = EXP_DIR / "output"

# ============================================================
# Character Description (identical across ALL segments)
# ============================================================
CHAR_DESC_CN = "28岁中国男性程序员林浩，瘦高，短发，戴黑框眼镜，穿灰色连帽卫衣配牛仔裤"
CHAR_DESC_EN = "28-year-old Chinese male programmer Lin Hao, slim and tall, short black hair, black-framed glasses, wearing grey hoodie and jeans"

# ============================================================
# Scene Descriptions
# ============================================================
SCENE1_DESC_CN = "深夜网吧，昏暗灯光，成排电脑桌，蓝色屏幕光映照"
SCENE1_DESC_EN = "late-night internet cafe, dim lighting, rows of computer desks, blue screen glow"

SCENE2_DESC_CN = "城市天台，白天，阳光明媚，可以俯瞰城市建筑群，铁栏杆"
SCENE2_DESC_EN = "city rooftop, daytime, bright sunlight, overlooking urban buildings, iron railing"

SCENE3_DESC_CN = "简陋出租屋，夜晚，台灯微光，旧木桌，单人床，墙壁斑驳"
SCENE3_DESC_EN = "small shabby rental room, nighttime, dim desk lamp, old wooden desk, single bed, peeling walls"

# ============================================================
# Seg1 Prompts — 深夜网吧
# ============================================================
SEG1_PROMPT_ANIME = (
    f"A {CHAR_DESC_EN}, sitting at a computer desk in a {SCENE1_DESC_EN}. "
    "He stares at the screen typing code. His phone buzzes on the desk. He picks it up and answers. "
    "His expression shifts from focused to shocked — mouth slightly open, hand freezes. "
    "He slowly puts the phone down, stares blankly ahead. Then he takes a deep breath, "
    "shuts down the computer calmly, stands up and walks toward the exit. "
    "Camera: side medium shot → medium close-up on phone call → pull back as he stands. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly. 9:16 vertical."
)

SEG1_PROMPT_REAL = (
    f"A {CHAR_DESC_EN}, sitting at a computer desk in a {SCENE1_DESC_EN}. "
    "He stares at the screen typing code. His phone buzzes on the desk. He picks it up and answers. "
    "His expression shifts from focused to shocked — mouth slightly open, hand freezes. "
    "He slowly puts the phone down, stares blankly ahead. Then he takes a deep breath, "
    "shuts down the computer calmly, stands up and walks toward the exit. "
    "Camera: side medium shot → medium close-up on phone call → pull back as he stands. "
    "DSLR photograph, 35mm lens, natural dim lighting. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# Seg2 Prompts — 城市天台 (VIDEO EXTENSION from Seg1)
# ============================================================
SEG2_PROMPT_ANIME = (
    f"Continuing from the previous scene: The same {CHAR_DESC_EN} stands on a {SCENE2_DESC_EN}. "
    "Wind blows through his hoodie. He grips the iron railing, looking out at the city below. "
    "He mutters to himself, face showing frustration. He pulls out his phone, glances at the screen. "
    "He shoves it back in his pocket, lifts his head, and a slight determined smile forms. "
    "Camera: behind medium shot → side medium close-up → front medium shot as he looks up. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly. 9:16 vertical."
)

SEG2_PROMPT_REAL = (
    f"Continuing from the previous scene: The same {CHAR_DESC_EN} stands on a {SCENE2_DESC_EN}. "
    "Wind blows through his hoodie. He grips the iron railing, looking out at the city below. "
    "He mutters to himself, face showing frustration. He pulls out his phone, glances at the screen. "
    "He shoves it back in his pocket, lifts his head, and a slight determined smile forms. "
    "Camera: behind medium shot → side medium close-up → front medium shot as he looks up. "
    "DSLR photograph, 35mm lens, bright natural daylight. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# Seg3 Prompts — 简陋出租屋 (VIDEO EXTENSION from Seg2)
# ============================================================
SEG3_PROMPT_ANIME = (
    f"Continuing from the previous scene: The same {CHAR_DESC_EN} pushes open the door of a {SCENE3_DESC_EN}. "
    "He drops his backpack on the bed, sits at the old wooden desk. He opens a laptop, "
    "the screen light illuminates his tired face. He starts typing, brow furrowed in concentration. "
    "He rubs his eyes but keeps coding, a faint smile forming as something works. "
    "Camera: doorway medium shot → over-shoulder close-up on laptop → side medium close-up face. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly. 9:16 vertical."
)

SEG3_PROMPT_REAL = (
    f"Continuing from the previous scene: The same {CHAR_DESC_EN} pushes open the door of a {SCENE3_DESC_EN}. "
    "He drops his backpack on the bed, sits at the old wooden desk. He opens a laptop, "
    "the screen light illuminates his tired face. He starts typing, brow furrowed in concentration. "
    "He rubs his eyes but keeps coding, a faint smile forming as something works. "
    "Camera: doorway medium shot → over-shoulder close-up on laptop → side medium close-up face. "
    "DSLR photograph, 35mm lens, dim warm desk lamp light. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# TTS Dialogue (Chinese) — all dialogue ends by ~12s mark
# ============================================================
DIALOGUE = {
    "seg1": [
        {"speaker": "林浩", "text": "喂？什么意思公司没了？", "start": 3, "end": 7},
        # Parts 3-4 (7-15s): Silent — shock, stands, walks out
    ],
    "seg2": [
        {"speaker": "林浩", "text": "三年，全搭进去了。", "start": 2, "end": 6},
        {"speaker": "林浩", "text": "那就重来。", "start": 9, "end": 12},
        # Part 4 (12-15s): Silent buffer
    ],
    "seg3": [
        {"speaker": "林浩", "text": "这个架构不对，得换。", "start": 5, "end": 10},
        # Parts 3-4 (10-15s): Silent — keeps coding, smile
    ],
}


def run(cmd, **kwargs):
    """Run subprocess, print status, return result."""
    print(f"\n{'='*60}", flush=True)
    label = ' '.join(str(c) for c in cmd[:6])
    print(f"CMD: {label}...", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, **kwargs)
    elapsed = time.time() - t0
    print(f"RC: {r.returncode} ({elapsed:.0f}s)", flush=True)
    if r.returncode != 0:
        print(f"STDERR: {r.stderr[-500:]}", flush=True)
    if r.stdout:
        print(r.stdout[-800:], flush=True)
    return r


def main():
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(OUTPUT, exist_ok=True)

    gen_log = {
        "experiment": "EXP-V7-039",
        "description": "3-segment cross-scene single-character consistency test",
        "key_tests": ["3_segments", "cross_scene_3_locations", "character_consistency",
                       "video_extension_chain", "audio_buffer"],
        "character": CHAR_DESC_CN,
        "scenes": [SCENE1_DESC_CN, SCENE2_DESC_CN, SCENE3_DESC_CN],
        "steps": [],
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    # ── Step 1: Generate Assets (anime + real concurrent) ────
    print("\n[STEP 1] Generating reference assets...", flush=True)

    asset_specs_anime = [
        {"name": "linhao-anime", "type": "character",
         "desc": f"{CHAR_DESC_CN}，站立正面半身照，深色背景",
         "style": "anime"},
        {"name": "wangba-anime", "type": "scene",
         "desc": SCENE1_DESC_CN, "style": "anime"},
        {"name": "rooftop-anime", "type": "scene",
         "desc": SCENE2_DESC_CN, "style": "anime"},
        {"name": "rental-anime", "type": "scene",
         "desc": SCENE3_DESC_CN, "style": "anime"},
    ]
    asset_specs_real = [
        {"name": "linhao-real", "type": "character",
         "desc": f"{CHAR_DESC_CN}，站立正面半身照，深色背景",
         "style": "realistic"},
        {"name": "wangba-real", "type": "scene",
         "desc": SCENE1_DESC_CN, "style": "realistic"},
        {"name": "rooftop-real", "type": "scene",
         "desc": SCENE2_DESC_CN, "style": "realistic"},
        {"name": "rental-real", "type": "scene",
         "desc": SCENE3_DESC_CN, "style": "realistic"},
    ]

    anime_spec_f = EXP_DIR / "asset-specs-anime.json"
    real_spec_f = EXP_DIR / "asset-specs-real.json"
    anime_spec_f.write_text(json.dumps(asset_specs_anime, ensure_ascii=False, indent=2))
    real_spec_f.write_text(json.dumps(asset_specs_real, ensure_ascii=False, indent=2))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(run, ["python3", "-u", str(TOOLS / "gemini_chargen.py"),
                               "--specs", str(anime_spec_f), "--out-dir", str(ASSETS)])
        fr = pool.submit(run, ["python3", "-u", str(TOOLS / "gemini_chargen.py"),
                               "--specs", str(real_spec_f), "--out-dir", str(ASSETS)])
        fa.result()
        fr.result()

    expected_assets = [
        "char-linhao-anime.webp", "scene-wangba-anime.webp",
        "scene-rooftop-anime.webp", "scene-rental-anime.webp",
        "char-linhao-real.webp", "scene-wangba-real.webp",
        "scene-rooftop-real.webp", "scene-rental-real.webp",
    ]
    asset_status = {}
    for name in expected_assets:
        p = ASSETS / name
        if p.exists():
            sz = p.stat().st_size
            print(f"  ✓ {name} ({sz//1024}KB)", flush=True)
            asset_status[name] = "ok"
        else:
            print(f"  ✗ MISSING: {name}", flush=True)
            asset_status[name] = "missing"

    gen_log["steps"].append({
        "step": "1_asset_generation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "assets": asset_status,
    })

    # ── Step 2: Upload Assets to Volcano Engine ──────────────
    print("\n[STEP 2] Uploading assets to Volcano Engine...", flush=True)

    asset_uris = {}
    for name in expected_assets:
        p = ASSETS / name
        if not p.exists():
            continue
        group_name = f"v7-039-{name.replace('.webp', '')}"
        r = run(["python3", "-u", str(TOOLS / "ark_asset_upload.py"),
                 "--image", str(p),
                 "--group-name", group_name,
                 "--name", name.replace(".webp", ""),
                 "--json",
                 "--repo-dir", os.path.expanduser("~/trinity-v7-consistency")])
        if r.returncode == 0 and r.stdout.strip():
            try:
                result = json.loads(r.stdout.strip().split('\n')[-1])
                if isinstance(result, list) and len(result) > 0:
                    asset_uris[name] = result[0].get("asset_uri", "")
                elif isinstance(result, dict):
                    asset_uris[name] = result.get("asset_uri", "")
            except json.JSONDecodeError:
                pass
        if name in asset_uris and asset_uris[name]:
            print(f"  ✓ {name} → {asset_uris[name][:60]}", flush=True)
        else:
            print(f"  ✗ Upload failed for {name}, will use local path", flush=True)

    gen_log["steps"].append({
        "step": "2_asset_upload",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "asset_uris": asset_uris,
    })

    def img_ref(name):
        if name in asset_uris and asset_uris[name]:
            return asset_uris[name]
        return str(ASSETS / name)

    # ── Step 3: Seg1 (anime + realistic concurrent) ──────────
    print("\n[STEP 3] Generating Seg1 (anime + realistic concurrent)...", flush=True)

    seg1_batch = [
        {
            "id": "anime-seg1",
            "prompt": SEG1_PROMPT_ANIME,
            "images": [img_ref("char-linhao-anime.webp"), img_ref("scene-wangba-anime.webp")],
            "out": "anime-seg1.mp4",
        },
        {
            "id": "real-seg1",
            "prompt": SEG1_PROMPT_REAL,
            "images": [img_ref("char-linhao-real.webp"), img_ref("scene-wangba-real.webp")],
            "out": "real-seg1.mp4",
        },
    ]

    seg1_json = EXP_DIR / "seg1-batch.json"
    seg1_json.write_text(json.dumps(seg1_batch, ensure_ascii=False, indent=2))

    r = run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
             "--batch", str(seg1_json), "--out-dir", str(OUTPUT)])

    gen_log["steps"].append({
        "step": "3_seg1_generation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "prompts": {"anime": SEG1_PROMPT_ANIME, "real": SEG1_PROMPT_REAL},
    })

    # ── Step 4: Seg2 via VIDEO EXTENSION from Seg1 ───────────
    print("\n[STEP 4] Generating Seg2 via video extension from Seg1...", flush=True)

    seg2_items = []
    if (OUTPUT / "anime-seg1.mp4").exists():
        seg2_items.append({
            "id": "anime-seg2",
            "prompt": SEG2_PROMPT_ANIME,
            "images": [img_ref("char-linhao-anime.webp"), img_ref("scene-rooftop-anime.webp")],
            "video": str(OUTPUT / "anime-seg1.mp4"),
            "out": "anime-seg2.mp4",
        })
    if (OUTPUT / "real-seg1.mp4").exists():
        seg2_items.append({
            "id": "real-seg2",
            "prompt": SEG2_PROMPT_REAL,
            "images": [img_ref("char-linhao-real.webp"), img_ref("scene-rooftop-real.webp")],
            "video": str(OUTPUT / "real-seg1.mp4"),
            "out": "real-seg2.mp4",
        })

    if seg2_items:
        seg2_json = EXP_DIR / "seg2-batch.json"
        seg2_json.write_text(json.dumps(seg2_items, ensure_ascii=False, indent=2))
        r = run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                 "--batch", str(seg2_json), "--out-dir", str(OUTPUT)])
    else:
        print("⛔ No seg1 outputs! Cannot extend to seg2.", flush=True)

    gen_log["steps"].append({
        "step": "4_seg2_video_extension",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": "video_extension_from_seg1",
    })

    # ── Step 5: Seg3 via VIDEO EXTENSION from Seg2 ───────────
    print("\n[STEP 5] Generating Seg3 via video extension from Seg2...", flush=True)

    seg3_items = []
    if (OUTPUT / "anime-seg2.mp4").exists():
        seg3_items.append({
            "id": "anime-seg3",
            "prompt": SEG3_PROMPT_ANIME,
            "images": [img_ref("char-linhao-anime.webp"), img_ref("scene-rental-anime.webp")],
            "video": str(OUTPUT / "anime-seg2.mp4"),
            "out": "anime-seg3.mp4",
        })
    if (OUTPUT / "real-seg2.mp4").exists():
        seg3_items.append({
            "id": "real-seg3",
            "prompt": SEG3_PROMPT_REAL,
            "images": [img_ref("char-linhao-real.webp"), img_ref("scene-rental-real.webp")],
            "video": str(OUTPUT / "real-seg2.mp4"),
            "out": "real-seg3.mp4",
        })

    if seg3_items:
        seg3_json = EXP_DIR / "seg3-batch.json"
        seg3_json.write_text(json.dumps(seg3_items, ensure_ascii=False, indent=2))
        r = run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                 "--batch", str(seg3_json), "--out-dir", str(OUTPUT)])
    else:
        print("⛔ No seg2 outputs! Cannot extend to seg3.", flush=True)

    gen_log["steps"].append({
        "step": "5_seg3_video_extension",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": "video_extension_from_seg2",
    })

    # ── Step 6: Concat + Per-Segment Audio Check ─────────────
    print("\n[STEP 6] Concatenating and checking audio...", flush=True)

    final_videos = {}
    for style in ["anime", "real"]:
        seg1 = OUTPUT / f"{style}-seg1.mp4"
        seg2 = OUTPUT / f"{style}-seg2.mp4"
        seg3 = OUTPUT / f"{style}-seg3.mp4"
        final = OUTPUT / f"{style}-final-45s.mp4"

        segs_exist = [s for s in [seg1, seg2, seg3] if s.exists()]
        if len(segs_exist) >= 2:
            r = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
                     "--inputs"] + [str(s) for s in segs_exist] + [
                     "--out", str(final),
                     "--check-audio", "--check-per-segment"])
            if final.exists():
                final_videos[style] = str(final)
                print(f"  ✓ {style} final: {final.stat().st_size//1024}KB ({len(segs_exist)} segs)", flush=True)
            else:
                print(f"  ✗ {style} concat failed", flush=True)
        else:
            print(f"  SKIP {style}: only {len(segs_exist)} segs available", flush=True)

    gen_log["steps"].append({
        "step": "6_concat_audio_check",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "final_videos": final_videos,
    })

    # ── Save generation log ──────────────────────────────────
    gen_log["completed"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    log_path = EXP_DIR / "generation-log.json"
    log_path.write_text(json.dumps(gen_log, ensure_ascii=False, indent=2))

    # ── Summary ──────────────────────────────────────────────
    print(f"\n{'='*60}", flush=True)
    print("EXP-V7-039 COMPLETE", flush=True)
    for f in sorted(OUTPUT.iterdir()):
        sz = f.stat().st_size // 1024
        print(f"  {f.name} — {sz}KB", flush=True)
    print(f"\nGeneration log: {log_path}", flush=True)


if __name__ == "__main__":
    main()
