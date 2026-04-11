#!/usr/bin/env python3 -u
"""
EXP-V7-047 Runner — 重生黑客 (Dual Track: Anime + Realistic, 3-Seg Extend Chain)
H-130: 重生+黑客 → ≥8.5 anime, ≥7.5 realistic (identity resonance with 朱江)
"""

import json
import os
import sys
import time
import concurrent.futures
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
LINHAO_DESC = "21岁中国男大学生，黑色短发，偏瘦，戴黑框眼镜，穿2005年风格宽松T恤和牛仔裤，书呆子气质但眼神锐利"
LINHAO_EN = "21-year-old Chinese male college student, short black hair, thin build, black-framed glasses, wearing loose 2005-style T-shirt and jeans, nerdy appearance but sharp intelligent eyes"

ZHANGLEI_DESC = "21岁中国男大学生，圆脸微胖，热情外向，穿运动服，头发微卷"
ZHANGLEI_EN = "21-year-old Chinese male college student, round chubby face, energetic extroverted, wearing sportswear, slightly curly hair"

WANGPROF_DESC = "60岁中国男教授，头发花白稀疏，戴金丝眼镜，穿白衬衫深灰西裤，严肃表情"
WANGPROF_EN = "60-year-old Chinese male professor, sparse grey-white hair, gold-rimmed glasses, white shirt with dark grey trousers, stern expression"

# ============================================================
# Scenes
# ============================================================
DORM_DESC = "[INDOOR] 2005年大学6人间宿舍，上下铺铁架床，蓝色床帘，桌上CRT台式显示器，墙贴周杰伦海报和CS1.6截图，2005年纸质日历，翻盖手机，窗外梧桐树，上午暖黄阳光透纱窗，约20㎡"
DORM_EN = "Interior of a 2005-era Chinese university 6-person dormitory, bunk beds with metal frames, blue bed curtains, CRT desktop monitor on desk, Jay Chou poster and CS 1.6 screenshot on wall, 2005 paper calendar, flip phone on desk, sycamore trees outside window, warm morning sunlight through sheer curtains, approximately 20 square meters"

LAB_DESC = "[INDOOR] 大学计算机机房，4排×8台CRT台式机，灰色地板，白色日光灯管，前方投影白板，学生坐塑料椅操作，2000年代风格，嗡嗡风扇声，偏冷白灯光，约60㎡"
LAB_EN = "Interior of a 2000s-era Chinese university computer lab, 4 rows of 8 CRT desktop computers, grey floor, white fluorescent tube lights, projector whiteboard at front, students on plastic chairs, cool white lighting, humming fan noise, approximately 60 square meters"

NETBAR_DESC = "[INDOOR] 2005年校门口网吧，烟雾缭绕，一排排蓝色荧光屏幕，红色塑料椅，墙贴'禁止吸烟'标语但烟雾弥漫，收银台后挂网费价目表(2元/小时)，偏暗灯光，蓝绿色调，约40㎡"
NETBAR_EN = "Interior of a 2005-era Chinese internet cafe near campus gate, hazy with cigarette smoke, rows of blue-glowing CRT screens, red plastic chairs, 'No Smoking' sign on wall contradicted by visible smoke, price list behind counter (2 yuan per hour), dim lighting, blue-green color tone, approximately 40 square meters"

# ============================================================
# Asset Specs — Dual Track
# ============================================================
ASSET_SPECS_ANIME = [
    {"name": "林昊-anime", "type": "character", "desc": f"{LINHAO_DESC}，日漫风格，色彩明亮，线条清晰", "style": "anime"},
    {"name": "张磊-anime", "type": "character", "desc": f"{ZHANGLEI_DESC}，日漫风格，色彩明亮", "style": "anime"},
    {"name": "王教授-anime", "type": "character", "desc": f"{WANGPROF_DESC}，日漫风格", "style": "anime"},
    {"name": "宿舍-anime", "type": "scene", "desc": f"{DORM_DESC}，日漫风格，暖色调", "style": "anime"},
    {"name": "机房-anime", "type": "scene", "desc": f"{LAB_DESC}，日漫风格，冷色调", "style": "anime"},
    {"name": "网吧-anime", "type": "scene", "desc": f"{NETBAR_DESC}，日漫风格，蓝绿色调", "style": "anime"},
]

