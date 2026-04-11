#!/usr/bin/env python3 -u
"""
EXP-V7-043 Runner — B2 跨场景独立拼接验证「深夜食堂的神秘客人」
Direction B2: Independent generation per segment (NOT video extension), then concat.
Anime only (single track). Cross-scene: 深夜食堂 → 办公室回忆.
Hypothesis H-392: Cross-scene splice acceptable (≥6.0) because audience expects scene change.
"""

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
TOOLS = REPO / "tools"
EXP_DIR = Path(__file__).resolve().parent
ASSETS = EXP_DIR / "assets"
OUTPUT = EXP_DIR / "output"
ASSETS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

# ============================================================
# Characters
# ============================================================
MYSTERY_MAN_DESC = "30岁中国男性，黑色风衣，面容疲惫但眼神锐利，短黑发微乱"
MYSTERY_MAN_EN = "30-year-old Chinese East Asian man in black trench coat, fatigued face but sharp piercing eyes, short messy black hair"

LIMEI_DESC = "45岁中国女性，围裙，短发利落，温暖笑容，深夜食堂老板娘"
LIMEI_EN = "45-year-old Chinese East Asian woman wearing an apron, neat short hair, warm smile, late-night eatery owner"

BOSS_DESC = "50岁中国男性，灰发，严肃表情，穿深色西装，公司高管气质"
BOSS_EN = "50-year-old Chinese East Asian man with grey hair, stern expression, wearing dark formal suit, corporate executive demeanor"

# ============================================================
# Asset specs for gemini_chargen
# ============================================================
ASSET_SPECS = [
    {"name": "mystery-man-coat-anime", "type": "character",
     "desc": f"{MYSTERY_MAN_DESC}，日漫风格，站在雨中，湿漉漉", "style": "anime"},
    {"name": "mystery-man-suit-anime", "type": "character",
     "desc": "30岁中国男性，穿合身西装，短黑发整齐，精神状态好，日漫风格", "style": "anime"},
    {"name": "limei-anime", "type": "character",
     "desc": f"{LIMEI_DESC}，日漫风格，温暖灯光下", "style": "anime"},
    {"name": "boss-anime", "type": "character",
     "desc": f"{BOSS_DESC}，日漫风格，办公室场景", "style": "anime"},
    {"name": "izakaya-anime", "type": "scene",
     "desc": "深夜小巷居酒屋内部，吧台+几张座位，暖黄灯光，竖屏构图，雨夜，日漫风格", "style": "anime"},
    {"name": "office-anime", "type": "scene",
     "desc": "现代办公室，落地窗，城市天际线，白天阳光，大桌子，竖屏构图，日漫风格", "style": "anime"},
]

# ============================================================
# Seg1 — "夜雨中的食堂" (15s) — 独立生成
# ============================================================
SEG1_PROMPT = (
    "Japanese anime style digital animation, high quality, warm cinematic lighting. "
    f"A rainy night scene in a tiny old Japanese-style izakaya called '深夜食堂'. "
    f"Inside the izakaya, warm yellow light, a wooden bar counter with a few stools. "
    f"{LIMEI_EN} stands behind the bar counter wiping a glass. "
    f"The door opens, {MYSTERY_MAN_EN} enters from the rain, water dripping from his coat hem. "
    "Li Mei looks up at him. Camera: medium shot from bar counter towards door, fixed. "
    "The man walks to the bar and sits down, removes his coat hood, revealing his fatigued face. "
    "He looks around — he is the only customer. "
    "Camera: medium close-up, side view 45 degrees, fixed. "
    "Li Mei gives a gentle smile, turns around and starts cooking noodles. "
    "Steam rises from the pot. "
    "Camera: close-up Li Mei's side profile plus steam from pot, fixed. "
    "Dialogue (Chinese Mandarin, all dialogue must finish before second 12): "
    "[李梅]'下这么大雨，快进来坐。' "
    "[男子]'来碗……最简单的阳春面。' "
    "[李梅]'阳春面啊……上一个点这碗面的人，也是你这个表情。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera directly. 180-degree rule. "
    "No subtitles, no slow motion. 9:16 vertical."
)

# ============================================================
# Seg2 — "回忆中的办公室" (15s) — 独立生成 (NOT extend)
# Different scene, different lighting, 3 days earlier
# ============================================================
SEG2_PROMPT = (
    "Japanese anime style digital animation, high quality, bright daylight office lighting. "
    f"A bright modern office with floor-to-ceiling windows showing city skyline, daytime. "
    f"A large executive desk dominates the room. "
    f"The same {MYSTERY_MAN_EN.replace('black trench coat', 'fitted dark suit').replace('fatigued face but sharp piercing eyes, short messy black hair', 'neat short black hair, determined expression, standing tensely')} "
    "stands in front of the desk, holding a document file. "
    f"{BOSS_EN} sits behind the desk, then stands up, both hands on desk, leaning forward intimidatingly. "
    "Camera: medium shot from behind boss's shoulder looking at the man, fixed. "
    "The man places the document on the desk, fingers pressing the edge. "
    "Camera: close-up overhead on hands and document, fixed. "
    "The boss leans forward aggressively, imposing presence. "
    "Camera: low angle looking up at boss, fixed, intimidating composition. "
    "The man steps back, takes a deep breath, looks out the window at the skyline (NOT at camera). "
    "Camera: medium shot, side view, slow push-in to man's side profile close-up. "
    "Dialogue (Chinese Mandarin, all dialogue must finish before second 12): "
    "[老板]'你确定要举报？你知道这意味着什么。' "
    "[男子]'这些账目……不能再瞒了。' "
    "[老板]'你在这个公司十年了。房子、车子、股权。你要全放弃？' "
    "[男子]'有些东西……比这些值钱。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera directly. 180-degree rule. "
    "No subtitles, no slow motion. 9:16 vertical."
)


