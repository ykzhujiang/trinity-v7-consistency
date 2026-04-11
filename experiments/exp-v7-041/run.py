#!/usr/bin/env python3 -u
"""
EXP-V7-041 Runner — Anime+Realistic 双Segment, 资产锚定 + extend模式
Story: 创业者成长系统 — 陈磊, 25yo programmer, system activation
Key tests:
  1. Asset upload → asset:// URIs for character reference
  2. Seg2 via VIDEO EXTENSION (extend from Seg1 last frame) — not independent concat
  3. Dual track: anime + realistic (concurrent within each stage)
  4. 4 Parts per Segment, 中文台词, 9:16 vertical
  5. Dialogue must end before second 12 (1s buffer at end)

Steps:
  1. Generate reference assets (gemini_chargen.py) — anime+realistic character+scene
  2. Upload assets (ark_asset_upload.py) → asset:// URIs
  3. Seg1 generation (anime+realistic concurrent)
  4. Seg2 generation (anime+realistic concurrent) — EXTEND from Seg1
  5. Concat + per-segment audio check
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
EXP_DIR = Path(__file__).resolve().parent
ASSETS = EXP_DIR / "assets"
OUTPUT = EXP_DIR / "output"
ASSETS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

# ============================================================
# Character + Scene descriptions
# ============================================================
CHENLEI_CN = "25岁中国男性程序员，黑色卫衣，戴黑框眼镜，疲惫表情，乱蓬蓬的短发"
CHENLEI_EN = "25-year-old Chinese male programmer wearing black hoodie, black-rimmed glasses, tired expression, messy short hair"

SCENE_CN = "深夜创业公司小办公室，暗淡灯光，只有电脑屏幕发光，桌上散落着外卖盒和咖啡杯"
SCENE_EN = "late-night startup office, dim lighting, only computer screens glowing, takeout boxes and coffee cups scattered on desk"

SCENE2_EN = "same startup office now illuminated by blue holographic system panel light, revealing more of the cluttered workspace"

# ============================================================
# Seg1 Prompts — "系统激活"
# 4 Parts: (1) 趴键盘 (2) 抬头看面板 (3) 面板文字 (4) 伸手触碰
# Dialogue ends before second 12
# ============================================================
SEG1_PROMPT_ANIME = (
    f"Japanese anime style digital animation, high quality. "
    f"A {CHENLEI_EN} is slumped over his keyboard in a {SCENE_EN}. "
    "A spilled coffee cup lies next to him. "
    "Camera: medium shot from right 30 degrees, slowly pushing in. "
    "He lifts his head and rubs his eyes. A translucent blue holographic panel materializes in front of him. "
    "Camera shifts to medium close-up, right 20 degrees. "
    "Text scrolls across the panel surface. His expression changes from confusion to wide-eyed surprise. "
    "He reaches out tentatively to touch the panel, which bursts with bright light. "
    "Camera at right 15 degrees. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[陈磊]'又加班到凌晨三点……' [陈磊]'等等，这什么东西？' [陈磊]'创业者成长系统？点击激活？' "
    "All speech in Chinese Mandarin. Normal speed, natural pacing. "
    "Character never faces camera directly. 180-degree rule respected. "
    "No subtitles, no slow motion. 9:16 vertical."
)

SEG1_PROMPT_REAL = (
    f"DSLR photograph style, 35mm lens, cinematic lighting. "
    f"A {CHENLEI_EN} is slumped over his keyboard in a {SCENE_EN}. "
    "A spilled coffee cup lies next to him. "
    "Camera: medium shot from right 30 degrees, slowly pushing in. "
    "He lifts his head and rubs his eyes. A translucent blue holographic panel materializes in front of him. "
    "Camera shifts to medium close-up, right 20 degrees. "
    "Text scrolls across the panel surface. His expression changes from confusion to wide-eyed surprise. "
    "He reaches out tentatively to touch the panel, which bursts with bright light. "
    "Camera at right 15 degrees. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[陈磊]'又加班到凌晨三点……' [陈磊]'等等，这什么东西？' [陈磊]'创业者成长系统？点击激活？' "
    "All speech in Chinese Mandarin. Normal speed, natural pacing. "
    "Character never faces camera directly. 180-degree rule respected. "
    "No subtitles, no slow motion. 9:16 vertical."
)

# ============================================================
# Seg2 Prompts — "首次任务" (EXTEND mode from Seg1)
# 4 Parts: (1) 站起来看面板 (2) 看任务苦笑 (3) 挠头看计划书 (4) 深吸气握拳
# ============================================================
SEG2_PROMPT_ANIME = (
    f"Japanese anime style digital animation, high quality. "
    f"Continuation of previous scene. The same {CHENLEI_EN} stands up from his chair. "
    f"The office is now {SCENE2_EN}. "
    "The blue holographic panel follows his movement, now displaying a task list. "
    "Camera: medium shot from right 15 degrees. "
    "He reads the panel showing 'First Task: Convince an investor in 3 minutes' and grimaces with a bitter smile. "
    "Camera shifts to right 20 degrees. He scratches his head and glances at a business plan document on the desk. "
    "He takes a deep breath and clenches his fist, expression turning determined. "
    "Camera at right 25 degrees. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[陈磊]'首个任务……说服投资人？' [陈磊]'我连PPT都没做完啊！' [陈磊]'不过……万一是真的呢？干了！' "
    "All speech in Chinese Mandarin. Normal speed, natural pacing. "
    "Character never faces camera directly. 180-degree rule respected. "
    "No subtitles, no slow motion. 9:16 vertical."
)

SEG2_PROMPT_REAL = (
    f"DSLR photograph style, 35mm lens, cinematic lighting. "
    f"Continuation of previous scene. The same {CHENLEI_EN} stands up from his chair. "
    f"The office is now {SCENE2_EN}. "
    "The blue holographic panel follows his movement, now displaying a task list. "
    "Camera: medium shot from right 15 degrees. "
    "He reads the panel showing 'First Task: Convince an investor in 3 minutes' and grimaces with a bitter smile. "
    "Camera shifts to right 20 degrees. He scratches his head and glances at a business plan document on the desk. "
    "He takes a deep breath and clenches his fist, expression turning determined. "
    "Camera at right 25 degrees. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[陈磊]'首个任务……说服投资人？' [陈磊]'我连PPT都没做完啊！' [陈磊]'不过……万一是真的呢？干了！' "
    "All speech in Chinese Mandarin. Normal speed, natural pacing. "
    "Character never faces camera directly. 180-degree rule respected. "
    "No subtitles, no slow motion. 9:16 vertical."
)

# ============================================================
# Asset generation specs
# ============================================================
ASSET_SPECS = [
    {"id": "chenlei-anime", "style": "anime", "prompt": f"Character reference sheet, full body, anime style. {CHENLEI_EN}. Clean white background. Front view and 3/4 view."},
    {"id": "chenlei-real", "style": "realistic", "prompt": f"Character reference photo, full body, realistic. {CHENLEI_EN}. Clean white background. Front view and 3/4 view."},
    {"id": "scene-anime", "style": "anime", "prompt": f"Background art, anime style. {SCENE_EN}. No characters. Wide establishing shot. 9:16 vertical composition."},
    {"id": "scene-real", "style": "realistic", "prompt": f"Background photograph, realistic. {SCENE_EN}. No characters. Wide establishing shot. 9:16 vertical composition."},
]


def run_cmd(cmd, timeout=1800):
    """Run a command and return (returncode, stdout, stderr)."""
    print(f"[CMD] {' '.join(cmd)}", flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.stdout:
        print(p.stdout, flush=True)
    if p.stderr:
        print(f"[STDERR] {p.stderr}", flush=True)
    return p.returncode, p.stdout, p.stderr


def step1_generate_assets():
    """Generate character + scene reference images using gemini_chargen."""
    print("\n=== STEP 1: Generate Reference Assets ===", flush=True)
    specs_path = EXP_DIR / "asset_specs.json"
    specs_path.write_text(json.dumps(ASSET_SPECS, indent=2))

    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for spec in ASSET_SPECS:
            out_path = ASSETS / f"{spec['id']}.webp"
            cmd = [
                "python3", "-u", str(TOOLS / "gemini_chargen.py"),
                "--prompt", spec["prompt"],
                "--out", str(out_path),
                "--width", "600",
            ]
            futures[pool.submit(run_cmd, cmd, 120)] = spec["id"]

        for f in as_completed(futures):
            sid = futures[f]
            rc, out, err = f.result()
            img_path = ASSETS / f"{sid}.webp"
            if rc == 0 and img_path.exists():
                print(f"  ✅ {sid}: {img_path} ({img_path.stat().st_size // 1024}KB)", flush=True)
                results[sid] = str(img_path)
            else:
                print(f"  ❌ {sid}: generation failed (rc={rc})", flush=True)
                results[sid] = None
    return results


def step2_upload_assets(asset_paths):
    """Upload assets via ark_asset_upload.py → asset:// URIs."""
    print("\n=== STEP 2: Upload Assets ===", flush=True)
    asset_ids = {}
    valid_paths = {k: v for k, v in asset_paths.items() if v}

    if not valid_paths:
        print("  ⚠️ No assets to upload, will proceed text-only", flush=True)
        return asset_ids

    # Try upload
    for aid, apath in valid_paths.items():
        cmd = [
            "python3", "-u", str(TOOLS / "ark_asset_upload.py"),
            "--file", apath,
        ]
        rc, out, err = run_cmd(cmd, 60)
        if rc == 0 and "asset://" in out:
            # Extract asset:// URI from output
            for line in out.splitlines():
                if "asset://" in line:
                    uri = line.strip().split()[-1] if line.strip() else ""
                    if uri.startswith("asset://"):
                        asset_ids[aid] = uri
                        print(f"  ✅ {aid}: {uri}", flush=True)
                        break
        else:
            print(f"  ⚠️ {aid}: upload failed, will use tmpfiles fallback", flush=True)

    # Fallback: tmpfiles.org for any that failed
    for aid, apath in valid_paths.items():
        if aid not in asset_ids:
            cmd = ["curl", "-s", "-F", f"file=@{apath}", "https://tmpfiles.org/api/v1/upload"]
            rc, out, err = run_cmd(cmd, 30)
            if rc == 0:
                try:
                    resp = json.loads(out)
                    url = resp.get("data", {}).get("url", "")
                    if url:
                        # Convert tmpfiles.org URL to direct link
                        direct = url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                        asset_ids[aid] = direct
                        print(f"  ✅ {aid} (tmpfiles): {direct}", flush=True)
                except:
                    print(f"  ❌ {aid}: tmpfiles upload also failed", flush=True)

    ids_path = EXP_DIR / "asset_ids.json"
    ids_path.write_text(json.dumps(asset_ids, indent=2))
    return asset_ids


