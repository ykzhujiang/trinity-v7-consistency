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
EXP-V7-009 — Version D Generalization Test (New Story: 电梯逆袭)

Dual track: anime + 3d-animated
Strategy: Version D (FFA + PSE + Crossfade)

Usage:
    python3 exp_v7_009_runner.py --style anime
    python3 exp_v7_009_runner.py --style 3d-animated
"""

import json, os, subprocess, sys, time, re
from pathlib import Path
from io import BytesIO

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-009"
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
# Characters
# ---------------------------------------------------------------------------
CHARACTERS = {
    "李明": "中国男性，28岁，178cm，偏瘦，短发微乱，面容清秀略显疲惫，穿深蓝色廉价西装白衬衫领带歪斜，黑色旧皮鞋，拎棕色旧公文包",
    "王总": "中国男性，50岁，172cm，微胖啤酒肚，秃顶两侧灰发，圆脸，穿黑色高定西装金色袖扣戴金表",
    "周老": "中国男性，65岁，170cm，偏瘦精干，花白短发，面容和善笑纹，肤色偏黑，穿灰色旧T恤黑色运动短裤，黄色皮卡丘拖鞋",
}

LOCATION_OFFICE = "现代写字楼高层办公室，大玻璃落地窗城市天际线，深色实木大办公桌，黑色皮椅"
LOCATION_ELEVATOR = "写字楼不锈钢电梯内部，暖色灯光，楼层数字屏"

# PSE for Segment 2 (must match Segment 1 ending state → Segment 2 opening state)
PSE_ANIME = (
    "Continuing exactly from: [李明] stands on the left side of the elevator interior, "
    "Chinese male 28 years old, thin build, messy short hair, wearing an oversized dark blue cheap suit "
    "with white shirt and crooked tie, left hand holding a brown old briefcase, right shoulder leaning "
    "against stainless steel elevator wall, looking down at the floor with a dejected expression. "
    "[周老] stands on the right side of the elevator, Chinese male 65 years old, thin and wiry, "
    "grey-white short hair, kind face with laugh lines, dark skin, wearing grey old T-shirt and "
    "black athletic shorts, yellow Pikachu slippers on his feet, both hands in T-shirt pockets, "
    "body relaxed leaning against elevator wall, looking at 李明 with curious bright eyes. "
    "Background: stainless steel elevator interior, warm lighting, floor number display screen above."
)

PSE_3D = (
    "Continuing exactly from: [李明] stands on the left side of the elevator in Pixar/3D animated style, "
    "Chinese male 28 years old, thin build, messy short black hair, wearing oversized dark blue cheap suit "
    "with white shirt and crooked tie, left hand holding brown old briefcase, right shoulder against "
    "stainless steel wall, looking at the floor, dejected expression. "
    "[周老] on the right side, Chinese male 65 years old, wiry build, grey-white short hair, kind face "
    "with deep laugh lines, tanned skin, grey old T-shirt and black shorts, bright yellow Pikachu "
    "slippers, both hands tucked in shirt pockets, relaxed posture, looking at 李明 with amused curiosity. "
    "Background: 3D animated stainless steel elevator, warm golden ceiling lights, digital floor display."
)

# Segment 1 Parts
SEG1_PARTS = """[Part 1] 王总右手食指敲着桌面，左手端起咖啡杯，嘴角撇下来，俯视着对面的李明。王总 says "你这简历...三年换了五份工作，你是来面试的还是来旅游的？"李明嘴唇抿紧但没低头，双手握拳放在膝盖上。

[Part 2] 王总说到激动处左手一挥，咖啡杯里的咖啡泼出来溅到桌上的简历纸上，王总愣了一秒然后假装没事继续说。王总 says "我们公司不需要——"他低头瞟了一眼被咖啡浸湿的简历，清了清嗓子。李明嘴角微微上扬。

[Part 3] 李明站起来，左手拿起桌上被咖啡浸湿的简历纸，右手整了整歪斜的领带，直视王总。李明 says "王总，您的咖啡比您的眼光还不稳。"王总嘴巴张开但说不出话，右手还保持着端杯的姿势但杯子已经空了。

[Part 4] 李明转身走向办公室玻璃门，左手拎公文包右手拉开门把手，背影挺直。王总在背后站起来指着他的方向但没说出话。李明头也不回走出办公室，走廊里他的嘴角终于露出一个笑。"""

# Segment 2 Parts
SEG2_PARTS = """[Part 1] 电梯内安静，只有数字屏上楼层数字在跳。李明低着头叹了口气，右手松了松领带。周老侧头看他，眼睛眯起来带着笑意。周老 says "小伙子，刚才那句'咖啡比眼光不稳'，是你临场想的？"

