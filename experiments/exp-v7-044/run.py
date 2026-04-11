#!/usr/bin/env python3 -u
"""
EXP-V7-044 Runner — 资产锚定 + Extend 组合「深夜食堂的系统」
3 Segments, Direction A (extend), asset upload, anime + realistic dual-track
H-392: asset:// + extend combo → anime ≥ 8.5, realistic ≥ 7.0
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
LINRAN_DESC = "25岁中国女性，马尾辫，格子衬衫外系围裙，温柔笑容，纤细身材"
LINRAN_EN = "25-year-old Chinese woman with ponytail, plaid shirt under apron, warm gentle smile, slender build"

LAOZHANG_DESC = "55岁中国男性出租车司机，络腮胡，满脸皱纹，深灰色夹克配围巾，疲态"
LAOZHANG_EN = "55-year-old Chinese male taxi driver, thick stubble beard, deep wrinkles, dark grey jacket with scarf, fatigued look"

SCENE_DESC = "深夜街角中式小食堂，暖黄灯光，木质吧台，蒸汽缭绕，门口挂着'营业中'的霓虹灯牌，中国风格装饰"
SCENE_EN = "late-night Chinese street-corner eatery, warm yellow lighting, wooden bar counter, steam rising, neon 'OPEN' sign at door, Chinese decor"

ASSET_SPECS = [
    {"name": "林然-anime", "type": "character", "desc": f"{LINRAN_DESC}，动漫风格，眼神温柔带点倔强", "style": "anime"},
    {"name": "老张-anime", "type": "character", "desc": f"{LAOZHANG_DESC}，动漫风格，眼神疲惫但善良", "style": "anime"},
    {"name": "食堂-anime", "type": "scene", "desc": f"{SCENE_DESC}，动漫风格，竖屏构图", "style": "anime"},
    {"name": "林然-realistic", "type": "character", "desc": f"{LINRAN_DESC}，写实风格", "style": "realistic"},
    {"name": "老张-realistic", "type": "character", "desc": f"{LAOZHANG_DESC}，写实风格", "style": "realistic"},
    {"name": "食堂-realistic", "type": "scene", "desc": f"{SCENE_DESC}，写实风格", "style": "realistic"},
]

# ============================================================
# Seg1 — "最后一位客人" (15s)
# ============================================================
SEG1_ANIME = (
    "Anime-style digital animation, high quality, warm cinematic aesthetic. "
    f"A {LINRAN_EN} stands behind the wooden bar counter of a {SCENE_EN}. "
    "She looks up at a wall clock showing 2:47 AM, sighs, continues wiping the counter. "
    "Camera: medium shot, front left 15 degrees, fixed. "
    "Her hand suddenly stops — faint blue glowing text appears on the counter surface like a hologram. "
    "Camera: close-up of her hand, overhead 30 degrees, fixed. "
    "Blue light reflects on her face. She reads the text, eyes widening, mouth slightly open. "
    "Camera: medium close-up, side view, fixed. "
    "Door bell chimes. Door opens, cold wind rushes in. A {LAOZHANG_EN} walks in, rubbing his hands. "
    "Camera: wide shot, door entrance, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[林然]'又是没人来的一晚。再这样下去，这店真撑不住了。' "
    "[林然]'嗯？这什么……五……五万？治愈一颗心？这什么鬼游戏？' "
    "[老张]'小林啊，还没关门呢？来碗热汤面，今晚跑了十二个小时，腰都断了。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

SEG1_REAL = (
    "DSLR cinematic, 35mm lens, warm yellow practical lighting from hanging lamps. Photorealistic, real humans. "
    f"A {LINRAN_EN} stands behind the wooden bar counter of a {SCENE_EN}. "
    "She looks up at a wall clock showing 2:47 AM, sighs, continues wiping the counter. "
    "Camera: medium shot, front left 15 degrees, fixed. "
    "Her hand suddenly stops — faint blue glowing text appears on the counter surface like a hologram. "
    "Camera: close-up of her hand, overhead 30 degrees, fixed. "
    "Blue light reflects on her face. She reads the text, eyes widening, mouth slightly open. "
    "Camera: medium close-up, side view, fixed. "
    "Door bell chimes. Door opens, cold wind rushes in. A {LAOZHANG_EN} walks in, rubbing his hands. "
    "Camera: wide shot, door entrance, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[林然]'又是没人来的一晚。再这样下去，这店真撑不住了。' "
    "[林然]'嗯？这什么……五……五万？治愈一颗心？这什么鬼游戏？' "
    "[老张]'小林啊，还没关门呢？来碗热汤面，今晚跑了十二个小时，腰都断了。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
    "NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG."
)

# ============================================================
# Seg2 — "一碗面的温度" (15s, extend from Seg1)
# ============================================================
SEG2_ANIME = (
    "Anime-style digital animation, continuation of previous scene. "
    f"Same {SCENE_EN}. The {LINRAN_EN} places a steaming bowl of noodles in front of the {LAOZHANG_EN} "
    "who sits at the bar counter. He picks up chopsticks but stares at the noodles, lost in thought. "
    "Camera: medium shot, side view showing both across counter, fixed. "
    "His rough hands tremble slightly holding chopsticks. She silently adds a fried egg to his bowl. "
    "Camera: close-up of his hands, flat angle, fixed. "
    "He slurps a big mouthful of noodles, tears suddenly falling — but mouth still chewing, voice muffled. "
    "Camera: medium close-up, his side face, fixed. "
    "She stands by the stove, back to him. Blue text silently glows on counter: task progress 72 percent. "
    "She clenches her fist, takes a deep breath, turns around. "
    "Camera: medium shot, her by stove, slightly side view, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[老张]'小林，你说人活着图什么？跑了三十年出租，攒的钱全给儿子买房了，现在儿子嫌我老……' "
    "[林然]'张叔，加蛋不加钱。你是我第一个客人，当然有优待。' "
    "[老张]'嗯……好吃。真好吃。好久没人给我做饭了。' "
    "[林然]'张叔……你辛苦了。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

SEG2_REAL = (
    "DSLR cinematic, 35mm lens, warm yellow practical lighting. Photorealistic, real humans. Continuation of previous scene. "
    f"Same {SCENE_EN}. The {LINRAN_EN} places a steaming bowl of noodles in front of the {LAOZHANG_EN} "
    "who sits at the bar counter. He picks up chopsticks but stares at the noodles, lost in thought. "
    "Camera: medium shot, side view showing both across counter, fixed. "
    "His rough hands tremble slightly holding chopsticks. She silently adds a fried egg to his bowl. "
    "Camera: close-up of his hands, flat angle, fixed. "
    "He slurps a big mouthful of noodles, tears suddenly falling — but mouth still chewing, voice muffled. "
    "Camera: medium close-up, his side face, fixed. "
    "She stands by the stove, back to him. Blue text silently glows on counter: task progress 72 percent. "
    "She clenches her fist, takes a deep breath, turns around. "
    "Camera: medium shot, her by stove, slightly side view, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[老张]'小林，你说人活着图什么？跑了三十年出租，攒的钱全给儿子买房了，现在儿子嫌我老……' "
    "[林然]'张叔，加蛋不加钱。你是我第一个客人，当然有优待。' "
    "[老张]'嗯……好吃。真好吃。好久没人给我做饭了。' "
    "[林然]'张叔……你辛苦了。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
    "NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG."
)

# ============================================================
# Seg3 — "系统的真相" (15s, extend from Seg2)
# ============================================================
SEG3_ANIME = (
    "Anime-style digital animation, continuation of previous scene. "
    f"Same {SCENE_EN}, now empty — the old man has left. The {LINRAN_EN} sits alone at the bar, "
    "hands wrapped around a cup of hot tea, apron untied draped on shoulder. "
    "Blue text on counter shows: 'Task complete. Reward: 50000 yuan.' She stares, stunned. "
    "Camera: medium shot, front right 10 degrees, fixed. "
    "She checks her phone. Blue text appears: 'You are not chosen. You are needed.' "
    "Camera: close-up phone screen, overhead 45 degrees, fixed. "
    "She puts down phone, looks at the seat where the old man sat. A napkin with scrawled writing: "
    "'面好吃，谢了小林'. She smirks. "
    "Camera: medium close-up, her side face, fixed. "
    "Wide exterior shot: warm yellow light from the eatery windows, quiet street, dawn light on horizon. "
    "Blue glow flickers inside. "
    "Camera: wide exterior, slight upward 15 degrees, slow pull-back. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[林然]'真……真的到账了？五万块？' "
    "[林然]'被需要的……什么意思？' "
    "[林然]'嘁，这老头……字跟狗爬似的。' "
    "[林然(画外音)]'好吧，系统先生。下一个任务是什么？' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Character never faces camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

SEG3_REAL = (
    "DSLR cinematic, 35mm lens, warm yellow practical lighting. Photorealistic, real human. Continuation of previous scene. "
    f"Same {SCENE_EN}, now empty — the old man has left. The {LINRAN_EN} sits alone at the bar, "
    "hands wrapped around a cup of hot tea, apron untied draped on shoulder. "
    "Blue text on counter shows: 'Task complete. Reward: 50000 yuan.' She stares, stunned. "
    "Camera: medium shot, front right 10 degrees, fixed. "
    "She checks her phone. Blue text appears: 'You are not chosen. You are needed.' "
    "Camera: close-up phone screen, overhead 45 degrees, fixed. "
    "She puts down phone, looks at the seat where the old man sat. A napkin with scrawled writing: "
    "'面好吃，谢了小林'. She smirks. "
    "Camera: medium close-up, her side face, fixed. "
    "Wide exterior shot: warm yellow light from the eatery windows, quiet street, dawn light on horizon. "
    "Blue glow flickers inside. "
    "Camera: wide exterior, slight upward 15 degrees, slow pull-back. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[林然]'真……真的到账了？五万块？' "
    "[林然]'被需要的……什么意思？' "
    "[林然]'嘁，这老头……字跟狗爬似的。' "
    "[林然(画外音)]'好吧，系统先生。下一个任务是什么？' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Character never faces camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
    "NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG."
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
    """Generate 6 reference images (2 chars × 2 styles + 1 scene × 2 styles)."""
    print("\n=== STEP 1: Generate Reference Assets (Gemini) ===", flush=True)
    specs_path = EXP_DIR / "asset_specs.json"
    specs_path.write_text(json.dumps(ASSET_SPECS, indent=2, ensure_ascii=False))
    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "gemini_chargen.py",
        "--specs", specs_path, "--out-dir", ASSETS,
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
                print(f"  ❌ {name}: missing or too small", flush=True)
    else:
        print("  ❌ No manifest.json found!", flush=True)
    return results


def step2_upload_assets(asset_paths):
    """Upload all to Volcano → asset:// URIs."""
    print("\n=== STEP 2: Upload Assets to Volcano Engine ===", flush=True)
    valid = {k: v for k, v in asset_paths.items() if v}
    if not valid:
        print("  ❌ No assets!", flush=True)
        return {}
    paths = list(valid.values())
    names = list(valid.keys())
    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "ark_asset_upload.py",
        "--images", *paths, "--names", *names,
        "--group-name", "exp-v7-044", "--json",
    ], 300)
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
        status = "✅" if name in asset_ids else "❌"
        print(f"  {status} {name}: {asset_ids.get(name, 'FAILED')}", flush=True)
    (EXP_DIR / "asset_ids.json").write_text(json.dumps(asset_ids, indent=2, ensure_ascii=False))
    return asset_ids