ASSET_SPECS_REAL = [
    {"name": "林昊-real", "type": "character", "desc": f"{LINHAO_DESC}，写实风格，DSLR质感", "style": "realistic"},
    {"name": "张磊-real", "type": "character", "desc": f"{ZHANGLEI_DESC}，写实风格，DSLR质感", "style": "realistic"},
    {"name": "王教授-real", "type": "character", "desc": f"{WANGPROF_DESC}，写实风格，DSLR质感", "style": "realistic"},
    {"name": "宿舍-real", "type": "scene", "desc": f"{DORM_DESC}，写实风格", "style": "realistic"},
    {"name": "机房-real", "type": "scene", "desc": f"{LAB_DESC}，写实风格", "style": "realistic"},
    {"name": "网吧-real", "type": "scene", "desc": f"{NETBAR_DESC}，写实风格", "style": "realistic"},
]

ALL_SPECS = ASSET_SPECS_ANIME + ASSET_SPECS_REAL

# ============================================================
# Seedance Prompts — Anime Track
# ============================================================
ANIME_SEG1 = (
    "Japanese anime style, vivid colors, clean linework, cinematic composition. "
    f"Interior of a 2005-era Chinese university dormitory with bunk beds and CRT monitors. "
    f"A {LINHAO_EN.replace('black-framed glasses', 'black-framed glasses, anime style')} suddenly sits up on the top bunk bed, cold sweat on forehead. "
    "He looks down at his young hands — shock and disbelief on his face. "
    "Camera: medium shot, side angle 20 degrees, fixed. "
    "He looks around — CRT monitor, flip phone, 2005 calendar on wall, Jay Chou poster. Expression shifts from shock to bitter, ironic smile. "
    "Camera: wide shot showing dormitory interior details, fixed. "
    f"A {ZHANGLEI_EN.replace('sportswear', 'sportswear, anime style')} peeks from the bottom bunk: curious expression. "
    "The protagonist freezes for a second, then suddenly bursts into laughter — knowing smile. "
    "Camera: two-shot medium, side angle, fixed. "
    "He jumps down from bed, walks to desk, turns on the old computer. Windows XP boot screen glows. Deep breath, corner of mouth curves up. "
    "Camera: medium close-up, side profile, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[林昊]'这是……2005年？我……回来了？' "
    "[张磊]'昊子你没事吧？做噩梦了？' "
    "[林昊]'没事……哈，哈哈哈。我没事。' "
    "[林昊]'这次，我要改写一切。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

ANIME_SEG2 = (
    "Japanese anime style, vivid colors, clean linework, cinematic composition. Continuation of previous scene. "
    f"Interior of a 2000s Chinese university computer lab with rows of CRT monitors, cool white fluorescent lighting. "
    f"A {WANGPROF_EN.replace('stern expression', 'stern expression, anime style')} lectures at the front near a whiteboard. "
    f"The {LINHAO_EN.replace('black-framed glasses', 'black-framed glasses, anime style')} sits in the back row, fingers flying across keyboard rapidly. "
    "Camera: medium shot from side, showing his screen with code, fixed. "
    "A classmate next to him peeks at his screen, confused expression, wide eyes. "
    "Camera: over-shoulder shot showing screen with complex code, fixed. "
    "The professor walks over, pushes up gold-rimmed glasses, expression shifts from impatience to serious focus as he reads the code. "
    "Camera: medium shot, three-quarter angle showing professor reading screen, fixed. "
    "The protagonist's expression tightens slightly — hint of worry. Then calm poker face. The professor stares at him for five seconds, turns and walks back. "
    "Camera: two-shot, side angle, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[同学]'你这写的啥？函数名都看不懂……' "
    "[林昊]'呃，课外自学的。' "
    "[王教授]'这个……反向传播算法？你从哪学的？' "
    "[林昊]'在图书馆看到一篇国外论文，觉得有意思就试了试。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

ANIME_SEG3 = (
    "Japanese anime style, vivid colors, clean linework, cinematic composition. Continuation of previous scene. "
    f"Interior of a 2005 Chinese internet cafe, dim lighting, blue-green glow from CRT screens, hazy atmosphere, red plastic chairs. "
    f"Late night. The {LINHAO_EN.replace('black-framed glasses', 'black-framed glasses, anime style')} types code intensely on a computer. "
    "Camera: medium close-up, side profile, screen glow on face, fixed. "
    f"The {ZHANGLEI_EN.replace('sportswear', 'sportswear, anime style')} sits next to him, occasionally peeking at his screen with curiosity. "
    "Camera: two-shot medium, side angle, fixed. "
    "The protagonist opens a domain registration page, types rapidly — registering many domain names. His finger pauses on the last one, brief hesitation. "
    "Camera: close-up of hands on keyboard, then screen showing domain list, fixed. "
    "He presses Enter decisively. Turns to his friend with a confident smile. "
    "Camera: medium shot, slight low angle, showing both characters, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[张磊]'又在搞那些看不懂的东西？' "
    "[林昊]'帮我注册几个域名，借你身份证。' "
    "[张磊]'啥是域名？' "
    "[林昊]'磊子，记住今天——这是我们人生翻盘的第一步。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical."
)

# ============================================================
# Seedance Prompts — Realistic Track
# ============================================================
REAL_SEG1 = (
    "DSLR cinematic, 35mm lens, warm morning sunlight through sheer curtains. Photorealistic, real humans. "
    f"Interior of a 2005-era Chinese university dormitory with metal bunk beds, blue bed curtains, CRT monitor on desk, Jay Chou poster on wall, 2005 paper calendar. "
    f"A {LINHAO_EN} suddenly sits up on the top bunk, cold sweat on forehead. "
    "He looks down at his young hands — shock and disbelief. "
    "Camera: medium shot, side angle 20 degrees, fixed. "
    "He looks around — CRT monitor, flip phone, 2005 calendar. Expression: shock to bitter ironic smile. "
    "Camera: wide shot showing dormitory details, fixed. "
    f"A {ZHANGLEI_EN} peeks from bottom bunk: 'Having a nightmare?' "
    "The protagonist freezes, then bursts into knowing laughter. "
    "Camera: two-shot medium, side angle, fixed. "
    "He jumps down, walks to desk, turns on old computer. Windows XP boot screen. Deep breath, mouth curves up. "
    "Camera: medium close-up, side profile, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[林昊]'这是……2005年？我……回来了？' "
    "[张磊]'昊子你没事吧？做噩梦了？' "
    "[林昊]'没事……哈，哈哈哈。我没事。' "
    "[林昊]'这次，我要改写一切。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
    "NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG."
)

REAL_SEG2 = (
    "DSLR cinematic, 35mm lens, cool white fluorescent lighting. Photorealistic, real humans. Continuation of previous scene. "
    f"Interior of a 2000s Chinese university computer lab, rows of CRT desktop computers, grey floor, white fluorescent tube lights, projector whiteboard at front. "
    f"A {WANGPROF_EN} lectures at front. "
    f"The {LINHAO_EN} sits in back row, fingers flying across keyboard. "
    "Camera: medium shot from side showing his screen with code, fixed. "
    "A classmate peeks at his screen, confused. "
    "Camera: over-shoulder shot showing complex code on screen, fixed. "
    "The professor walks over, pushes up gold-rimmed glasses, expression shifts from impatience to serious as he reads the code. "
    "Camera: medium shot, three-quarter angle, fixed. "
    "Protagonist tightens expression slightly, then calm. Professor stares 5 seconds, turns back. "
    "Camera: two-shot, side angle, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[同学]'你这写的啥？函数名都看不懂……' "
    "[林昊]'呃，课外自学的。' "
    "[王教授]'这个……反向传播算法？你从哪学的？' "
    "[林昊]'在图书馆看到一篇国外论文，觉得有意思就试了试。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
    "NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG."
)

REAL_SEG3 = (
    "DSLR cinematic, 35mm lens, dim blue-green lighting from CRT screens. Photorealistic, real humans. Continuation of previous scene. "
    f"Interior of a 2005 Chinese internet cafe, hazy smoke, rows of blue-glowing CRT screens, red plastic chairs, 'No Smoking' sign, price list on wall (2 yuan per hour). "
    f"Late night. The {LINHAO_EN} types code intensely. Screen glow illuminates his face. "
    "Camera: medium close-up, side profile, fixed. "
    f"The {ZHANGLEI_EN} sits next to him, occasionally peeking at his screen. "
    "Camera: two-shot medium, side angle, fixed. "
    "Protagonist opens domain registration page, types rapidly. Finger pauses on last domain, brief hesitation. "
    "Camera: close-up of hands on keyboard then screen, fixed. "
    "Presses Enter decisively. Turns to friend with confident smile. "
    "Camera: medium shot, slight low angle, fixed. "
    "Dialogue (Chinese Mandarin, must finish before second 12): "
    "[张磊]'又在搞那些看不懂的东西？' "
    "[林昊]'帮我注册几个域名，借你身份证。' "
    "[张磊]'啥是域名？' "
    "[林昊]'磊子，记住今天——这是我们人生翻盘的第一步。' "
    "All speech Chinese Mandarin, normal speed, natural pacing. "
    "Characters never face camera. 180-degree rule. No subtitles, no slow motion. 9:16 vertical. "
    "NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG."
)

# ============================================================
# Utility
# ============================================================
def run_cmd(cmd, timeout=1800):
    import subprocess
    cmd_str = [str(c) for c in cmd]
    print(f"[CMD] {' '.join(cmd_str)}", flush=True)
    p = subprocess.run(cmd_str, capture_output=True, text=True, timeout=timeout)
    if p.stdout:
        print(p.stdout, flush=True)
    if p.stderr:
        print(f"[STDERR] {p.stderr}", flush=True)
    return p.returncode, p.stdout, p.stderr


# ============================================================
# Step 1: Generate Reference Assets (Gemini)
# ============================================================
def step1_generate_assets():
    print("\n=== STEP 1: Generate Reference Assets (Anime + Realistic) ===", flush=True)
    specs_path = EXP_DIR / "asset_specs.json"
    specs_path.write_text(json.dumps(ALL_SPECS, indent=2, ensure_ascii=False))
    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "gemini_chargen.py",
        "--specs", specs_path, "--out-dir", ASSETS,
    ], 600)
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