def step3_generate_seg1(asset_ids):
    """Generate Seg1 for anime + realistic concurrently."""
    print("\n=== STEP 3: Generate Seg1 (anime+realistic concurrent) ===", flush=True)

    batch = []
    # Anime
    anime_images = [asset_ids.get("chenlei-anime", ""), asset_ids.get("scene-anime", "")]
    anime_images = [x for x in anime_images if x]
    batch.append({
        "id": "anime-seg1",
        "prompt": SEG1_PROMPT_ANIME,
        "images": anime_images,
        "out": str(OUTPUT / "anime-seg1.mp4"),
    })
    # Realistic
    real_images = [asset_ids.get("chenlei-real", ""), asset_ids.get("scene-real", "")]
    real_images = [x for x in real_images if x]
    batch.append({
        "id": "real-seg1",
        "prompt": SEG1_PROMPT_REAL,
        "images": real_images,
        "out": str(OUTPUT / "real-seg1.mp4"),
    })

    batch_path = EXP_DIR / "seg1_batch.json"
    batch_path.write_text(json.dumps(batch, indent=2))

    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--batch", str(batch_path),
        "--out-dir", str(OUTPUT),
    ]
    rc, out, err = run_cmd(cmd, 1200)
    results = {}
    for item in batch:
        p = Path(item["out"])
        if p.exists() and p.stat().st_size > 10000:
            results[item["id"]] = str(p)
            print(f"  ✅ {item['id']}: {p.stat().st_size // 1024}KB", flush=True)
        else:
            print(f"  ❌ {item['id']}: not generated or too small", flush=True)
            results[item["id"]] = None
    return results


