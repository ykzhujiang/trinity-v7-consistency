#!/usr/bin/env python3 -u
"""
EXP-V7-042 Runner — 情感密度测试「最后一行代码」
Story: 陈默 (28yo programmer), 创业×系统文, 3 emotional beats in 30s
Key: anime + realistic dual-track, extend mode, asset upload to Volcano
Hypothesis H-391: 3 emotional beats → Sensor ≥ 8.0 (vs V7-038's 7.0)
"""

import json
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

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
# Character + Scene
# ============================================================
CHENMO_DESC = "28岁中国男性程序员，黑色帽衫皱巴巴，黑眼圈严重，胡子拉碴，瘦高"
CHENMO_EN = "28-year-old Chinese male programmer wearing wrinkled black hoodie, severe dark circles under eyes, stubble, tall and thin"

SCENE_DESC = "简陋创业公司办公室，深夜，一张桌一把椅一台电脑，桌上堆满外卖盒和红牛罐，窗外城市夜景"
SCENE_EN = "cramped startup office at night, one desk one chair one computer, desk covered with takeout boxes and Red Bull cans, city night view through window"

# ============================================================
# Asset generation specs (batch mode for gemini_chargen)
# ============================================================
ASSET_SPECS = [
    {"name": "陈默-anime", "type": "character", "desc": f"{CHENMO_DESC}，日漫热血风格，眼神疲惫但有光", "style": "anime"},
    {"name": "陈默-realistic", "type": "character", "desc": f"{CHENMO_DESC}，拟真电影风格，眼神疲惫但有光", "style": "realistic"},
    {"name": "office-anime", "type": "scene", "desc": f"{SCENE_DESC}，日漫风格，竖屏构图", "style": "anime"},
    {"name": "office-realistic", "type": "scene", "desc": f"{SCENE_DESC}，拟真电影风格，竖屏构图", "style": "realistic"},
]

