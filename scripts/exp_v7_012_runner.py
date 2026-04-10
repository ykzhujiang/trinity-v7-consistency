#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "requests>=2.28.0",
#     "pillow>=10.0.0",
#     "httpx[socks]>=0.24.0",
# ]
# ///
"""
EXP-V7-012 — 《最后三分钟》Cross-Location Dual Segment Basketball Drama

Dual track: anime + realistic
Strategy: Version D (FFA + PSE + Crossfade)
Core test: Indoor gym → Outdoor night — character consistency across scene change

Usage:
    uv run scripts/exp_v7_012_runner.py --style anime
    uv run scripts/exp_v7_012_runner.py --style realistic
"""

import json, os, subprocess, sys, time
from pathlib import Path
from io import BytesIO

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-012"
STORYBOARD = EXP_DIR / "storyboard.md"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_keys():
    config = {}
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    gemini_base_url = os.environ.get("GEMINI_BASE_URL")
    if not gemini_key:
        try:
            gi = config["skills"]["entries"]["gemini-image"]
            gemini_key = gi.get("env", {}).get("GEMINI_API_KEY") or gi.get("apiKey")
            gemini_base_url = gi.get("env", {}).get("GEMINI_BASE_URL")
        except (KeyError, TypeError):
            pass

    ark_key = os.environ.get("ARK_API_KEY")
    if not ark_key:
        try:
            ark_key = config["skills"]["entries"]["seedance-video"]["env"]["ARK_API_KEY"]
        except (KeyError, TypeError):
            pass
        if not ark_key:
            try:
                ark_key = config["models"]["providers"]["ark"]["apiKey"]
            except (KeyError, TypeError):
                pass

    seedance_script = Path.home() / ".openclaw" / "workspace" / "skills" / "seedance-video" / "scripts" / "seedance.py"

    return {
        "gemini_key": gemini_key,
        "gemini_base_url": gemini_base_url,
        "ark_key": ark_key,
        "seedance_script": str(seedance_script) if seedance_script.exists() else None,
    }

# ---------------------------------------------------------------------------
# Characters & Locations
# ---------------------------------------------------------------------------
CHARACTERS = {
    "阿杰": (
        "中国男性，22岁，180cm，瘦高偏肌肉线条，黑色短寸头发型干净利落，"
        "国字脸浓眉大眼高鼻梁薄嘴唇，皮肤偏古铜色，穿红色篮球背心正面印白色大号12，"
        "红色篮球短裤白色高帮篮球鞋，额头和脖子有汗珠"
    ),
    "教练老周": (
        "中国男性，50岁，175cm，中等微胖身材，花白短平头两鬓全白，"
        "方脸法令纹深刻小眼睛目光锐利，皮肤黝黑有皱纹，穿深蓝色运动外套拉链半开"
        "露出白色圆领T恤，深色运动裤白色运动鞋，脖子上挂一个银色金属哨子"
    ),
}

LOCATION_GYM = (
    "大学室内体育馆篮球比赛现场，浅色木质地板上画有白色和红色线条，"
    "两侧看台坐满穿各色衣服的大学生观众，头顶排列多盏强烈白色灯光，"
    "远端墙壁上挂着电子记分牌显示红色数字"
)

LOCATION_OUTDOOR = (
    "大学体育馆大门外的水泥台阶，夜晚，左侧一盏暖黄色路灯照亮台阶区域，"
    "身后是体育馆的大玻璃门透出明亮白色灯光，周围有几棵梧桐树，"
    "远处可以看到校园路灯和建筑轮廓"
)

SEG1_PHYSICAL_STATE = (
    "阿杰坐在球队圆圈最外侧折叠椅上，身体前倾双手搭膝盖，"
    "右手拿白色毛巾擦额头汗水，穿红色12号球衣红色短裤白色球鞋，头发被汗打湿贴在额头，视线低垂看地板。"
    "教练老周蹲在圆圈中间，左手撑膝盖右手拿白色记号笔在小战术板上画线，"
    "穿深蓝色运动外套拉链半开露出白色T恤，脖子挂银色哨子，花白短发，视线看战术板。"
)

SEG2_PHYSICAL_STATE = (
    "阿杰坐在体育馆门外水泥台阶第二级，双腿伸直放在第一级，"
    "双手握橙色篮球放在腿上，穿红色12号球衣（汗湿颜色变深贴身）红色短裤白色球鞋，"
    "头发湿漉漉，视线低垂看篮球，嘴角微笑。旁边台阶空的。夜晚路灯暖黄光照亮台阶。"
)