def step4_generate_seg2(seg1_results, asset_ids):
    """Generate Seg2 via VIDEO EXTENSION from Seg1."""
    print("\n=== STEP 4: Generate Seg2 (extend from Seg1, concurrent) ===", flush=True)

    batch = []
    if seg1_results.get("anime-seg1"):
        batch.append({
            "id": "anime-seg2",
            "prompt": SEG2_PROMPT_ANIME,
            "video": seg1_results["anime-seg1"],
            "images": [v for k, v in asset_ids.items() if "anime" in k and v],
            "out": str(OUTPUT / "anime-seg2.mp4"),
        })
    if seg1_results.get("real-seg1"):
        batch.append({
            "id": "real-seg2",
            "prompt": SEG2_PROMPT_REAL,
            "video": seg1_results["real-seg1"],
            "images": [v for k, v in asset_ids.items() if "real" in k and v],
            "out": str(OUTPUT / "real-seg2.mp4"),
        })

    if not batch:
        print("  ❌ No Seg1 videos to extend from!", flush=True)
        return {}

    batch_path = EXP_DIR / "seg2_batch.json"
    batch_path.write_text(json.dumps(batch, indent=2))

    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--batch", str(batch_path),
        "--out-dir", str(OUTPUT),
    ]
    rc, out, err = run_cmd(cmd, 1800)  # Longer timeout for extend
    results = {}
    for item in batch:
        p = Path(item["out"])
        if p.exists() and p.stat().st_size > 10000:
            results[item["id"]] = str(p)
            print(f"  ✅ {item['id']}: {p.stat().st_size // 1024}KB", flush=True)
        else:
            print(f"  ❌ {item['id']}: not generated or too small", flush=True)
            results[item["id"]] = None
    return results


