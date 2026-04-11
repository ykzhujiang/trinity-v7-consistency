#!/usr/bin/env python3 -u
"""
EXP-V7-046 Runner — 系统逆袭：面馆传奇 (Realistic Only, 3-Seg Extend Chain)
H-127: DSLR realistic with indoor/outdoor scene prompts → consistent ≥ 8.0/10
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
LIFENG_DESC = "30岁中国男性程序员，圆脸，戴黑框眼镜，穿蓝白格子衫，普通人长相，略微发福"
LIFENG_EN = "30-year-old Chinese male programmer, round face, black-framed glasses, blue-white plaid shirt, average build, slightly chubby"

ZHOUZONG_DESC = "45岁中国男性互联网高管，秃顶，啤酒肚，穿深色名牌西装，金属框眼镜，气势凌人"
ZHOUZONG_EN = "45-year-old Chinese male tech executive, bald on top, beer belly, dark designer suit, metal-frame glasses, imposing demeanor"

LOBBY_DESC = "[INDOOR] 高级写字楼大堂，玻璃幕墙，大理石地面，金属旋转门，现代简约风格，白色LED灯光，安保人员桌台"
LOBBY_EN = "Interior of a modern high-rise office building lobby with glass curtain walls, marble floor, metal revolving door, modern minimalist design, white LED lighting, security desk"

NOODLE_OLD_DESC = "[INDOOR] 10平米破旧街边小面馆，塑料桌椅，油腻墙壁，褪色手写菜单，暖黄白炽灯，蒸汽从厨房飘出，门口有折叠招牌"
NOODLE_OLD_EN = "Interior of a tiny 10-sqm run-down Chinese noodle shop, plastic tables and chairs, greasy walls, faded handwritten menu board, warm incandescent bulb, steam from kitchen, folding sign at door"

NOODLE_NEW_DESC = "[INDOOR] 翻新后的面馆，新招牌写着'峰味面馆'，明亮暖色灯光，木质桌椅，排队人群从门口延伸到街上，干净整洁"
NOODLE_NEW_EN = "Interior of a renovated Chinese noodle shop named 'Feng Wei Noodles', bright warm lighting, wooden tables and chairs, queue of customers extending from door, clean and tidy"

ASSET_SPECS = [
    {"name": "李峰", "type": "character", "desc": f"{LIFENG_DESC}，写实风格", "style": "realistic"},
    {"name": "周总", "type": "character", "desc": f"{ZHOUZONG_DESC}，写实风格", "style": "realistic"},
    {"name": "写字楼大堂", "type": "scene", "desc": f"{LOBBY_DESC}", "style": "realistic"},
    {"name": "旧面馆", "type": "scene", "desc": f"{NOODLE_OLD_DESC}", "style": "realistic"},
    {"name": "新面馆", "type": "scene", "desc": f"{NOODLE_NEW_DESC}", "style": "realistic"},
]

# ============================================================
# Seg1 — 被裁员 + 系统觉醒 (15s)
# Location: [INDOOR] 写字楼大堂
# ============================================================
SEG1_PROMPT = (
    "DSLR cinematic, 35mm lens, cool white LED office lighting. Photorealistic, real humans. "
    f"Interior of a modern office building lobby. A {LIFENG_EN} is carrying a cardboard box, being escorted out by a security guard. "
    "Items spill from the box — a small cactus pot falls and breaks on the marble floor. "
    "Camera: medium shot, side angle 20 degrees, fixed. "
    f"He crouches to pick up items. His phone buzzes, screen glows blue. "
    "Camera: close-up of phone screen in his hand, overhead 30 degrees, fixed. "
    "His face shows tear tracks, expression shifts from sadness to confusion as he reads the phone. "
    "Camera: medium close-up, side face, fixed. He is NOT looking at camera. "
    "He gives a bitter laugh, puts the cactus back in the box, touches his hair anxiously. "
    "Camera: medium shot, slight low angle, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[李峰]'裁员优化……感谢我为公司做出的贡献？呵。' "
    "[李峰]'嗯？什么……商业系统已激活？当前余额237元？' "
    "[李峰]'237块钱创业？系统你开什么玩笑。' "
    "[李峰]'永久脱发？！不不不，我接，我接还不行吗！' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
    "NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG."
)

# ============================================================
# Seg2 — 街边小面馆 系统第一课 (15s, extend from Seg1)
# Location: [INDOOR] 旧面馆
# ============================================================
SEG2_PROMPT = (
    "DSLR cinematic, 35mm lens, warm incandescent lighting from hanging bulb. Photorealistic, real humans. Continuation of previous scene. "
    f"Interior of a tiny run-down Chinese noodle shop. The {LIFENG_EN} sits at a plastic table in the corner, "
    "a steaming bowl of plain noodles in front of him, phone on table glowing blue. "
    "A middle-aged Chinese woman (noodle shop owner, 50s, apron, kind face) brings the bowl over. "
    "Camera: medium shot, side view, fixed. "
    "He looks at his phone calculating. Phone screen shows system analysis text in blue. His eyes light up. "
    "Camera: close-up of phone screen, flat angle, fixed. "
    "He looks around the shop — camera pans slowly across empty plastic chairs, faded menu, people walking past the door without entering. "
    "Camera: slow horizontal pan, eye level, fixed. "
    "The owner wipes a table, sighing. He puts down his chopsticks, corner of mouth curving up slightly. "
    "Camera: two-shot medium, side angle showing both, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[李峰]'一碗面8块，还剩229。' "
    "[李峰]'日均客流42人……隐藏价值四颗星？这面馆有搞头？' "
    "[老板娘]'年轻人，吃完早点走吧，我这店下个月就关了。' "
    "[李峰]'老板娘，这店……我要接手。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
    "NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG."
)

# ============================================================
# Seg3 — 逆袭初现 + 悬念 (15s, extend from Seg2)
# Location: [INDOOR] 新面馆
# ============================================================
SEG3_PROMPT = (
    "DSLR cinematic, 35mm lens, bright warm lighting. Photorealistic, real humans. Continuation of previous scene. "
    f"Interior of a renovated bustling Chinese noodle shop. The {LIFENG_EN} now wears an apron, confidently working behind the counter. "
    "The shop has a new sign, wooden furniture, and a long queue of customers. "
    "Camera: wide shot showing busy interior, slight high angle, fixed. "
    f"A familiar figure in the queue — the {ZHOUZONG_EN}, sweating, squeezing among customers. "
    "Camera: medium shot picking him out in the crowd, fixed. "
    "The bald executive reaches the counter, looks up, sees the programmer. His expression shifts from anticipation to shock. "
    "The programmer smiles calmly. "
    "Camera: over-shoulder shot from behind programmer, showing executive's shocked face, fixed. "
    "The programmer turns back to work. His phone buzzes — new system task appears. He shakes his head with a smile. "
    "Camera: close-up of phone screen, then medium close-up of his side face smiling, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[李峰]'72小时——余额127350元。任务完成。' "
    "[李峰]'这不是……周总？' "
    "[李峰]'周总您好。一碗招牌红烧牛肉面，28元。' "
    "[李峰]'开10家分店？行吧，系统先生。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
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
    """Generate reference images: 2 chars + 3 scenes (realistic only)."""
    print("\n=== STEP 1: Generate Reference Assets (Gemini, Realistic DSLR) ===", flush=True)
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
        "--group-name", "exp-v7-046", "--json",
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


def step3_generate_videos(asset_ids):
    """Generate 3 Segments sequentially (extend chain), realistic only."""
    prompts = {"seg1": SEG1_PROMPT, "seg2": SEG2_PROMPT, "seg3": SEG3_PROMPT}
    # Map segments to their scene assets
    seg_scenes = {
        "seg1": "写字楼大堂",
        "seg2": "旧面馆",
        "seg3": "新面馆",
    }
    results = {}

    for seg_idx, seg_name in enumerate(["seg1", "seg2", "seg3"], 1):
        print(f"\n=== STEP 3.{seg_idx}: Generate {seg_name.upper()} (Realistic) ===", flush=True)
        
        # Build image list: characters + this segment's scene
        images = []
        for char in ["李峰", "周总"]:
            if char in asset_ids:
                images.append(asset_ids[char])
        scene_key = seg_scenes[seg_name]
        if scene_key in asset_ids:
            images.append(asset_ids[scene_key])

        item = {
            "id": f"real-{seg_name}",
            "prompt": prompts[seg_name],
            "images": images,
            "out": str(OUTPUT / f"real-{seg_name}.mp4"),
        }
        # Extend from previous
        if seg_idx > 1:
            prev = results.get(f"real-seg{seg_idx - 1}")
            if prev:
                item["video"] = prev
            else:
                print(f"  ⚠️ No previous segment, skipping", flush=True)
                continue

        batch = [item]
        batch_path = EXP_DIR / f"{seg_name}_batch.json"
        batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False))
        rc, out, err = run_cmd([
            "python3", "-u", TOOLS / "seedance_gen.py",
            "--batch", batch_path, "--out-dir", OUTPUT,
        ], 1800)

        p = Path(item["out"])
        if p.exists() and p.stat().st_size > 10000:
            results[item["id"]] = str(p)
            print(f"  ✅ {item['id']}: {p.stat().st_size // 1024}KB", flush=True)
        else:
            results[item["id"]] = None
            print(f"  ❌ {item['id']}: failed", flush=True)

    return results


def step4_concat_check(seg_results):
    """Concat 3 segments + audio check."""
    print("\n=== STEP 4: Concat + Audio Check ===", flush=True)
    segs = [seg_results.get(f"real-seg{i}") for i in range(1, 4)]
    valid_segs = [s for s in segs if s]
    if len(valid_segs) < 2:
        print(f"  ⚠️ Only {len(valid_segs)} segments, need at least 2", flush=True)
        return {}

    all_audio_ok = True
    for i, seg_path in enumerate(valid_segs, 1):
        rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-select_streams", "a",
                               "-show_entries", "stream=codec_name", "-of", "csv=p=0", seg_path], 10)
        has_audio = rc == 0 and out.strip() != ""
        if has_audio:
            print(f"  ✅ seg{i}: audio OK ({out.strip()})", flush=True)
        else:
            print(f"  ❌ seg{i}: NO AUDIO!", flush=True)
            all_audio_ok = False

    out_path = str(OUTPUT / "real-final.mp4")
    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "ffmpeg_concat.py",
        "--inputs", *valid_segs, "--out", out_path, "--check-audio",
    ], 60)
    final = {}
    if rc == 0 and Path(out_path).exists():
        final["realistic"] = {
            "path": out_path,
            "size_kb": Path(out_path).stat().st_size // 1024,
            "audio_ok": all_audio_ok,
            "seg_count": len(valid_segs),
        }
        print(f"  ✅ final: {final['realistic']['size_kb']}KB, {len(valid_segs)} segs, audio={'OK' if all_audio_ok else 'FAIL'}", flush=True)
    else:
        print(f"  ❌ concat failed", flush=True)
    return final


def write_log(asset_ids, seg_results, final):
    log = {
        "experiment": "EXP-V7-046",
        "hypothesis": "H-127: DSLR realistic + indoor/outdoor scene prompt → consistent ≥ 8.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "story": "系统逆袭：面馆传奇 — 李峰+周总, 都市×系统文×爽+逆袭",
        "method": "Volcano asset upload + video extension (3-seg extend chain) + realistic-only + indoor/outdoor scene tags",
        "segments": 3,
        "style": "realistic-only",
        "scene_tags": {
            "seg1": "[INDOOR] 写字楼大堂",
            "seg2": "[INDOOR] 旧面馆",
            "seg3": "[INDOOR] 新面馆",
        },
        "asset_ids": asset_ids,
        "seg_results": {k: ("OK" if v else "FAIL") for k, v in seg_results.items()},
        "final": final,
    }
    (EXP_DIR / "generation-log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"\nGeneration log: {EXP_DIR / 'generation-log.json'}", flush=True)


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
    print("EXP-V7-046 SUMMARY", flush=True)
    print("=" * 60, flush=True)
    info = final.get("realistic", {})
    if info:
        audio = "✅" if info.get("audio_ok") else "⛔NO AUDIO"
        print(f"  {'✅' if info.get('audio_ok') else '⚠️'} realistic: {info['size_kb']}KB, {info['seg_count']} segs, {audio}", flush=True)
    else:
        print(f"  ❌ realistic: FAILED", flush=True)


if __name__ == "__main__":
    main()