def _build_images(asset_ids, style, chars=True):
    """Build image list for a given style."""
    suffix = "anime" if style == "anime" else "realistic"
    keys = []
    if chars:
        keys += [f"林然-{suffix}", f"老张-{suffix}"]
    keys.append(f"食堂-{suffix}")
    return [asset_ids[k] for k in keys if k in asset_ids]


def step3_generate_videos(asset_ids):
    """Generate 3 Segments sequentially (extend chain), anime+realistic concurrent per stage."""
    prompts = {
        "seg1": {"anime": SEG1_ANIME, "real": SEG1_REAL},
        "seg2": {"anime": SEG2_ANIME, "real": SEG2_REAL},
        "seg3": {"anime": SEG3_ANIME, "real": SEG3_REAL},
    }
    results = {}

    for seg_idx, seg_name in enumerate(["seg1", "seg2", "seg3"], 1):
        print(f"\n=== STEP 3.{seg_idx}: Generate {seg_name.upper()} (concurrent anime+realistic) ===", flush=True)
        batch = []
        for style_key, style_label in [("anime", "anime"), ("real", "realistic")]:
            item = {
                "id": f"{style_key}-{seg_name}",
                "prompt": prompts[seg_name][style_key],
                "images": _build_images(asset_ids, style_label),
                "out": str(OUTPUT / f"{style_key}-{seg_name}.mp4"),
            }
            # For seg2/seg3, extend from previous segment
            if seg_idx > 1:
                prev_seg = f"seg{seg_idx - 1}"
                prev_path = results.get(f"{style_key}-{prev_seg}")
                if prev_path:
                    item["video"] = prev_path
                else:
                    print(f"  ⚠️ {style_key}-{seg_name}: no previous segment to extend from, skipping", flush=True)
                    continue
            batch.append(item)

        if not batch:
            print(f"  ❌ No items for {seg_name}!", flush=True)
            continue

        batch_path = EXP_DIR / f"{seg_name}_batch.json"
        batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False))
        rc, out, err = run_cmd([
            "python3", "-u", TOOLS / "seedance_gen.py",
            "--batch", batch_path, "--out-dir", OUTPUT,
        ], 1800)

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
    """Concat 3 segments per style + audio check."""
    print("\n=== STEP 4: Concat + Audio Check ===", flush=True)
    final = {}
    for style in ["anime", "real"]:
        segs = [seg_results.get(f"{style}-seg{i}") for i in range(1, 4)]
        valid_segs = [s for s in segs if s]
        if len(valid_segs) < 2:
            print(f"  ⚠️ {style}: only {len(valid_segs)} segments, need at least 2", flush=True)
            continue

        # Audio check per segment
        all_audio_ok = True
        for i, seg_path in enumerate(valid_segs, 1):
            rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-select_streams", "a",
                                   "-show_entries", "stream=codec_name", "-of", "csv=p=0", seg_path], 10)
            has_audio = rc == 0 and out.strip() != ""
            if has_audio:
                print(f"  ✅ {style}-seg{i}: audio OK ({out.strip()})", flush=True)
            else:
                print(f"  ❌ {style}-seg{i}: NO AUDIO!", flush=True)
                all_audio_ok = False

        out_path = str(OUTPUT / f"{style}-final.mp4")
        rc, out, err = run_cmd([
            "python3", "-u", TOOLS / "ffmpeg_concat.py",
            "--inputs", *valid_segs, "--out", out_path, "--check-audio",
        ], 60)
        if rc == 0 and Path(out_path).exists():
            final[style] = {
                "path": out_path,
                "size_kb": Path(out_path).stat().st_size // 1024,
                "audio_ok": all_audio_ok,
                "seg_count": len(valid_segs),
            }
            print(f"  ✅ {style}-final: {final[style]['size_kb']}KB, {len(valid_segs)} segs, audio={'OK' if all_audio_ok else 'FAIL'}", flush=True)
        else:
            print(f"  ❌ {style}-final: concat failed", flush=True)
    return final


