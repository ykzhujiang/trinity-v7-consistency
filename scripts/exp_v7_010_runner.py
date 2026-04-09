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
EXP-V7-010 — Asset Library Integration + Dual Segment Consistency

Dual track: anime + realistic
Strategy: Version D (FFA + PSE + Crossfade)
Story: 创业者遭遇投资人背叛，绝地反击

Usage:
    uv run scripts/exp_v7_010_runner.py --style anime
    uv run scripts/exp_v7_010_runner.py --style realistic
"""

import json, os, subprocess, sys, time, re
from pathlib import Path
from io import BytesIO

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-010"
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
    "陈锐": "中国男性，30岁，180cm，偏瘦精干，短寸头，浓眉大眼，下颌线硬朗，皮肤偏白，穿深灰色修身西装白衬衫没打领带袖口卷到手腕，黑色牛津鞋，左手腕银色钢表",
    "赵鹏": "中国男性，52岁，175cm，壮实微胖，背梳油头花白，方脸法令纹深，戴金丝边眼镜，穿藏蓝色双排扣西装红色口袋巾金色袖扣，黑色漆皮鞋，右手无名指金色戒指",
    "苏晴": "中国女性，27岁，165cm，纤瘦，齐肩黑色直发刘海斜分，鹅蛋脸皮肤白皙，穿白色衬衫深蓝色西装裤黑色低跟鞋，左手抱银色笔记本电脑",
}

LOCATION_MEETING = "现代高档写字楼会议室，落地玻璃窗城市天际线，长方形白色大会议桌，灰色办公椅，桌上散放文件和两杯水"
LOCATION_CORRIDOR = "写字楼走廊，米灰色大理石地板，左侧落地窗自然光，右侧白色墙面抽象画，尽头银色电梯门"

SEG1_PHYSICAL_STATE = (
    "陈锐坐在会议桌左侧灰色椅子上，身体微微前倾，双手交叉放在桌面上，视线正对对面的赵鹏。"
    "赵鹏坐在会议桌右侧，身体后仰靠椅背，左手按着桌上一份装订好的白色文件，右手食指竖起指向陈锐，视线俯视。"
    "桌上两杯水，文件散落。"
)

SEG2_PHYSICAL_STATE = (
    "陈锐站在会议室门外走廊中央，右手拿着黑色手机，左手自然下垂，面朝电梯方向，背对会议室玻璃门。"
    "苏晴从走廊右前方电梯方向走过来，左手抱着银色笔记本电脑，右手自然摆动，步伐利落。两人相距约三米。"
)

SEG1_PARTS = """[Part 1] 赵鹏左手按住桌上的白色合同文件，右手食指指向陈锐脸的方向，嘴角向下撇，眉头皱起。赵鹏 says "陈锐，你那个破项目烧了我三千万，现在告诉我要再追加？"陈锐双手交叉放在桌上不动，目光平静地直视赵鹏，嘴唇微微抿紧。

[Part 2] 赵鹏猛地站起来，双手抓起桌上的合同文件，用力从中间撕开，纸片碎屑从他手中飘落到桌面和地板上。赵鹏 says "这份协议，作废！"陈锐身体微微后仰，眼睛眨了一下，双手从桌面收回放到扶手上，表情从平静变为短暂的震惊。

[Part 3] 陈锐低头看着桌上散落的合同碎片，沉默两秒，右手拿起面前的水杯慢慢喝了一口，然后放下杯子。他抬头直视赵鹏，嘴角缓慢上扬露出一个笑。陈锐 says "赵总，谢谢你帮我省了时间。"赵鹏站在原地，脸上的愤怒变成困惑，金丝边眼镜微微滑到鼻尖。

[Part 4] 陈锐推开椅子站起来，左手整了整西装衣襟，右手拿起桌角自己的黑色手机，转身走向会议室玻璃门。赵鹏张了张嘴想说什么但没出声，右手无意识地扶了扶眼镜。陈锐右手拉开门走出去，背影笔挺。赵鹏 says "你...你走着瞧！"但陈锐已经走出了会议室。"""

SEG2_PARTS = """[Part 1] 陈锐从会议室走出来关上玻璃门，深吸一口气，右手把手机塞进西装口袋。苏晴从电梯方向快步走来，左手抱着笔记本电脑，看到陈锐后脚步稍微加快。苏晴 says "陈总，谈崩了？"陈锐转身面向苏晴，耸了耸肩膀。