# ============================================================
# Step 2: Upload Assets to Volcano
# ============================================================
def step2_upload_assets(asset_paths):
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
        "--group-name", "exp-v7-047", "--json",
    ], 600)
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


# ============================================================
# Step 3: Generate Videos — Dual Track, 3 Segments Each
# ============================================================
def gen_one_segment(style, seg_idx, prompt, asset_ids, prev_video=None):
    """Generate one segment for one style. Returns path or None."""
    seg_name = f"seg{seg_idx}"
    tag = f"{style}-{seg_name}"
    print(f"\n--- Generating {tag} ---", flush=True)

    # Build image list: characters + scene for this segment
    char_suffix = "-anime" if style == "anime" else "-real"
    scene_map = {1: "宿舍", 2: "机房", 3: "网吧"}
    
    images = []
    for char in ["林昊", "张磊", "王教授"]:
        key = f"{char}{char_suffix}"
        if key in asset_ids:
            images.append(asset_ids[key])
    scene_key = f"{scene_map[seg_idx]}{char_suffix}"
    if scene_key in asset_ids:
        images.append(asset_ids[scene_key])

    item = {
        "id": tag,
        "prompt": prompt,
        "images": images,
        "out": str(OUTPUT / f"{tag}.mp4"),
    }
    if prev_video:
        item["video"] = prev_video

    batch = [item]
    batch_path = EXP_DIR / f"{tag}_batch.json"
    batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False))
    rc, out, err = run_cmd([
        "python3", "-u", TOOLS / "seedance_gen.py",
        "--batch", batch_path, "--out-dir", OUTPUT,
    ], 1800)

    p = Path(item["out"])
    if p.exists() and p.stat().st_size > 10000:
        print(f"  ✅ {tag}: {p.stat().st_size // 1024}KB", flush=True)
        return str(p)
    else:
        print(f"  ❌ {tag}: failed", flush=True)
        return None