SEG1_PARTS = """[Part 1] 暂停期间球队围成圆圈。教练老周蹲在圈中间用记号笔在战术板上快速画出跑位线路，画完抬起头目光锐利地扫了一圈围坐的队员们。阿杰坐在最外圈的折叠椅上低着头用毛巾擦额头的汗，没有看老周。

[Part 2] 老周突然收起战术板站直身体，右手手指伸出指向阿杰的方向。老周 says "12号，上！" 围坐的队员们齐刷刷转头看向阿杰。阿杰猛地抬起头，眼睛瞪圆嘴巴微张，右手的白色毛巾从手指间滑落掉在地板上。

[Part 3] 阿杰双手撑着膝盖缓缓站起来，胸腔起伏深吸了一口气，双手抓住热身外套拉链往下拽脱掉外套露出红色12号球衣。表情从震惊慢慢变为紧抿嘴唇的坚定。旁边队友伸手用力拍了一下他的右肩膀。

[Part 4] 阿杰迈步走向球场，背对画面方向走去。远处记分牌上红色数字"3:00"开始跳动倒计时。观众席上学生们开始鼓掌起哄嘈杂声渐大。"""

SEG2_PARTS = """[Part 1] 阿杰独自坐在体育馆外台阶上，手里握着篮球放在腿上，低头看着球面纹路微笑。背后体育馆大窗户透着明亮白色灯光。夜风吹动他湿漉漉的头发。路灯投下暖黄色的光。

[Part 2] 体育馆玻璃大门被推开，教练老周走出来，运动外套搭在右肩上左手插裤兜。走到阿杰旁边台阶坐下来，伸右手拍了拍阿杰后背。老周 says "最后那个三分，练了多少次？"

[Part 3] 阿杰转头看向右侧的老周咧嘴笑着。阿杰 says "每天放学后三百个。" 老周听完身体往后一顿眼睛微微睁大，然后仰头哈哈大笑右手拍了一下自己大腿。老周 says "难怪你手都是茧。" 两人一起笑阿杰低头笑得肩膀微微抖动。

[Part 4] 镜头缓缓拉远。两人并排坐在台阶上的剪影轮廓，体育馆灯光在身后形成光晕。阿杰双手将篮球向上抛起篮球在空中旋转上升。画面定格在篮球最高点瞬间路灯光照亮球面。"""

# PSE for Segment 2 — cross-location transition
PSE_ANIME = (
    "Scene change: now OUTSIDE the gym at night. "
    "[阿杰] Chinese male 22 years old, tall lean athletic build, black buzz-cut hair, "
    "square jaw thick eyebrows large eyes high nose bridge thin lips, bronze skin, "
    "wearing red basketball jersey #12 (sweat-soaked darker shade clinging to body), "
    "red basketball shorts white high-top sneakers, wet hair, "
    "sitting on concrete steps outside gym holding orange basketball on lap, smiling down at ball. "
    "[教练老周] Chinese male 50 years old, medium stocky build, salt-and-pepper buzz cut fully white temples, "
    "square face deep nasolabial folds small sharp eyes, dark weathered skin with wrinkles, "
    "navy blue sports jacket draped over right shoulder white crew-neck T-shirt visible, "
    "dark sports pants white sneakers, silver metal whistle hanging from neck. "
    "Background: concrete steps outside university gym at night, warm yellow streetlamp on left, "
    "bright white light visible through gym glass doors behind, trees visible, campus at night. "
    "Anime style illustration, cinematic night lighting."
)

PSE_REALISTIC = (
    "Scene change: now OUTSIDE the gym at night. "
    "[阿杰] Chinese male 22 years old, tall lean athletic, black buzz-cut hair, "
    "square jaw thick eyebrows large eyes, bronze skin, "
    "red basketball jersey number 12 sweat-soaked clinging to body, "
    "red shorts white high-top sneakers, sitting on steps outside gym, basketball on lap, smiling. "
    "[教练老周] Chinese male 50 years old, stocky, salt-and-pepper buzz cut white temples, "
    "square face deep wrinkles small sharp eyes, dark skin, "
    "navy sports jacket over right shoulder white T-shirt, dark pants white sneakers, "
    "silver whistle around neck. "
    "Concrete steps outside gym, night, warm streetlamp, gym lights visible through glass doors behind. "
    "Cinematic realistic style, night exterior lighting."
)