[Part 2] 李明抬头看向周老，注意到他的皮卡丘拖鞋，表情困惑。李明 says "您...听到了？"周老从T恤口袋里掏出右手摆了摆。周老 says "隔壁办公室的，隔音不太好。"周老咧嘴笑露出白牙。

[Part 3] 电梯到达一楼，门打开。周老从短裤口袋里掏出一张名片，两根手指夹着递向李明。周老 says "我觉得你挺有意思。有空来聊聊。"李明接过名片低头一看，眼睛猛然睁大，嘴角开始不自主抽搐。

[Part 4] 李明抬头看向周老，周老已经踩着皮卡丘拖鞋悠闲走出电梯，右手背在身后摆了摆手。李明站在原地，手拿名片，嘴巴半张，眼睛瞪大。电梯门开始缓缓关闭。"""

CONSISTENCY_SUFFIX = (
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement. 9:16 vertical format. "
    "Consistent warm indoor lighting throughout."
)

SEG1_PHYSICAL_STATE = (
    "李明坐在办公桌对面的黑色椅子上，身体前倾，双手放在膝盖上，视线看向对面的王总。"
    "王总坐在大办公桌后的皮椅上，身体后仰，右手食指敲桌面，左手端着白色咖啡杯，视线俯视李明。"
    "桌上散落着李明的简历纸。"
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

    if style == "3d-animated":
        style_desc = "3D animated character portrait, Pixar/Disney quality CG"
        scene_style = "3D animated environment, Pixar quality"
    else:
        style_desc = "Anime-style semi-realistic illustration"
        scene_style = "Anime-style illustration, cinematic quality"

    for name, desc in CHARACTERS.items():
        path = os.path.join(out_dir, f"char-{name}.webp")
        prompt = (
            f"{style_desc} character portrait. 9:16 vertical. "
            f"Chinese character: {desc}. "
            f"Character looking slightly to the left (NOT at camera). Upper body visible. "
            f"Clean background, studio lighting."
        )
        print(f"  Generating: {name}")
        if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
            assets[name] = path

    # Scene 1: office
    p = os.path.join(out_dir, "scene-office.webp")
    prompt = (
        f"{scene_style}. Modern high-rise office. 9:16 vertical. "
        f"{LOCATION_OFFICE}. No people. Warm lighting."
    )
    print("  Generating: office scene")
    if generate_asset(keys["gemini_key"], prompt, p, keys.get("gemini_base_url")):
        assets["scene-office"] = p

    # Scene 2: elevator
    p2 = os.path.join(out_dir, "scene-elevator.webp")
    prompt2 = (
        f"{scene_style}. Stainless steel elevator interior. 9:16 vertical. "
        f"{LOCATION_ELEVATOR}. No people. Warm overhead lighting."
    )
    print("  Generating: elevator scene")
    if generate_asset(keys["gemini_key"], prompt2, p2, keys.get("gemini_base_url")):
        assets["scene-elevator"] = p2

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


def call_seedance(keys, prompt, images, output_path, input_video=None, duration=15):
    cmd = ["python3", keys["seedance_script"], "run",
           "--prompt", prompt, "--ratio", "9:16",
           "--duration", str(duration), "--out", output_path]
    if input_video:
        if os.path.isfile(input_video):
            input_video = upload_to_tmpfiles(input_video)
        cmd.extend(["--video", input_video])
    for img in images:
        cmd.extend(["--image", img])

    env = os.environ.copy()
    if keys["ark_key"]:
        env["ARK_API_KEY"] = keys["ark_key"]

    print(f"  Prompt ({len(prompt)} chars): {prompt[:250]}...")
    print(f"  Images: {len(images)}, Video ref: {input_video is not None}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    if result.returncode == 0:
        print(f"  ✓ Video: {output_path}")
        return True
    else:
        print(f"  ✗ Failed: {result.stderr[:500]}")
        return False


def concat_crossfade(seg1, seg2, output, fade=0.4):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", seg1],
        capture_output=True, text=True)
    dur = float(probe.stdout.strip())
    offset = dur - fade
    result = subprocess.run([
        "ffmpeg", "-i", seg1, "-i", seg2,
        "-filter_complex", f"xfade=transition=fade:duration={fade}:offset={offset}",
        "-y", output
    ], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✓ Crossfade: {output}")
        return True
    print(f"  ✗ Crossfade failed: {result.stderr[:300]}")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["anime", "3d-animated"], required=True)
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-video", action="store_true")
    args = parser.parse_args()

    keys = load_keys()
    assert keys["gemini_key"], "GEMINI_API_KEY not found"
    
    out_dir = str(EXP_DIR / args.style)
    assets_dir = os.path.join(out_dir, "assets")
    os.makedirs(out_dir, exist_ok=True)

    # Step 1: Assets
    if not args.skip_assets:
        print(f"\n{'='*60}")
        print(f"EXP-V7-009 Version D — {args.style} — Step 1: Assets")
        print(f"{'='*60}")
        assets = generate_all_assets(keys, args.style, assets_dir)
        print(f"Generated {len(assets)} assets")
    else:
        assets = {}
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                name = f.replace(".webp", "").replace("char-", "").replace("scene-", "scene-" if "scene" in f else "")
                assets[f.replace(".webp", "").replace("char-", "")] = os.path.join(assets_dir, f)

    if args.skip_video:
        print("Skipping video generation.")
        return

    assert keys["ark_key"], "ARK_API_KEY not found"
    assert keys["seedance_script"], "seedance.py not found"

    # Step 2: Segment 1 — Office scene (text-to-video with ref images)
    print(f"\n{'='*60}")
    print(f"Step 2: Segment 1 — Office interview")
    print(f"{'='*60}")

    seg1_images = []
    for name in ["李明", "王总"]:
        if name in assets:
            seg1_images.append(assets[name])
    if "scene-office" in assets:
        seg1_images.append(assets["scene-office"])

    img_refs = []
    for i, name in enumerate(["李明", "王总", "scene-office"]):
        if name in assets or f"scene-{name}" in assets:
            img_refs.append(f"@image{i+1} as {'character ' + name if name != 'scene-office' else 'the office background'}")

    seg1_prompt = (
        ", ".join(img_refs) + ". " if img_refs else ""
    ) + (
        f"Physical state: {SEG1_PHYSICAL_STATE}\n"
        f"Camera: Medium close-up, office interior, camera on the side of the desk angled toward 李明 (no axis crossing).\n\n"
        f"{SEG1_PARTS}\n\n"
        f"All characters are Chinese. {CONSISTENCY_SUFFIX} "
        "Modern high-rise office with dark wood desk, black leather chairs, glass windows with city skyline. "
        "Consistent warm indoor lighting, same generic Asian city skyline throughout."
    )

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

    # Step 4: Segment 2 — Elevator (Version D: FFA + PSE + video extension)
    print(f"\n{'='*60}")
    print(f"Step 4: Segment 2 — Elevator encounter (Version D)")
    print(f"{'='*60}")

    pse = PSE_ANIME if args.style == "anime" else PSE_3D

    seg2_images = [last_frame]  # FFA: last frame as @image1
    for name in ["李明", "周老"]:
        if name in assets:
            seg2_images.append(assets[name])
    if "scene-elevator" in assets:
        seg2_images.append(assets["scene-elevator"])

    # Build image refs for seg2
    seg2_img_refs = ["@image1 as the first frame of this scene"]
    idx = 2
    for name in ["李明", "周老"]:
        if name in assets:
            seg2_img_refs.append(f"@image{idx} as character {name}")
            idx += 1
    if "scene-elevator" in assets:
        seg2_img_refs.append(f"@image{idx} as the elevator interior")

    seg2_prompt = (
        ", ".join(seg2_img_refs) + ". "
        f"Extend @video1 by 15 seconds. "
        f"Continue seamlessly from this exact frame. "
        f"Scene transition: 李明 has walked from the office to the elevator. "
        f"{pse}\n\n"
        f"Camera: Medium shot, inside elevator, camera in the corner opposite the door (no axis crossing).\n\n"
        f"{SEG2_PARTS}\n\n"
        f"All characters are Chinese. {CONSISTENCY_SUFFIX} "
        "Stainless steel elevator interior, warm overhead lighting, digital floor display."
    )

    seg2_path = os.path.join(out_dir, "segment-02.mp4")
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
        "experiment": "EXP-V7-009",
        "strategy": "Version D (FFA + PSE + Crossfade)",
        "style": args.style,
        "story": "电梯逆袭 — 都市逆袭×搞笑",
        "seg1_prompt": seg1_prompt,
        "seg2_prompt": seg2_prompt,
        "seg1_images": seg1_images,
        "seg2_images": seg2_images,
        "crossfade": True,
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