# ============================================================
# Seg1 — "崩溃边缘" (15s, 4 Parts)
# Emotions: 自嘲搞笑 → 震惊
# Dialogue must end before second 12
# ============================================================
SEG1_PROMPT_ANIME = (
    "Japanese anime style digital animation, high quality, hot-blooded anime aesthetic. "
    f"A {CHENMO_EN} is slumped in a chair in a {SCENE_EN}. "
    "He tilts his head back on the chair, an empty Red Bull can slips from his hand and clatters to the floor "
    "where seven or eight other empty cans already lie. "
    "Camera: close-up overhead 15 degrees, fixed. "
    "He suddenly sits upright, grabs his hair with both hands. The screen shows error code. "
    "Camera: medium close-up, right 20 degrees, fixed. "
    "He gives a bitter smile, types one line on keyboard. Screen shows: '// 如果这是最后一行代码，我想写什么？' "
    "Camera: medium shot, right 25 degrees, slow push-in. "
    "He presses Enter. Screen suddenly turns blue, then flashes gold text: "
    "'【创业者操作系统 v1.0】检测到宿主……适配度99.7%。是否激活？' "
    "His eyes go wide, hand frozen above keyboard. "
    "Camera: medium close-up, right 25 degrees, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[陈默]'第三轮融资……又黄了。' "
    "[陈默]'服务器炸了，投资人跑了，合伙人……也跑了。就剩我一个傻子还在写代码。' "
    "[陈默]'写什么呢……写我不认输？哈，太中二了。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Character never faces camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

SEG1_PROMPT_REAL = (
    "DSLR cinematic, 35mm lens, moody warm lighting from monitor only. "
    f"A {CHENMO_EN} is slumped in a chair in a {SCENE_EN}. "
    "He tilts his head back on the chair, an empty Red Bull can slips from his hand and clatters to the floor "
    "where seven or eight other empty cans already lie. "
    "Camera: close-up overhead 15 degrees, fixed. "
    "He suddenly sits upright, grabs his hair with both hands. The screen shows error code. "
    "Camera: medium close-up, right 20 degrees, fixed. "
    "He gives a bitter smile, types one line on keyboard. Screen shows: '// 如果这是最后一行代码，我想写什么？' "
    "Camera: medium shot, right 25 degrees, slow push-in. "
    "He presses Enter. Screen suddenly turns blue, then flashes gold text: "
    "'【创业者操作系统 v1.0】检测到宿主……适配度99.7%。是否激活？' "
    "His eyes go wide, hand frozen above keyboard. "
    "Camera: medium close-up, right 25 degrees, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[陈默]'第三轮融资……又黄了。' "
    "[陈默]'服务器炸了，投资人跑了，合伙人……也跑了。就剩我一个傻子还在写代码。' "
    "[陈默]'写什么呢……写我不认输？哈，太中二了。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Character never faces camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

# ============================================================
# Seg2 — "系统上线" (15s, 4 Parts, extend from Seg1)
# Emotions: 搞笑(银行卡/脱发) → 热血(干就完了)
# ============================================================
SEG2_PROMPT_ANIME = (
    "Japanese anime style digital animation, high quality, continuation of previous scene. "
    f"The same {CHENMO_EN} leans forward, hands on desk, staring at screen. "
    "Office now bathed in golden light from screen. "
    "Screen shows: '宿主：陈默 | 创业失败次数：3 | 剩余现金：2847元 | 隐藏天赋：未解锁'. "
    "His mouth twitches. Camera: medium close-up, right 25 degrees, fixed. "
    "Screen pops up: '首日任务：24小时内获得天使投资。奖励：解锁【看穿谎言】技能。失败惩罚：永久脱发。' "
    "He instinctively touches his hair. Camera: medium close-up, right 20 degrees, fixed. "
    "He stands up, chair falls backward. Golden light on his face. Fist slowly clenches. "
    "Camera: medium shot, right 15 degrees, slow pull-back. "
    "He smirks, eyes sharp. Slams fist on desk — all the empty Red Bull cans jump. "
    "Camera: medium close-up, right 20 degrees, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[陈默]'连我银行卡余额都知道……这什么鬼？' "
    "[陈默]'永久脱发？！你认真的？！' "
    "[陈默]'投资人跑了三轮都没融到……24小时？' "
    "[陈默]'融不到资我也没头发了啊——干就完了！' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Character never faces camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

SEG2_PROMPT_REAL = (
    "DSLR cinematic, 35mm lens, warm golden lighting from monitor, continuation of previous scene. "
    f"The same {CHENMO_EN} leans forward, hands on desk, staring at screen. "
    "Office now bathed in golden light from screen. "
    "Screen shows: '宿主：陈默 | 创业失败次数：3 | 剩余现金：2847元 | 隐藏天赋：未解锁'. "
    "His mouth twitches. Camera: medium close-up, right 25 degrees, fixed. "
    "Screen pops up: '首日任务：24小时内获得天使投资。奖励：解锁【看穿谎言】技能。失败惩罚：永久脱发。' "
    "He instinctively touches his hair. Camera: medium close-up, right 20 degrees, fixed. "
    "He stands up, chair falls backward. Golden light on his face. Fist slowly clenches. "
    "Camera: medium shot, right 15 degrees, slow pull-back. "
    "He smirks, eyes sharp. Slams fist on desk — all the empty Red Bull cans jump. "
    "Camera: medium close-up, right 20 degrees, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[陈默]'连我银行卡余额都知道……这什么鬼？' "
    "[陈默]'永久脱发？！你认真的？！' "
    "[陈默]'投资人跑了三轮都没融到……24小时？' "
    "[陈默]'融不到资我也没头发了啊——干就完了！' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Character never faces camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)


def run_cmd(cmd, timeout=1800):
    print(f"[CMD] {' '.join(str(c) for c in cmd)}", flush=True)
    p = __import__("subprocess").run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)
    if p.stdout:
        print(p.stdout, flush=True)
    if p.stderr:
        print(f"[STDERR] {p.stderr}", flush=True)
    return p.returncode, p.stdout, p.stderr


def step1_generate_assets():
    """Generate character + scene reference images using gemini_chargen batch mode."""
    print("\n=== STEP 1: Generate Reference Assets (Gemini) ===", flush=True)
    specs_path = EXP_DIR / "asset_specs.json"
    specs_path.write_text(json.dumps(ASSET_SPECS, indent=2, ensure_ascii=False))

    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "gemini_chargen.py",
        "--specs", specs_path,
        "--out-dir", ASSETS,
    ], 180)

    # Read manifest written by gemini_chargen
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
    """Upload ALL assets to Volcano Engine → asset:// URIs. No tmpfiles fallback."""
    print("\n=== STEP 2: Upload Assets to Volcano Engine ===", flush=True)
    valid = {k: v for k, v in asset_paths.items() if v}
    if not valid:
        print("  ❌ No assets to upload!", flush=True)
        return {}

    # Collect all paths for batch upload
    paths = list(valid.values())
    names = list(valid.keys())

    cmd = [
        "python3", "-u", TOOLS / "ark_asset_upload.py",
        "--images", *paths,
        "--names", *names,
        "--group-name", "exp-v7-042",
        "--json",
    ]
    rc, out, err = run_cmd(cmd, 300)

    asset_ids = {}
    if rc == 0:
        try:
            # The --json output is the full stdout (multi-line JSON)
            data = json.loads(out.strip())
            if isinstance(data, dict) and "assets" in data:
                for item in data["assets"]:
                    if item.get("status") == "ok" and item.get("asset_uri"):
                        asset_ids[item["name"]] = item["asset_uri"]
            elif isinstance(data, dict):
                asset_ids = {k: v for k, v in data.items() if isinstance(v, str) and v.startswith("asset://")}
        except json.JSONDecodeError:
            # Fallback: parse stderr for [OK] lines
            combined = (out or "") + "\n" + (err or "")
            for line in combined.splitlines():
                if "[OK]" in line and "asset://" in line:
                    # Format: [OK] name: asset://asset-xxx
                    parts = line.split("asset://")
                    if len(parts) >= 2:
                        uri = "asset://" + parts[1].strip()
                        # Extract name between [OK] and :
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


def step3_seg1(asset_ids):
    """Generate Seg1: anime + realistic concurrent."""
    print("\n=== STEP 3: Generate Seg1 (concurrent anime+realistic) ===", flush=True)
    batch = []

    # Anime: char + scene refs
    anime_imgs = [asset_ids[k] for k in ["陈默-anime", "office-anime"] if k in asset_ids]
    batch.append({
        "id": "anime-seg1",
        "prompt": SEG1_PROMPT_ANIME,
        "images": anime_imgs,
        "out": str(OUTPUT / "anime-seg1.mp4"),
    })

    # Realistic: char + scene refs (⛔ MUST include char ref — V7-037 bug fix)
    real_imgs = [asset_ids[k] for k in ["陈默-realistic", "office-realistic"] if k in asset_ids]
    batch.append({
        "id": "real-seg1",
        "prompt": SEG1_PROMPT_REAL,
        "images": real_imgs,
        "out": str(OUTPUT / "real-seg1.mp4"),
    })

    batch_path = EXP_DIR / "seg1_batch.json"
    batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False))

    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "seedance_gen.py",
        "--batch", batch_path,
        "--out-dir", OUTPUT,
    ], 1200)

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