def step3_generate_videos(asset_ids):
    anime_prompts = [ANIME_SEG1, ANIME_SEG2, ANIME_SEG3]
    real_prompts = [REAL_SEG1, REAL_SEG2, REAL_SEG3]
    results = {}

    # Seg1: anime + realistic in parallel
    print("\n=== STEP 3.1: Generate Seg1 (Anime + Realistic PARALLEL) ===", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_anime = pool.submit(gen_one_segment, "anime", 1, anime_prompts[0], asset_ids)
        f_real = pool.submit(gen_one_segment, "realistic", 1, real_prompts[0], asset_ids)
        results["anime-seg1"] = f_anime.result()
        results["realistic-seg1"] = f_real.result()

    # Seg2: extend from Seg1, parallel
    print("\n=== STEP 3.2: Generate Seg2 (Extend from Seg1, PARALLEL) ===", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        if results.get("anime-seg1"):
            futures["anime-seg2"] = pool.submit(gen_one_segment, "anime", 2, anime_prompts[1], asset_ids, results["anime-seg1"])
        if results.get("realistic-seg1"):
            futures["realistic-seg2"] = pool.submit(gen_one_segment, "realistic", 2, real_prompts[1], asset_ids, results["realistic-seg1"])
        for key, f in futures.items():
            results[key] = f.result()

    # Seg3: extend from Seg2, parallel
    print("\n=== STEP 3.3: Generate Seg3 (Extend from Seg2, PARALLEL) ===", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        if results.get("anime-seg2"):
            futures["anime-seg3"] = pool.submit(gen_one_segment, "anime", 3, anime_prompts[2], asset_ids, results["anime-seg2"])
        if results.get("realistic-seg2"):
            futures["realistic-seg3"] = pool.submit(gen_one_segment, "realistic", 3, real_prompts[2], asset_ids, results["realistic-seg2"])
        for key, f in futures.items():
            results[key] = f.result()

    return results


# ============================================================
# Step 4: Concat + Audio Check
# ============================================================
def step4_concat_check(seg_results):
    print("\n=== STEP 4: Concat + Audio Check ===", flush=True)
    final = {}
    for style in ["anime", "realistic"]:
        segs = [seg_results.get(f"{style}-seg{i}") for i in range(1, 4)]
        valid_segs = [s for s in segs if s]
        if len(valid_segs) < 2:
            print(f"  ⚠️ {style}: only {len(valid_segs)} segments", flush=True)
            continue

        all_audio_ok = True
        for i, seg_path in enumerate(valid_segs, 1):
            rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-select_streams", "a",
                                   "-show_entries", "stream=codec_name", "-of", "csv=p=0", seg_path], 10)
            has_audio = rc == 0 and out.strip() != ""
            if has_audio:
                print(f"  ✅ {style} seg{i}: audio OK", flush=True)
            else:
                print(f"  ❌ {style} seg{i}: NO AUDIO!", flush=True)
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
            print(f"  ✅ {style} final: {final[style]['size_kb']}KB, {len(valid_segs)} segs, audio={'OK' if all_audio_ok else 'FAIL'}", flush=True)
        else:
            print(f"  ❌ {style} concat failed", flush=True)
    return final


# ============================================================
# Step 5: Write Generation Log
# ============================================================
def write_log(asset_ids, seg_results, final):
    log = {
        "experiment": "EXP-V7-047",
        "hypothesis": "H-130: 重生+黑客题材 → ≥8.5 anime, ≥7.5 realistic (identity resonance)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "story": "重生黑客 — 林昊重生回2005年大一，用21年技术记忆改写人生",
        "method": "Dual track (anime+realistic) × 3-seg extend chain × Volcano asset upload × concurrent generation",
        "segments": 3,
        "styles": ["anime", "realistic"],
        "scene_tags": {
            "seg1": "[INDOOR] 2005年大学宿舍",
            "seg2": "[INDOOR] 大学计算机机房",
            "seg3": "[INDOOR] 2005年网吧",
        },
        "asset_ids": asset_ids,
        "seg_results": {k: ("OK" if v else "FAIL") for k, v in seg_results.items()},
        "final": final,
    }
    (EXP_DIR / "generation-log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"\nGeneration log: {EXP_DIR / 'generation-log.json'}", flush=True)


# ============================================================
# Main
# ============================================================
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

    t0 = time.time()
    asset_paths = step1_generate_assets()
    asset_ids = step2_upload_assets(asset_paths)
    seg_results = step3_generate_videos(asset_ids)
    final = step4_concat_check(seg_results)
    write_log(asset_ids, seg_results, final)
    elapsed = time.time() - t0

    print("\n" + "=" * 60, flush=True)
    print(f"EXP-V7-047 SUMMARY (elapsed: {elapsed:.0f}s)", flush=True)
    print("=" * 60, flush=True)
    for style in ["anime", "realistic"]:
        info = final.get(style, {})
        if info:
            audio = "✅" if info.get("audio_ok") else "⛔NO AUDIO"
            print(f"  {'✅' if info.get('audio_ok') else '⚠️'} {style}: {info['size_kb']}KB, {info['seg_count']} segs, {audio}", flush=True)
        else:
            print(f"  ❌ {style}: FAILED", flush=True)


if __name__ == "__main__":
    main()