def step5_concat_and_check(seg1_results, seg2_results):
    """Concat segments and check audio per segment."""
    print("\n=== STEP 5: Concat + Audio Check ===", flush=True)
    final = {}

    for style in ["anime", "real"]:
        seg1 = seg1_results.get(f"{style}-seg1")
        seg2 = seg2_results.get(f"{style}-seg2")
        if not seg1 or not seg2:
            print(f"  ⚠️ {style}: missing segment(s), skip concat", flush=True)
            continue

        # Audio check per segment
        for seg_name, seg_path in [(f"{style}-seg1", seg1), (f"{style}-seg2", seg2)]:
            rc, out, _ = run_cmd([
                "ffprobe", "-v", "error", "-select_streams", "a",
                "-show_entries", "stream=codec_name", "-of", "csv=p=0",
                seg_path
            ], 10)
            has_audio = rc == 0 and out.strip() != ""
            if has_audio:
                print(f"  ✅ {seg_name}: audio present ({out.strip()})", flush=True)
            else:
                print(f"  ❌ {seg_name}: NO AUDIO — cannot deliver!", flush=True)

        # Concat
        out_path = str(OUTPUT / f"{style}-final.mp4")
        cmd = [
            "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
            "--inputs", seg1, seg2,
            "--out", out_path,
        ]
        rc, out, err = run_cmd(cmd, 60)
        if rc == 0 and Path(out_path).exists():
            print(f"  ✅ {style}-final: {Path(out_path).stat().st_size // 1024}KB", flush=True)
            final[style] = out_path
        else:
            print(f"  ❌ {style}-final: concat failed", flush=True)

    return final


def write_generation_log(asset_ids, seg1_results, seg2_results, final_results):
    """Record generation metadata."""
    log = {
        "experiment": "EXP-V7-041",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "story": "创业者成长系统 — 陈磊, 25yo programmer",
        "method": "asset upload + video extension (extend mode)",
        "asset_ids": asset_ids,
        "seg1": {k: ("OK" if v else "FAIL") for k, v in seg1_results.items()},
        "seg2": {k: ("OK" if v else "FAIL") for k, v in seg2_results.items()},
        "final": {k: ("OK" if v else "FAIL") for k, v in final_results.items()},
    }
    log_path = EXP_DIR / "generation-log.json"
    log_path.write_text(json.dumps(log, indent=2))
    print(f"\n  📝 Log: {log_path}", flush=True)


def main():
    keys = load_keys()
    os.environ.setdefault("ARK_API_KEY", keys.get("ARK_API_KEY", ""))
    os.environ.setdefault("GEMINI_API_KEY", keys.get("GEMINI_API_KEY", ""))

    # Step 1: Generate assets
    asset_paths = step1_generate_assets()

    # Step 2: Upload assets
    asset_ids = step2_upload_assets(asset_paths)

    # Step 3: Generate Seg1
    seg1_results = step3_generate_seg1(asset_ids)

    # Step 4: Generate Seg2 (extend)
    seg2_results = step4_generate_seg2(seg1_results, asset_ids)

    # Step 5: Concat + audio check
    final_results = step5_concat_and_check(seg1_results, seg2_results)

    # Log
    write_generation_log(asset_ids, seg1_results, seg2_results, final_results)

    # Summary
    print("\n" + "=" * 60, flush=True)
    print("EXP-V7-041 SUMMARY", flush=True)
    print("=" * 60, flush=True)
    for style in ["anime", "real"]:
        status = "✅" if style in final_results else "❌"
        print(f"  {status} {style}: {'delivered' if style in final_results else 'FAILED'}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    main()