def step4_seg2(seg1_results, asset_ids):
    """Generate Seg2 via VIDEO EXTENSION from Seg1 (concurrent anime+realistic)."""
    print("\n=== STEP 4: Generate Seg2 (extend from Seg1, concurrent) ===", flush=True)
    batch = []

    if seg1_results.get("anime-seg1"):
        anime_imgs = [asset_ids[k] for k in ["陈默-anime", "office-anime"] if k in asset_ids]
        batch.append({
            "id": "anime-seg2",
            "prompt": SEG2_PROMPT_ANIME,
            "video": seg1_results["anime-seg1"],
            "images": anime_imgs,
            "out": str(OUTPUT / "anime-seg2.mp4"),
        })
    if seg1_results.get("real-seg1"):
        real_imgs = [asset_ids[k] for k in ["陈默-realistic", "office-realistic"] if k in asset_ids]
        batch.append({
            "id": "real-seg2",
            "prompt": SEG2_PROMPT_REAL,
            "video": seg1_results["real-seg1"],
            "images": real_imgs,
            "out": str(OUTPUT / "real-seg2.mp4"),
        })

    if not batch:
        print("  ❌ No Seg1 videos to extend!", flush=True)
        return {}

    batch_path = EXP_DIR / "seg2_batch.json"
    batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False))

    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "seedance_gen.py",
        "--batch", batch_path,
        "--out-dir", OUTPUT,
    ], 1800)

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