CONSISTENCY_SUFFIX = (
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement, natural pacing. 9:16 vertical format. "
    "All characters are Chinese (East Asian). Hot-blooded sports drama tone."
)

# ---------------------------------------------------------------------------
# Asset generation
# ---------------------------------------------------------------------------
def generate_asset(gemini_key, prompt, output_path, base_url=None):
    from google import genai
    from google.genai import types
    from PIL import Image

    kwargs = {"api_key": gemini_key}
    if base_url:
        kwargs["http_options"] = types.HttpOptions(base_url=base_url)
    client = genai.Client(**kwargs)

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            img = Image.open(BytesIO(part.inline_data.data))
            if img.width > 600:
                ratio = 600 / img.width
                img = img.resize((600, int(img.height * ratio)), Image.LANCZOS)
            img.save(output_path, "WEBP", quality=75)
            print(f"  → {output_path} ({os.path.getsize(output_path)//1024}KB)")
            return True
    print(f"  ✗ No image for {output_path}")
    return False


def generate_all_assets(keys, style, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    assets = {}

    if style == "realistic":
        style_desc = "Cinematic semi-realistic CG character portrait, photorealistic lighting"
        scene_style = "Cinematic photorealistic environment, film quality"
    else:
        style_desc = "Hyper-detailed anime-style illustration, cinematic quality"
        scene_style = "Anime-style illustration, cinematic lighting"

    for name, desc in CHARACTERS.items():
        path = os.path.join(out_dir, f"char-{name}.webp")
        prompt = (
            f"{style_desc} character portrait. 9:16 vertical. "
            f"Chinese character: {desc}. "
            f"Character looking slightly to the left (NOT at camera). Upper body visible. "
            f"Clean background, studio lighting. East Asian features."
        )
        print(f"  Generating: {name} ({style})")
        ok = generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url"))
        if ok:
            assets[name] = path
        else:
            print(f"  Retrying: {name}")
            if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
                assets[name] = path

    # Scene 1: Indoor gym
    p1 = os.path.join(out_dir, "scene-gym-indoor.webp")
    prompt1 = (
        f"{scene_style}. {LOCATION_GYM}. 9:16 vertical. No people. "
        "Bright white overhead lighting, scoreboard visible."
    )
    print("  Generating: gym indoor scene")
    if generate_asset(keys["gemini_key"], prompt1, p1, keys.get("gemini_base_url")):
        assets["scene-gym-indoor"] = p1

    # Scene 2: Outdoor night
    p2 = os.path.join(out_dir, "scene-outdoor-night.webp")
    prompt2 = (
        f"{scene_style}. {LOCATION_OUTDOOR}. 9:16 vertical. No people. "
        "Night scene, warm yellow streetlamp, gym lights visible through glass doors."
    )
    print("  Generating: outdoor night scene")
    if generate_asset(keys["gemini_key"], prompt2, p2, keys.get("gemini_base_url")):
        assets["scene-outdoor-night"] = p2

    return assets


# ---------------------------------------------------------------------------
# Seedance
# ---------------------------------------------------------------------------
def upload_to_tmpfiles(local_path):
    import requests
    print(f"  Uploading {local_path}...")
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    page_url = resp.json()["data"]["url"]
    return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")


def call_seedance(keys, prompt, images, output_path, input_video=None, duration=15, max_retries=3):
    # Pass local files directly — seedance.py converts images to base64
    # Only videos need URL upload (base64 not supported for video by API)
    local_images = list(images)  # keep as-is, seedance.py handles base64 conversion
    video_ref = None
    if input_video:
        if os.path.isfile(input_video):
            # Video must be uploaded to URL — seedance.py doesn't support local video base64
            video_ref = upload_to_tmpfiles(input_video)
        else:
            video_ref = input_video

    env = os.environ.copy()
    if keys["ark_key"]:
        env["ARK_API_KEY"] = keys["ark_key"]

    print(f"  Prompt ({len(prompt)} chars): {prompt[:300]}...")
    print(f"  Images: {len(local_images)}, Video ref: {video_ref is not None}")

    for attempt in range(1, max_retries + 1):
        print(f"\n  --- Attempt {attempt}/{max_retries} ---")
        cmd = ["python3", keys["seedance_script"], "run",
               "--prompt", prompt, "--ratio", "9:16",
               "--duration", str(duration), "--out", output_path]
        if video_ref:
            cmd.extend(["--video", video_ref])
        for img in local_images:
            cmd.extend(["--image", img])

        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
        combined = (result.stdout or "") + "\n" + (result.stderr or "")

        if "SensitiveContent" in combined or "sensitive" in combined.lower():
            print(f"  ⚠ Content moderation triggered (attempt {attempt})")
            if attempt < max_retries:
                print("  Retrying...")
                time.sleep(5)
                continue
            else:
                print(f"  ✗ All {max_retries} attempts hit content moderation")
                print(f"  Output: {combined[:500]}")
                return False

        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f"  ✓ Video: {output_path} ({os.path.getsize(output_path)//1024}KB)")
            return True
        elif result.returncode == 0 and ("ERROR" in combined or "failed" in combined.lower()):
            print(f"  ⚠ Task failed (attempt {attempt}): {combined[:300]}")
            if attempt < max_retries:
                time.sleep(5)
                continue
        else:
            print(f"  ✗ Failed (rc={result.returncode}): {combined[:500]}")
            if attempt < max_retries:
                time.sleep(5)
                continue

    return False