def write_log(asset_ids, seg_results, final):
    log = {
        "experiment": "EXP-V7-044",
        "hypothesis": "H-392: asset + extend combo → anime ≥ 8.5, realistic ≥ 7.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "story": "深夜食堂的系统 — 林然+老张, 都市×系统文×温暖喜剧",
        "method": "Volcano asset upload + video extension (3-seg extend chain) + concurrent dual-track",
        "segments": 3,
        "asset_ids": asset_ids,
        "seg_results": {k: ("OK" if v else "FAIL") for k, v in seg_results.items()},
        "final": final,
    }
    (EXP_DIR / "generation-log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False))


def main():
    keys = load_keys()
    os.environ.setdefault("ARK_API_KEY", keys.get("ark_key") or "")
    os.environ.setdefault("GEMINI_API_KEY", keys.get("gemini_key") or "")
    if keys.get("gemini_base_url"):
        os.environ.setdefault("GEMINI_BASE_URL", keys["gemini_base_url"])
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
    seg_results = step3_generate_videos(asset_ids)
    final = step4_concat_check(seg_results)
    write_log(asset_ids, seg_results, final)

    print("\n" + "=" * 60, flush=True)
    print("EXP-V7-044 SUMMARY", flush=True)
    print("=" * 60, flush=True)
    for style in ["anime", "real"]:
        info = final.get(style, {})
        if info:
            audio = "✅" if info.get("audio_ok") else "⛔NO AUDIO"
            print(f"  {'✅' if info.get('audio_ok') else '⚠️'} {style}: {info['size_kb']}KB, {info['seg_count']} segs, {audio}", flush=True)
        else:
            print(f"  ❌ {style}: FAILED", flush=True)


if __name__ == "__main__":
    main()