[Part 2] 陈锐和苏晴并肩站在走廊中央，陈锐双手插在西装裤口袋里，侧头看着苏晴。陈锐 says "协议撕了。苏晴，把他投的每一个项目都查一遍。"苏晴把笔记本电脑换到右手抱着，左手从裤袋摸出手机晃了晃，眼神亮了。

[Part 3] 苏晴低头看了一眼手机屏幕，然后抬头直视陈锐，嘴角向上弯起一个弧度。苏晴 says "已经查了。您猜怎么着？他投的六个项目，四个在亏。"陈锐听完后偏头看向走廊尽头的电梯方向，嘴角慢慢咧开。

[Part 4] 陈锐转身大步走向走廊尽头的银色电梯门，左手按下电梯按钮，右手从口袋掏出手机看了一眼。苏晴在他身后两步远，右手抱笔记本电脑，左手整理了一下刘海。电梯门打开，陈锐迈步走进电梯，在电梯里转身面向镜头外侧方向，嘴角的笑意还没收。陈锐 says "走，该我们出牌了。"苏晴快步跟进电梯，电梯门缓缓关闭。"""

# PSE for Segment 2
PSE_ANIME = (
    "Continuing exactly from: [陈锐] stands outside the meeting room in the corridor, "
    "Chinese male 30 years old, lean and sharp, buzz cut hair, thick eyebrows, strong jawline, fair skin, "
    "wearing fitted dark grey suit with white shirt no tie sleeves rolled to wrists, black Oxford shoes, "
    "silver steel watch on left wrist, right hand holding black phone, left hand at side, facing toward elevator, "
    "back to the glass meeting room door. "
    "[苏晴] walking toward him from the elevator end of corridor, "
    "Chinese female 27 years old, slim, shoulder-length straight black hair with side-swept bangs, "
    "oval face fair skin, wearing white blouse dark blue dress pants black low heels, "
    "left hand holding silver laptop, right arm swinging naturally, brisk purposeful stride. "
    "Background: modern office corridor, grey marble floor, floor-to-ceiling windows on left with natural light, "
    "white walls with abstract paintings on right, silver elevator doors at far end. Anime style illustration."
)

PSE_REALISTIC = (
    "Continuing exactly from: [陈锐] stands outside the meeting room in the corridor, "
    "Chinese male 30 years old, lean athletic build, buzz cut hair, thick eyebrows, strong jawline, fair skin, "
    "wearing fitted dark grey suit white shirt no tie sleeves rolled to wrists, black Oxford shoes, "
    "silver steel watch on left wrist, right hand holding black phone, left hand at side, facing elevator direction. "
    "[苏晴] approaching from elevator end of corridor, "
    "Chinese female 27 years old, slim, shoulder-length straight black hair side-swept bangs, "
    "oval face fair skin, white blouse dark blue dress pants black low heels, "
    "left hand holding silver laptop, right arm swinging, walking briskly. "
    "Background: modern office corridor, grey marble floor, floor-to-ceiling windows left side natural light, "
    "white walls abstract paintings right side, silver elevator doors at end. Cinematic realistic style."
)

CONSISTENCY_SUFFIX = (
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement, natural pacing. 9:16 vertical format. "
    "Consistent warm indoor lighting throughout. All characters are Chinese (East Asian)."
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
            # Retry once
            print(f"  Retrying: {name}")
            if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
                assets[name] = path

    # Scene: meeting room
    p = os.path.join(out_dir, "scene-meeting.webp")
    prompt = (
        f"{scene_style}. {LOCATION_MEETING}. 9:16 vertical. No people. "
        "Warm indoor lighting, afternoon sun through windows."
    )
    print("  Generating: meeting room scene")
    if generate_asset(keys["gemini_key"], prompt, p, keys.get("gemini_base_url")):
        assets["scene-meeting"] = p

    # Scene: corridor
    p2 = os.path.join(out_dir, "scene-corridor.webp")
    prompt2 = (
        f"{scene_style}. {LOCATION_CORRIDOR}. 9:16 vertical. No people. "
        "Natural light from floor-to-ceiling windows, clean modern aesthetic."
    )
    print("  Generating: corridor scene")
    if generate_asset(keys["gemini_key"], prompt2, p2, keys.get("gemini_base_url")):
        assets["scene-corridor"] = p2

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
        if os.path.isfile(img):
            img = upload_to_tmpfiles(img)
        cmd.extend(["--image", img])

    env = os.environ.copy()
    if keys["ark_key"]:
        env["ARK_API_KEY"] = keys["ark_key"]

    print(f"  Prompt ({len(prompt)} chars): {prompt[:300]}...")
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
        print(f"EXP-V7-010 Version D — {args.style} — Step 1: Assets")
        print(f"{'='*60}")
        assets = generate_all_assets(keys, args.style, assets_dir)
        print(f"Generated {len(assets)} assets")
    else:
        assets = {}
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                if f.endswith(".webp"):
                    key = f.replace(".webp", "").replace("char-", "")
                    assets[key] = os.path.join(assets_dir, f)

    if args.skip_video:
        print("Skipping video generation.")
        return

    assert keys["ark_key"], "ARK_API_KEY not found"
    assert keys["seedance_script"], "seedance.py not found"

    # Step 2: Segment 1 — Meeting room confrontation
    print(f"\n{'='*60}")
    print(f"Step 2: Segment 1 — 撕毁协议 ({args.style})")
    print(f"{'='*60}")

    seg1_images = []
    img_refs = []
    idx = 1
    for name in ["陈锐", "赵鹏"]:
        if name in assets:
            seg1_images.append(assets[name])
            img_refs.append(f"@image{idx} as character {name}")
            idx += 1
    if "scene-meeting" in assets:
        seg1_images.append(assets["scene-meeting"])
        img_refs.append(f"@image{idx} as the meeting room background")

    seg1_prompt = (
        (", ".join(img_refs) + ". ") if img_refs else ""
    ) + (
        f"Physical state: {SEG1_PHYSICAL_STATE}\n"
        f"Camera: Medium close-up, meeting room interior, camera on table side angled 45 degrees toward 陈锐 (no axis crossing).\n\n"
        f"{SEG1_PARTS}\n\n"
        f"{CONSISTENCY_SUFFIX} "
        "Modern high-end meeting room with white conference table, grey chairs, floor-to-ceiling glass windows with city skyline. "
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

    # Step 4: Segment 2 — Corridor (Version D: FFA + PSE + video extension)
    print(f"\n{'='*60}")
    print(f"Step 4: Segment 2 — 底牌 ({args.style}, Version D)")
    print(f"{'='*60}")

    pse = PSE_ANIME if args.style == "anime" else PSE_REALISTIC

    seg2_images = [last_frame]  # FFA
    seg2_img_refs = ["@image1 as the first frame of this scene (continue from here)"]
    idx = 2
    for name in ["陈锐", "苏晴"]:
        if name in assets:
            seg2_images.append(assets[name])
            seg2_img_refs.append(f"@image{idx} as character {name}")
            idx += 1
    if "scene-corridor" in assets:
        seg2_images.append(assets["scene-corridor"])
        seg2_img_refs.append(f"@image{idx} as the corridor background")

    seg2_prompt = (
        ", ".join(seg2_img_refs) + ". "
        f"Extend @video1 by 15 seconds. "
        f"Continue seamlessly from this exact frame. "
        f"Scene transition: 陈锐 has just walked out of the meeting room into the corridor. "
        f"{pse}\n\n"
        f"Camera: Medium shot, corridor, camera near left-side floor-to-ceiling window (no axis crossing).\n\n"
        f"{SEG2_PARTS}\n\n"
        f"{CONSISTENCY_SUFFIX} "
        "Office corridor with grey marble floor, natural light from windows, white walls with abstract paintings, silver elevator at the end."
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
        "experiment": "EXP-V7-010",
        "strategy": "Version D (FFA + PSE + Crossfade)",
        "style": args.style,
        "story": "创业者逆袭 — 都市创业×搞笑热血",
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