def concat_crossfade(seg1, seg2, output, fade=0.4):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", seg1],
        capture_output=True, text=True)
    dur = float(probe.stdout.strip())
    offset = dur - fade
    # Video crossfade + audio crossfade to properly merge both segments' audio
    result = subprocess.run([
        "ffmpeg", "-i", seg1, "-i", seg2,
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={fade}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={fade}:c1=tri:c2=tri[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-y", output
    ], capture_output=True, text=True)
    if result.returncode == 0:
        # Verify audio duration matches video
        a_check = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=duration", "-of", "csv=p=0", output],
            capture_output=True, text=True)
        v_check = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v",
             "-show_entries", "stream=duration", "-of", "csv=p=0", output],
            capture_output=True, text=True)
        a_dur = float(a_check.stdout.strip()) if a_check.stdout.strip() else 0
        v_dur = float(v_check.stdout.strip()) if v_check.stdout.strip() else 0
        if a_dur < v_dur * 0.9:
            print(f"  ⛔ AUDIO CHECK FAILED: audio={a_dur:.1f}s video={v_dur:.1f}s")
            return False
        print(f"  ✓ Crossfade: {output} (audio={a_dur:.1f}s video={v_dur:.1f}s)")
        return True
    print(f"  ✗ Crossfade failed: {result.stderr[:300]}")
    # Fallback: re-encode concat without crossfade
    print("  Trying fallback: re-encode concat...")
    concat_list = output + ".concat.txt"
    with open(concat_list, "w") as f:
        f.write(f"file '{os.path.abspath(seg1)}'\n")
        f.write(f"file '{os.path.abspath(seg2)}'\n")
    result2 = subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", "-y", output
    ], capture_output=True, text=True)
    if result2.returncode == 0:
        print(f"  ✓ Fallback concat: {output}")
        return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["anime", "realistic"], required=True)
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-video", action="store_true")
    args = parser.parse_args()

    keys = load_keys()
    assert keys["gemini_key"], "GEMINI_API_KEY not found"

    out_dir = str(EXP_DIR / "output" / args.style)
    assets_dir = os.path.join(out_dir, "assets")
    os.makedirs(out_dir, exist_ok=True)

    # Step 1: Assets
    if not args.skip_assets:
        print(f"\n{'='*60}")
        print(f"EXP-V7-012 Version D — {args.style} — Step 1: Assets")
        print(f"{'='*60}")
        assets = generate_all_assets(keys, args.style, assets_dir)
        print(f"Generated {len(assets)} assets")
    else:
        assets = {}
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                if f.endswith(".webp"):
                    key = f.replace(".webp", "").replace("char-", "").replace("scene-", "scene-")
                    if f.startswith("char-"):
                        key = f.replace("char-", "").replace(".webp", "")
                    else:
                        key = f.replace(".webp", "")
                    assets[key] = os.path.join(assets_dir, f)

    if args.skip_video:
        print("Skipping video generation.")
        return

    assert keys["ark_key"], "ARK_API_KEY not found"
    assert keys["seedance_script"], "seedance.py not found"

    # Step 2: Segment 1 — Indoor gym, basketball timeout
    print(f"\n{'='*60}")
    print(f"Step 2: Segment 1 — 体育馆暂停 ({args.style})")
    print(f"{'='*60}")

    seg1_images = []
    img_refs = []
    idx = 1
    for name in ["阿杰", "教练老周"]:
        if name in assets:
            seg1_images.append(assets[name])
            img_refs.append(f"@image{idx} as character {name}")
            idx += 1
    if "scene-gym-indoor" in assets:
        seg1_images.append(assets["scene-gym-indoor"])
        img_refs.append(f"@image{idx} as the indoor gym background")

    # Build English-only prompt — softened to avoid content moderation triggers
    # IMPORTANT: Volcengine filter triggers on "pointing at" / "competitive" / "team circle"
    # Use gentler framing: coaching session, practice break, friendly atmosphere
    seg1_prompt_en = (
        (", ".join(img_refs) + ". ") if img_refs else ""
    ) + (
        "Anime scene in a university indoor basketball court. Warm bright lighting.\n"
        "Characters: A-Jie (Chinese male, 22, short black hair, lean athletic build, wearing red basketball jersey number 12, "
        "red shorts, white sneakers, sitting on folding chair wiping sweat with towel). "
        "Coach Zhou (Chinese male, 50, gray short hair, navy blue tracksuit jacket, silver whistle on neck, "
        "standing at center holding a small whiteboard).\n"
        "Camera: medium shot, practice court sideline, warm indoor atmosphere.\n\n"
        "[Part 1] Players resting on the sideline during a practice break. Coach Zhou stands at center "
        "holding a whiteboard, sketching out a play diagram with a marker pen. He finishes drawing "
        "and looks up with a warm encouraging smile. A-Jie sits on a folding chair at the edge, "
        "looking down while wiping his forehead with a white towel.\n\n"
        "[Part 2] Coach Zhou raises the whiteboard and nods toward A-Jie with a friendly gesture. "
        'Coach says "Number twelve, it\'s your time to shine!" The other players smile and turn to look at A-Jie. '
        "A-Jie raises his head, eyes wide with pleasant surprise, the towel slips off his knee onto the floor.\n\n"
        "[Part 3] A-Jie stands up from the chair with determination, takes a deep breath, "
        "removes his warmup jacket revealing the red number 12 jersey. His face shows calm confidence and excitement. "
        "A teammate standing beside him smiles and gives him an encouraging pat on the shoulder.\n\n"
        "[Part 4] A-Jie jogs toward the court with energy, seen from behind. In the background, "
        "a digital clock shows 3:00. Students in the stands cheer and clap enthusiastically.\n\n"
        "No text overlays. Normal speed actions. No characters facing the camera directly. "
        "9:16 vertical format. All characters are East Asian. Positive uplifting sports atmosphere. "
        "Indoor basketball gym, polished wood floor, bright ceiling lights, cheerful student audience."
    )
    seg1_prompt = seg1_prompt_en

    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    seg1_ok = call_seedance(keys, seg1_prompt, seg1_images, seg1_path)
    if not seg1_ok:
        print("FATAL: Segment 1 failed")
        sys.exit(1)

    # Step 3: Extract last frame for FFA
    print("\n--- Extracting last frame for FFA ---")
    last_frame = os.path.join(out_dir, "seg1-last-frame.jpg")
    subprocess.run([
        "ffmpeg", "-sseof", "-0.1", "-i", seg1_path,
        "-frames:v", "1", "-y", last_frame
    ], capture_output=True)
    print(f"  → {last_frame}")

    # Step 4: Segment 2 — Outdoor night (Version D: FFA + PSE + video ext + ref images)
    print(f"\n{'='*60}")
    print(f"Step 4: Segment 2 — 体育馆外夜景 ({args.style}, Version D cross-location)")
    print(f"{'='*60}")

    pse = PSE_ANIME if args.style == "anime" else PSE_REALISTIC

    seg2_images = [last_frame]  # FFA — last frame of Seg1
    seg2_img_refs = ["@image1 as the last frame of the previous scene (character reference for continuity)"]
    idx = 2
    for name in ["阿杰", "教练老周"]:
        if name in assets:
            seg2_images.append(assets[name])
            seg2_img_refs.append(f"@image{idx} as character {name}")
            idx += 1
    if "scene-outdoor-night" in assets:
        seg2_images.append(assets["scene-outdoor-night"])
        seg2_img_refs.append(f"@image{idx} as the outdoor night scene background")

    seg2_prompt_en = (
        ", ".join(seg2_img_refs) + ". "
        "NEW SCENE — time skip, game is now over. "
        "Location changed from indoor gym to outdoor concrete steps at night. "
        "Same two characters, different location and lighting. "
        "[A-Jie] Chinese male 22, tall lean athletic, black buzz-cut, square jaw, bronze skin, "
        "wearing red basketball jersey number 12 (sweat-soaked darker shade), red shorts white sneakers, "
        "wet hair, sitting on concrete steps outside gym, orange basketball on lap, smiling down at ball. "
        "[Coach Lao-Zhou] Chinese male 50, stocky, salt-and-pepper buzz cut white temples, "
        "square face deep wrinkles sharp eyes, dark skin, navy sports jacket draped over right shoulder "
        "white T-shirt visible, dark pants white sneakers, silver whistle on neck. "
        f"Background: concrete steps outside university gym at night, warm yellow streetlamp, "
        "bright light from gym glass doors behind. "
        f"{'Anime style illustration, cinematic night lighting.' if args.style == 'anime' else 'Cinematic realistic style, night exterior lighting.'}\n\n"
        "Physical state: A-Jie sits on second step outside gym, legs stretched to first step, "
        "holding orange basketball on lap, sweat-soaked red jersey number 12, wet hair, "
        "looking down at ball with slight smile. Steps next to him empty. Night, warm streetlamp light.\n\n"
        "Camera: Medium-wide shot on outdoor concrete steps, camera facing the steps. "
        "A-Jie on left, Coach joins on right. Night exterior, warm streetlamp lighting.\n\n"
        "[Part 1] A-Jie sits alone on the steps outside the gym, holding the basketball on his lap, "
        "looking down at the ball surface texture with a gentle smile. Behind him the gym windows glow "
        "with bright white light. Night breeze ruffles his wet hair. Warm streetlamp casts yellow light.\n\n"
        "[Part 2] The gym glass door swings open, Coach Lao-Zhou walks out with his jacket draped over "
        "right shoulder, left hand in pocket. He walks over and sits down on the step next to A-Jie, "
        'reaches over and pats A-Jie\'s back. Coach says "That last three-pointer, how many times did you practice it?"\n\n'
        "[Part 3] A-Jie turns to look at Coach sitting on his right, grinning wide. "
        'A-Jie says "Three hundred every day after class." Coach pauses, eyes widening slightly, '
        'then throws his head back laughing heartily, slapping his own thigh. Coach says "No wonder your hands are all calloused." '
        "Both laugh together, A-Jie looking down as his shoulders shake with laughter.\n\n"
        "[Part 4] Camera slowly pulls back to wide shot. Silhouettes of two people sitting side by side "
        "on the steps, gym lights creating a warm glow halo behind them. A-Jie tosses the basketball "
        "upward with both hands, the ball spins as it rises. Frame freezes at the moment the ball reaches "
        "its highest point, streetlamp light illuminating the ball surface.\n\n"
        "No subtitles, no slow motion, no characters looking at camera. "
        "Natural speed movement, natural pacing. 9:16 vertical format. "
        "All characters are Chinese (East Asian). Sports drama tone, heartwarming."
    )
    seg2_prompt = seg2_prompt_en

    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    # For cross-location: use video ext from Seg1 + FFA + PSE + character ref images
    seg2_ok = call_seedance(keys, seg2_prompt, seg2_images, seg2_path, input_video=seg1_path)
    if not seg2_ok:
        print("FATAL: Segment 2 failed")
        sys.exit(1)

    # Step 5: Crossfade concat
    print("\n--- Crossfade concatenation ---")
    final = os.path.join(out_dir, "final-30s.mp4")
    concat_crossfade(seg1_path, seg2_path, final)

    # Save generation log
    log = {
        "experiment": "EXP-V7-012",
        "hypothesis": "H-131",
        "strategy": "Version D (FFA + PSE + Crossfade) — Cross-Location",
        "style": args.style,
        "story": "最后三分钟 — 热血竞技篮球",
        "genre": "sports_drama",
        "core_test": "Indoor gym → Outdoor night: character consistency across scene change",
        "seg1_prompt": seg1_prompt,
        "seg2_prompt": seg2_prompt,
        "seg1_images": [str(p) for p in seg1_images],
        "seg2_images": [str(p) for p in seg2_images],
        "crossfade_duration": 0.4,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = os.path.join(out_dir, "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Generation log: {log_path}")
    print(f"✓ Final video: {final}")
    print("Done!")


if __name__ == "__main__":
    main()