def step5_concat_check(seg1_results, seg2_results):
    """Concat + per-segment audio check."""
    print("\n=== STEP 5: Concat + Audio Check ===", flush=True)
    final = {}
    for style in ["anime", "real"]:
        seg1 = seg1_results.get(f"{style}-seg1")
        seg2 = seg2_results.get(f"{style}-seg2")
        if not seg1 or not seg2:
            print(f"  ⚠️ {style}: missing segment(s)", flush=True)
            continue

        # Audio check
        all_audio_ok = True
        for seg_label, seg_path in [(f"{style}-seg1", seg1), (f"{style}-seg2", seg2)]:
            rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-select_streams", "a",
                                   "-show_entries", "stream=codec_name", "-of", "csv=p=0", seg_path], 10)
            has_audio = rc == 0 and out.strip() != ""
            if has_audio:
                print(f"  ✅ {seg_label}: audio OK ({out.strip()})", flush=True)
            else:
                print(f"  ❌ {seg_label}: NO AUDIO!", flush=True)
                all_audio_ok = False

        if not all_audio_ok:
            print(f"  ⛔ {style}: audio missing — marking as failed", flush=True)

        # Concat regardless (for review)
        out_path = str(OUTPUT / f"{style}-final.mp4")
        rc, out, err = run_cmd([
            "python3", "-u", TOOLS / "ffmpeg_concat.py",
            "--inputs", seg1, seg2,
            "--out", out_path,
            "--check-audio",
        ], 60)
        if rc == 0 and Path(out_path).exists():
            final[style] = {"path": out_path, "size_kb": Path(out_path).stat().st_size // 1024, "audio_ok": all_audio_ok}
            print(f"  ✅ {style}-final: {final[style]['size_kb']}KB", flush=True)
        else:
            print(f"  ❌ {style}-final: concat failed", flush=True)
    return final


def write_log(asset_ids, seg1, seg2, final):
    log = {
        "experiment": "EXP-V7-042",
        "hypothesis": "H-391: 3 emotional beats → Sensor ≥ 8.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "story": "最后一行代码 — 陈默 28yo programmer, 创业×系统文",
        "method": "Volcano asset upload + video extension (extend mode) + concurrent dual-track",
        "asset_ids": asset_ids,
        "seg1_prompts": {"anime": SEG1_PROMPT_ANIME[:100] + "...", "realistic": SEG1_PROMPT_REAL[:100] + "..."},
        "seg2_prompts": {"anime": SEG2_PROMPT_ANIME[:100] + "...", "realistic": SEG2_PROMPT_REAL[:100] + "..."},
        "seg1": {k: ("OK" if v else "FAIL") for k, v in seg1.items()},
        "seg2": {k: ("OK" if v else "FAIL") for k, v in seg2.items()},
        "final": {k: v for k, v in final.items()},
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

    # Load Volcano keys
    import json as _json
    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    if cfg_path.exists():
        cfg = _json.loads(cfg_path.read_text())
        try:
            sv = cfg["skills"]["entries"]["seedance-video"]["env"]
            os.environ.setdefault("VOLCANO_ACCESS_KEY", sv.get("VOLCANO_ACCESS_KEY", ""))
            os.environ.setdefault("VOLCANO_ACCESS_SECRET", sv.get("VOLCANO_ACCESS_SECRET", ""))
        except (KeyError, TypeError):
            pass

    asset_paths = step1_generate_assets()
    asset_ids = step2_upload_assets(asset_paths)
    seg1 = step3_seg1(asset_ids)
    seg2 = step4_seg2(seg1, asset_ids)
    final = step5_concat_check(seg1, seg2)
    write_log(asset_ids, seg1, seg2, final)

    print("\n" + "=" * 60, flush=True)
    print("EXP-V7-042 SUMMARY", flush=True)
    print("=" * 60, flush=True)
    for style in ["anime", "real"]:
        info = final.get(style, {})
        if info:
            audio_status = "✅" if info.get("audio_ok") else "⛔NO AUDIO"
            print(f"  {'✅' if info.get('audio_ok') else '⚠️'} {style}: {info['size_kb']}KB {audio_status}", flush=True)
        else:
            print(f"  ❌ {style}: FAILED", flush=True)


if __name__ == "__main__":
    main()