def run_cmd(cmd, timeout=1800):
    print(f"[CMD] {' '.join(str(c) for c in cmd)}", flush=True)
    import subprocess
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)
    if p.stdout:
        print(p.stdout, flush=True)
    if p.stderr:
        print(f"[STDERR] {p.stderr}", flush=True)
    return p.returncode, p.stdout, p.stderr


def step1_generate_assets():
    """Generate character + scene reference images using gemini_chargen."""
    print("\n=== STEP 1: Generate Reference Assets (Gemini) ===", flush=True)
    specs_path = EXP_DIR / "asset_specs.json"
    specs_path.write_text(json.dumps(ASSET_SPECS, indent=2, ensure_ascii=False))

    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "gemini_chargen.py",
        "--specs", specs_path,
        "--out-dir", ASSETS,
    ], 300)

    manifest_path = ASSETS / "manifest.json"
    results = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for name, path in manifest.items():
            if Path(path).exists() and Path(path).stat().st_size > 1000:
                results[name] = path
                print(f"  ✅ {name}: {path} ({Path(path).stat().st_size // 1024}KB)", flush=True)
            else:
                results[name] = None
                print(f"  ❌ {name}: file missing or too small", flush=True)
    else:
        print("  ❌ No manifest.json found!", flush=True)
    return results


def step2_upload_assets(asset_paths):
    """Upload ALL assets to Volcano Engine → asset:// URIs."""
    print("\n=== STEP 2: Upload Assets to Volcano Engine ===", flush=True)
    valid = {k: v for k, v in asset_paths.items() if v}
    if not valid:
        print("  ❌ No assets to upload!", flush=True)
        return {}

    paths = list(valid.values())
    names = list(valid.keys())

    cmd = [
        "python3", "-u", TOOLS / "ark_asset_upload.py",
        "--images", *paths,
        "--names", *names,
        "--group-name", "exp-v7-043",
        "--json",
    ]
    rc, out, err = run_cmd(cmd, 300)

    asset_ids = {}
    if rc == 0:
        try:
            data = json.loads(out.strip())
            if isinstance(data, dict) and "assets" in data:
                for item in data["assets"]:
                    if item.get("status") == "ok" and item.get("asset_uri"):
                        asset_ids[item["name"]] = item["asset_uri"]
            elif isinstance(data, dict):
                asset_ids = {k: v for k, v in data.items() if isinstance(v, str) and v.startswith("asset://")}
        except json.JSONDecodeError:
            combined = (out or "") + "\n" + (err or "")
            for line in combined.splitlines():
                if "[OK]" in line and "asset://" in line:
                    parts = line.split("asset://")
                    if len(parts) >= 2:
                        uri = "asset://" + parts[1].strip()
                        name_part = line.split("[OK]")[1].split(":")[0].strip()
                        if name_part in names:
                            asset_ids[name_part] = uri

    for name in names:
        if name in asset_ids:
            print(f"  ✅ {name}: {asset_ids[name]}", flush=True)
        else:
            print(f"  ❌ {name}: upload failed!", flush=True)

    ids_path = EXP_DIR / "asset_ids.json"
    ids_path.write_text(json.dumps(asset_ids, indent=2, ensure_ascii=False))
    return asset_ids


def step3_generate_videos(asset_ids):
    """Generate Seg1 + Seg2 INDEPENDENTLY (B2 direction — NOT extend)."""
    print("\n=== STEP 3: Generate Seg1 + Seg2 (independent, NOT extend) ===", flush=True)

    # Seg1 images: mystery-man-coat, limei, izakaya scene
    seg1_imgs = [asset_ids[k] for k in ["mystery-man-coat-anime", "limei-anime", "izakaya-anime"] if k in asset_ids]
    # Seg2 images: mystery-man-suit, boss, office scene
    seg2_imgs = [asset_ids[k] for k in ["mystery-man-suit-anime", "boss-anime", "office-anime"] if k in asset_ids]

    batch = [
        {
            "id": "anime-seg1",
            "prompt": SEG1_PROMPT,
            "images": seg1_imgs,
            "out": str(OUTPUT / "anime-seg1.mp4"),
        },
        {
            "id": "anime-seg2",
            "prompt": SEG2_PROMPT,
            "images": seg2_imgs,
            "out": str(OUTPUT / "anime-seg2.mp4"),
            # ⛔ NO "video" key — this is independent generation, NOT extend
        },
    ]

    batch_path = EXP_DIR / "seg_batch.json"
    batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False))

    # Both can run concurrently since neither depends on the other
    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "seedance_gen.py",
        "--batch", batch_path,
        "--out-dir", OUTPUT,
    ], 1200)

    # Check for content moderation blocks
    combined = (out or "") + "\n" + (err or "")
    if any(kw in combined for kw in ["ContentModeration", "PrivacyInformation", "内容审核", "content_filter"]):
        print("\n⚠️ CONTENT MODERATION BLOCK! Abandoning experiment per standing order.", flush=True)
        return None  # Signal to abandon

    results = {}
    for item in batch:
        p = Path(item["out"])
        if p.exists() and p.stat().st_size > 10000:
            results[item["id"]] = str(p)
            print(f"  ✅ {item['id']}: {p.stat().st_size // 1024}KB", flush=True)
        else:
            results[item["id"]] = None
            print(f"  ❌ {item['id']}: failed", flush=True)
    return results


