#!/usr/bin/env python3 -u
"""
EXP-V7-038 Runner — Audio Buffer + Cross-Scene Switch Test
Story: 程序员的狂喜 (Coder's Euphoria) — 小李, 28yo programmer
Key tests:
  1. Dialogue ends by 12s (3s silent buffer before segment boundary)
  2. Cross-scene: office → hallway (different but related locations)
  3. Asset upload to Volcano Engine → asset:// URIs for Seedance
  4. Seg2 uses video extension from Seg1 for continuity

Steps:
  1. Generate reference assets (gemini_chargen.py) — anime+realistic concurrent
  2. Upload assets to Volcano Engine (ark_asset_upload.py) → asset:// URIs
  3. Seg1 generation (anime+realistic concurrent)
  4. Seg2 generation via VIDEO EXTENSION from Seg1 (anime+realistic concurrent)
  5. Concat + per-segment audio check
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
# Character + Scene descriptions
# ============================================================
CHAR_DESC_CN = "28岁中国男性程序员，瘦高，短发，戴黑框眼镜，穿蓝白格子衬衫，深色牛仔裤"
CHAR_DESC_EN = "28-year-old Chinese male programmer, slim and tall, short black hair, black-framed glasses, blue-white plaid shirt, dark jeans"

SCENE1_DESC_CN = "现代办公室，白天，明亮日光灯，白色办公桌，两台显示器，办公椅，文件柜"
SCENE1_DESC_EN = "modern office room, daytime, bright fluorescent lights, white desk with two monitors, office chair, filing cabinet"

SCENE2_DESC_CN = "办公楼走廊，白天，白色墙壁，灰色地面，尽头落地窗透进日光"
SCENE2_DESC_EN = "office building hallway, daytime, white walls, grey floor, floor-to-ceiling window at the end with sunlight"

# ============================================================
# Seg1 Prompts — Office interior
# ============================================================
SEG1_PROMPT_ANIME = (
    f"A {CHAR_DESC_EN}, sitting at a white office desk with two monitors in a {SCENE1_DESC_EN}. "
    "He stares at the screen with furrowed brows, hands on keyboard. Suddenly his eyes go wide and he leans forward, "
    "pointing at the screen. He throws both fists in the air with a huge smile, laughing in euphoria. "
    "Then he stands up abruptly, the office chair slides backward and crashes into the filing cabinet with a bang. "
    "Camera: side medium shot → push to medium close-up → pull back to medium shot as he stands. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly. 9:16 vertical."
)

SEG1_PROMPT_REAL = (
    f"A {CHAR_DESC_EN}, sitting at a white office desk with two monitors in a {SCENE1_DESC_EN}. "
    "He stares at the screen with furrowed brows, hands on keyboard. Suddenly his eyes go wide and he leans forward, "
    "pointing at the screen. He throws both fists in the air with a huge smile, laughing in euphoria. "
    "Then he stands up abruptly, the office chair slides backward and crashes into the filing cabinet with a bang. "
    "Camera: side medium shot → push to medium close-up → pull back to medium shot as he stands. "
    "DSLR photograph, 35mm lens, natural office lighting. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# Seg2 Prompts — Hallway (VIDEO EXTENSION from Seg1)
# ============================================================
SEG2_PROMPT_ANIME = (
    f"Continuing from the previous scene: The same {CHAR_DESC_EN} bursts out of an office door into a {SCENE2_DESC_EN}. "
    "He runs excitedly, waving his arms. He crashes into a colleague carrying a coffee cup. "
    "The coffee spills everywhere. He bows apologetically with palms together, looking embarrassed. "
    "The colleague shakes their head and walks away. He stands alone, scratching his head awkwardly with a sheepish grin. "
    "Camera: hallway medium shot → medium shot collision → medium close-up apology → medium shot alone. "
    "Japanese anime digital animation style. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly. 9:16 vertical."
)

SEG2_PROMPT_REAL = (
    f"Continuing from the previous scene: The same {CHAR_DESC_EN} bursts out of an office door into a {SCENE2_DESC_EN}. "
    "He runs excitedly, waving his arms. He crashes into a colleague carrying a coffee cup. "
    "The coffee spills everywhere. He bows apologetically with palms together, looking embarrassed. "
    "The colleague shakes their head and walks away. He stands alone, scratching his head awkwardly with a sheepish grin. "
    "Camera: hallway medium shot → medium shot collision → medium close-up apology → medium shot alone. "
    "DSLR photograph, 35mm lens, natural hallway lighting. Normal speed, natural pacing. "
    "No subtitles, no slow motion, no facing camera directly, no 3D, no CG, no Pixar. 9:16 vertical."
)

# ============================================================
# TTS Dialogue (Chinese) — all dialogue ends by ~12s mark
# ============================================================
DIALOGUE = {
    "seg1": [
        {"speaker": "小李", "text": "这个bug我找了三天……", "start": 0, "end": 3},
        {"speaker": "小李", "text": "等等！", "start": 3, "end": 5},
        {"speaker": "小李", "text": "我找到了！哈哈哈！", "start": 6, "end": 10},
        # Part4 (10-15s): SILENCE — 3s+ buffer
    ],
    "seg2": [
        {"speaker": "小李", "text": "老王！老王！我解了！", "start": 0, "end": 3},
        {"speaker": "小李", "text": "啊——", "start": 3, "end": 5},
        {"speaker": "小李", "text": "那个……对不起……", "start": 6, "end": 10},
        # Part4 (10-15s): SILENCE — 3s+ buffer
    ],
}


def run(cmd, **kwargs):
    """Run subprocess, print status, return result."""
    print(f"\n{'='*60}", flush=True)
    label = ' '.join(str(c) for c in cmd[:6])
    print(f"CMD: {label}...", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
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
        "experiment": "EXP-V7-038",
        "description": "Audio buffer + cross-scene switch test",
        "key_tests": ["3s_audio_buffer", "cross_scene_office_to_hallway", "asset_upload", "video_extension"],
        "steps": [],
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    # ── Step 1: Generate Assets (anime + real concurrent) ────
    print("\n[STEP 1] Generating reference assets...", flush=True)

    asset_specs_anime = [
        {"name": "xiaoli-anime", "type": "character",
         "desc": f"{CHAR_DESC_CN}，站在办公室里，正面半身照",
         "style": "anime"},
        {"name": "office-anime", "type": "scene",
         "desc": SCENE1_DESC_CN, "style": "anime"},
        {"name": "hallway-anime", "type": "scene",
         "desc": SCENE2_DESC_CN, "style": "anime"},
    ]
    asset_specs_real = [
        {"name": "xiaoli-real", "type": "character",
         "desc": f"{CHAR_DESC_CN}，站在办公室里，正面半身照",
         "style": "realistic"},
        {"name": "office-real", "type": "scene",
         "desc": SCENE1_DESC_CN, "style": "realistic"},
        {"name": "hallway-real", "type": "scene",
         "desc": SCENE2_DESC_CN, "style": "realistic"},
    ]

    anime_spec_f = EXP_DIR / "asset-specs-anime.json"
    real_spec_f = EXP_DIR / "asset-specs-real.json"
    anime_spec_f.write_text(json.dumps(asset_specs_anime, ensure_ascii=False, indent=2))
    real_spec_f.write_text(json.dumps(asset_specs_real, ensure_ascii=False, indent=2))

    # Concurrent: anime + real
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(run, ["python3", "-u", str(TOOLS / "gemini_chargen.py"),
                               "--specs", str(anime_spec_f), "--out-dir", str(ASSETS)])
        fr = pool.submit(run, ["python3", "-u", str(TOOLS / "gemini_chargen.py"),
                               "--specs", str(real_spec_f), "--out-dir", str(ASSETS)])
        fa.result()
        fr.result()

    # Verify assets
    expected_assets = [
        "char-xiaoli-anime.webp", "scene-office-anime.webp", "scene-hallway-anime.webp",
        "char-xiaoli-real.webp", "scene-office-real.webp", "scene-hallway-real.webp",
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

    asset_uris = {}  # name → asset:// URI
    for name in expected_assets:
        p = ASSETS / name
        if not p.exists():
            continue
        group_name = f"v7-038-{name.replace('.webp', '')}"
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
        if name in asset_uris:
            print(f"  ✓ {name} → {asset_uris[name][:60]}", flush=True)
        else:
            print(f"  ✗ Upload failed for {name}, will use local path", flush=True)

    gen_log["steps"].append({
        "step": "2_asset_upload",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "asset_uris": asset_uris,
    })

    # Helper: get image ref (prefer asset:// URI, fallback to local path)
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
            "images": [img_ref("char-xiaoli-anime.webp"), img_ref("scene-office-anime.webp")],
            "out": "anime-seg1.mp4",
        },
        {
            "id": "real-seg1",
            "prompt": SEG1_PROMPT_REAL,
            "images": [img_ref("char-xiaoli-real.webp"), img_ref("scene-office-real.webp")],
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
        "asset_refs": {
            "anime": [img_ref("char-xiaoli-anime.webp"), img_ref("scene-office-anime.webp")],
            "real": [img_ref("char-xiaoli-real.webp"), img_ref("scene-office-real.webp")],
        },
    })

    # ── Step 4: Seg2 via VIDEO EXTENSION (anime + real concurrent) ──
    print("\n[STEP 4] Generating Seg2 via video extension (anime + realistic concurrent)...", flush=True)

    seg2_batch = [
        {
            "id": "anime-seg2",
            "prompt": SEG2_PROMPT_ANIME,
            "images": [img_ref("char-xiaoli-anime.webp"), img_ref("scene-hallway-anime.webp")],
            "video": str(OUTPUT / "anime-seg1.mp4"),
            "out": "anime-seg2.mp4",
        },
        {
            "id": "real-seg2",
            "prompt": SEG2_PROMPT_REAL,
            "images": [img_ref("char-xiaoli-real.webp"), img_ref("scene-hallway-real.webp")],
            "video": str(OUTPUT / "real-seg1.mp4"),
            "out": "real-seg2.mp4",
        },
    ]

    seg2_json = EXP_DIR / "seg2-batch.json"
    seg2_json.write_text(json.dumps(seg2_batch, ensure_ascii=False, indent=2))

    # Check seg1 outputs exist before extending
    anime_seg1 = OUTPUT / "anime-seg1.mp4"
    real_seg1 = OUTPUT / "real-seg1.mp4"

    if anime_seg1.exists() and real_seg1.exists():
        r = run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                 "--batch", str(seg2_json), "--out-dir", str(OUTPUT)])
    elif anime_seg1.exists():
        # Only anime seg1 succeeded
        single = [seg2_batch[0]]
        (EXP_DIR / "seg2-batch-anime-only.json").write_text(json.dumps(single, ensure_ascii=False, indent=2))
        r = run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                 "--batch", str(EXP_DIR / "seg2-batch-anime-only.json"), "--out-dir", str(OUTPUT)])
    elif real_seg1.exists():
        single = [seg2_batch[1]]
        (EXP_DIR / "seg2-batch-real-only.json").write_text(json.dumps(single, ensure_ascii=False, indent=2))
        r = run(["python3", "-u", str(TOOLS / "seedance_gen.py"),
                 "--batch", str(EXP_DIR / "seg2-batch-real-only.json"), "--out-dir", str(OUTPUT)])
    else:
        print("⛔ No seg1 outputs exist! Cannot do video extension.", flush=True)

    gen_log["steps"].append({
        "step": "4_seg2_video_extension",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": "video_extension_from_seg1",
        "prompts": {"anime": SEG2_PROMPT_ANIME, "real": SEG2_PROMPT_REAL},
    })

    # ── Step 5: Concat + Per-Segment Audio Check ─────────────
    print("\n[STEP 5] Concatenating and checking audio...", flush=True)

    final_videos = {}
    for style in ["anime", "real"]:
        seg1 = OUTPUT / f"{style}-seg1.mp4"
        seg2 = OUTPUT / f"{style}-seg2.mp4"
        final = OUTPUT / f"{style}-final-30s.mp4"

        if seg1.exists() and seg2.exists():
            r = run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
                     "--inputs", str(seg1), str(seg2),
                     "--out", str(final),
                     "--check-audio", "--check-per-segment"])
            if final.exists():
                final_videos[style] = str(final)
                print(f"  ✓ {style} final: {final.stat().st_size//1024}KB", flush=True)
            else:
                print(f"  ✗ {style} concat failed", flush=True)
        else:
            print(f"  SKIP {style}: seg1={seg1.exists()} seg2={seg2.exists()}", flush=True)

    gen_log["steps"].append({
        "step": "5_concat_audio_check",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "final_videos": final_videos,
    })

    # ── Save generation log ──────────────────────────────────
    gen_log["completed"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    log_path = EXP_DIR / "generation-log.json"
    log_path.write_text(json.dumps(gen_log, ensure_ascii=False, indent=2))

    # ── Summary ──────────────────────────────────────────────
    print(f"\n{'='*60}", flush=True)
    print("EXP-V7-038 COMPLETE", flush=True)
    for f in sorted(OUTPUT.iterdir()):
        sz = f.stat().st_size // 1024
        print(f"  {f.name} — {sz}KB", flush=True)
    print(f"\nGeneration log: {log_path}", flush=True)
    print(f"Dialogue → all lines end by 10s mark, 5s silent buffer", flush=True)


if __name__ == "__main__":
    main()