def step4_concat_check(seg_results):
    """Concat + per-segment audio check."""
    print("\n=== STEP 4: Concat + Audio Check ===", flush=True)
    seg1 = seg_results.get("anime-seg1")
    seg2 = seg_results.get("anime-seg2")

    if not seg1 or not seg2:
        print("  ❌ Missing segment(s), cannot concat!", flush=True)
        return None

    # Audio check each segment
    all_audio_ok = True
    for label, path in [("anime-seg1", seg1), ("anime-seg2", seg2)]:
        rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-select_streams", "a",
                               "-show_entries", "stream=codec_name", "-of", "csv=p=0", path], 10)
        has_audio = rc == 0 and out.strip() != ""
        if has_audio:
            print(f"  ✅ {label}: audio OK ({out.strip()})", flush=True)
        else:
            print(f"  ❌ {label}: NO AUDIO!", flush=True)
            all_audio_ok = False

    # Concat
    final_path = str(OUTPUT / "anime-final.mp4")
    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "ffmpeg_concat.py",
        "--inputs", seg1, seg2,
        "--out", final_path,
        "--check-audio",
    ], 60)

    if rc == 0 and Path(final_path).exists():
        size_kb = Path(final_path).stat().st_size // 1024
        print(f"  ✅ anime-final: {size_kb}KB, audio_ok={all_audio_ok}", flush=True)
        return {"path": final_path, "size_kb": size_kb, "audio_ok": all_audio_ok}
    else:
        print(f"  ❌ Concat failed!", flush=True)
        return None


def write_log(asset_ids, seg_results, final):
    log = {
        "experiment": "EXP-V7-043",
        "hypothesis": "H-392: Cross-scene B2 splice ≥ 6.0 with asset upload",
        "direction": "B2 — independent generation per segment, then concat",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "story": "深夜食堂的神秘客人 — 跨场景(居酒屋→办公室回忆)",
        "method": "Volcano asset upload + independent gen (NOT extend) + anime only",
        "asset_ids": asset_ids,
        "seg1_prompt": SEG1_PROMPT[:200] + "...",
        "seg2_prompt": SEG2_PROMPT[:200] + "...",
        "seg_results": {k: ("OK" if v else "FAIL") for k, v in (seg_results or {}).items()},
        "final": final,
    }
    log_path = EXP_DIR / "generation-log.json"
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"\n📝 Log: {log_path}", flush=True)


def main():
    keys = load_keys()
    os.environ.setdefault("ARK_API_KEY", keys.get("ark_key") or "")
    os.environ.setdefault("GEMINI_API_KEY", keys.get("gemini_key") or "")
    if keys.get("gemini_base_url"):
        os.environ.setdefault("GEMINI_BASE_URL", keys["gemini_base_url"])

    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        try:
            sv = cfg["skills"]["entries"]["seedance-video"]["env"]
            os.environ.setdefault("VOLCANO_ACCESS_KEY", sv.get("VOLCANO_ACCESS_KEY", ""))
            os.environ.setdefault("VOLCANO_ACCESS_SECRET", sv.get("VOLCANO_ACCESS_SECRET", ""))
        except (KeyError, TypeError):
            pass

    asset_paths = step1_generate_assets()
    asset_ids = step2_upload_assets(asset_paths)

    if not asset_ids:
        print("⛔ No assets uploaded — cannot proceed!", flush=True)
        write_log({}, None, None)
        return

    seg_results = step3_generate_videos(asset_ids)
    if seg_results is None:
        # Content moderation block — abandon
        write_log(asset_ids, None, None)
        return

    final = step4_concat_check(seg_results)
    write_log(asset_ids, seg_results, final)

    print("\n" + "=" * 60, flush=True)
    print("EXP-V7-043 SUMMARY (B2 Cross-Scene)", flush=True)
    print("=" * 60, flush=True)
    if final:
        audio_status = "✅" if final.get("audio_ok") else "⛔NO AUDIO"
        print(f"  {'✅' if final.get('audio_ok') else '⚠️'} anime: {final['size_kb']}KB {audio_status}", flush=True)
    else:
        print(f"  ❌ anime: FAILED", flush=True)


if __name__ == "__main__":
    main()
