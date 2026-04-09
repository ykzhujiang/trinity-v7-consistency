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
EXP-V7-011 — 《面试翻车王》Comedy Dual Segment Consistency

Dual track: anime + realistic
Strategy: Version D (FFA + PSE + Crossfade)
Story: 社恐程序员面试说大实话，被录用

Usage:
    uv run scripts/exp_v7_011_runner.py --style anime
    uv run scripts/exp_v7_011_runner.py --style realistic
"""

import json, os, subprocess, sys, time, re
from pathlib import Path
from io import BytesIO

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-011"
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
# Characters & Location
# ---------------------------------------------------------------------------
CHARACTERS = {
    "小赵": "中国男性，25岁，170cm，偏瘦，柔软微卷黑色短发，圆脸带婴儿肥，单眼皮小眼睛，皮肤偏白，穿格子衬衫塞进卡其色休闲裤棕色运动鞋，黑色双肩包放在椅子旁",
    "HR姐姐": "中国女性，30岁，165cm，中等身材，黑色齐肩波波头，长脸高颧骨薄嘴唇，皮肤白皙，穿灰色职业西装内搭黑色高领，黑色细高跟，右手执黑色签字笔",
}

LOCATION = "科技公司面试间，白色极简风格，一张白色长桌两把灰色椅子面对面，桌上一杯水一份打印简历，落地窗外模糊城市天际线，天花板嵌入式白色灯光"

SEG1_PHYSICAL_STATE = (
    "小赵坐在白色长桌左侧灰色椅子上，双手放在膝盖上，背稍微佝偻，黑色双肩包放在椅子旁地上，视线低垂看桌面。"
    "HR姐姐坐在桌子对面右侧，身体端正，左手翻着桌上的打印简历，右手握黑色签字笔，视线朝下看简历。"
)

SEG2_PHYSICAL_STATE = (
    "小赵坐在白色长桌左侧灰色椅子上，身体微微后倾，双手搭在椅子扶手上，嘴唇紧闭正在思考。"
    "HR姐姐坐在对面，身体前倾，左肘撑桌面，右手握笔悬在简历上方，视线正对小赵，嘴角微微紧绷忍住笑意。"
)

SEG1_PARTS = """[Part 1] 小赵坐在椅子上，右手手指不停地摩擦裤腿侧缝，左手攥紧膝盖，肩膀微微耸起。HR姐姐低头翻简历，右手签字笔轻轻敲桌面两下。

[Part 2] HR姐姐抬头直视小赵方向，表情严肃职业化。HR姐姐 says "说说你最大的优点？" 小赵身体突然一僵，嘴巴比脑子快地脱口而出。小赵 says "我特别会摸鱼。" 小赵说完立刻双手捂住自己嘴巴，眼睛瞪得溜圆。

[Part 3] HR姐姐嘴角开始不受控制地抽搐，赶紧抬起左手拿起桌上的简历挡在脸前，假装在认真看内容。小赵双手从嘴上放下来疯狂摆手。小赵 says "我是说我效率特别高，空闲时间比较多……" HR姐姐简历后面的肩膀在微微抖动。

[Part 4] HR姐姐缓缓把简历放回桌上，脸已经憋得微微发红，努力恢复严肃表情，右手签字笔在简历上划了一下。HR姐姐 says "下一个问题——你为什么从上家离职？" 小赵听到问题后吞了一口口水，喉结明显上下滚动。"""

SEG2_PARTS = """[Part 1] 小赵歪头思考了两秒，然后突然坐直身体，用一种非常认真诚恳的表情直视HR姐姐方向。小赵 says "因为我发现老板的代码写得比我还烂。" HR姐姐右手的签字笔从手指间滑落，啪地掉到桌面上弹了一下。

[Part 2] 小赵意识到自己又说了大实话，整个人身体往椅子里缩，双手抓住椅子扶手，肩膀耸到耳朵旁边。HR姐姐弯腰到桌面下捡笔，借着桌子的遮挡偷偷笑出声，肩膀明显抖动。

[Part 3] HR姐姐坐直身体，深深吸了一口气，用力抿住嘴唇恢复专业表情，右手重新握紧签字笔。HR姐姐 says "最后一个问题，你的期望薪资？" 小赵认真地想了想，双手交叉放回膝盖上，非常诚恳地点了点头。小赵 says "够还花呗就行。"

[Part 4] HR姐姐终于忍不住笑出来，左手拍了一下桌面，身体前倾笑得肩膀直抖。HR姐姐 says "你被录用了。" 小赵整个人呆住，嘴巴微张，眨了两下眼睛。小赵 says "啊？真的？" HR姐姐边笑边摆手，用签字笔指了指小赵。HR姐姐 says "我们就缺一个敢说真话的。" 小赵脸上从懵逼慢慢绽放出一个傻笑。"""

# PSE for Segment 2
PSE_ANIME = (
    "Continuing exactly from the previous scene in the same interview room. "
    "[小赵] Chinese male 25 years old, thin, soft slightly curly black short hair, round baby face, "
    "single eyelid small eyes, fair skin, wearing plaid shirt tucked into khaki pants brown sneakers, "
    "sitting in grey chair left side of white table, leaning back slightly, hands on armrests, thinking. "
    "[HR姐姐] Chinese female 30 years old, medium build, black shoulder-length bob cut, "
    "long face high cheekbones thin lips, fair skin, grey professional blazer over black turtleneck, "
    "black stilettos, sitting across the table, leaning forward, left elbow on table, "
    "right hand holding black pen hovering over resume, suppressing a smile. "
    "Background: minimalist tech company interview room, white table, grey chairs, "
    "one glass of water and printed resume on table, floor-to-ceiling window with blurred city skyline. "
    "Anime style illustration."
)

PSE_REALISTIC = (
    "Continuing exactly from the previous scene in the same interview room. "
    "[小赵] Chinese male 25 years old, thin build, soft slightly curly black short hair, round baby face, "
    "single eyelid small eyes, fair skin, plaid shirt tucked into khaki pants brown sneakers, "
    "sitting left side of white table, leaning back, hands on armrests, pondering expression. "
    "[HR姐姐] Chinese female 30 years old, medium build, black shoulder-length bob, "
    "long face high cheekbones thin lips, fair skin, grey professional blazer black turtleneck, "
    "black stilettos, sitting across table, leaning forward, left elbow on table, "
    "right hand with black pen above resume, tight-lipped suppressing laughter. "
    "Same interview room, white minimalist, one table two chairs, resume and water glass on table, "
    "floor-to-ceiling window blurred cityscape. Cinematic realistic style."
)

CONSISTENCY_SUFFIX = (
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement, natural pacing. 9:16 vertical format. "
    "Consistent cool white office lighting throughout. All characters are Chinese (East Asian). "
    "Comedy tone — expressive faces, natural comedic timing."
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

    # Scene: interview room
    p = os.path.join(out_dir, "scene-interview.webp")
    prompt = (
        f"{scene_style}. {LOCATION}. 9:16 vertical. No people. "
        "Cool white office lighting, clean and modern."
    )
    print("  Generating: interview room scene")
    if generate_asset(keys["gemini_key"], prompt, p, keys.get("gemini_base_url")):
        assets["scene-interview"] = p

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
        print(f"EXP-V7-011 Version D — {args.style} — Step 1: Assets")
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

    # Step 2: Segment 1 — Interview comedy
    print(f"\n{'='*60}")
    print(f"Step 2: Segment 1 — 面试翻车 ({args.style})")
    print(f"{'='*60}")

    seg1_images = []
    img_refs = []
    idx = 1
    for name in ["小赵", "HR姐姐"]:
        if name in assets:
            seg1_images.append(assets[name])
            img_refs.append(f"@image{idx} as character {name}")
            idx += 1
    if "scene-interview" in assets:
        seg1_images.append(assets["scene-interview"])
        img_refs.append(f"@image{idx} as the interview room background")

    seg1_prompt = (
        (", ".join(img_refs) + ". ") if img_refs else ""
    ) + (
        f"Physical state: {SEG1_PHYSICAL_STATE}\n"
        f"Camera: Medium shot, interview room interior, camera slightly to the right side of the table angled toward 小赵 (no axis crossing). "
        f"Both characters visible in frame.\n\n"
        f"{SEG1_PARTS}\n\n"
        f"{CONSISTENCY_SUFFIX} "
        "Minimalist white interview room, white table, grey chairs, resume and water glass on table, "
        "floor-to-ceiling window with blurred city skyline outside."
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

    # Step 4: Segment 2 — Version D (FFA + PSE + video ext)
    print(f"\n{'='*60}")
    print(f"Step 4: Segment 2 — 录用反转 ({args.style}, Version D)")
    print(f"{'='*60}")

    pse = PSE_ANIME if args.style == "anime" else PSE_REALISTIC

    seg2_images = [last_frame]  # FFA
    seg2_img_refs = ["@image1 as the first frame of this scene (continue from here)"]
    idx = 2
    for name in ["小赵", "HR姐姐"]:
        if name in assets:
            seg2_images.append(assets[name])
            seg2_img_refs.append(f"@image{idx} as character {name}")
            idx += 1
    if "scene-interview" in assets:
        seg2_images.append(assets["scene-interview"])
        seg2_img_refs.append(f"@image{idx} as the interview room background")

    seg2_prompt = (
        ", ".join(seg2_img_refs) + ". "
        f"Extend @video1 by 15 seconds. "
        f"Continue seamlessly from this exact frame. "
        f"Same interview room, same characters, same positions. "
        f"{pse}\n\n"
        f"Camera: Same medium shot, same angle as previous segment (no axis crossing).\n\n"
        f"{SEG2_PARTS}\n\n"
        f"{CONSISTENCY_SUFFIX} "
        "Same minimalist white interview room, continuous scene."
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
        "experiment": "EXP-V7-011",
        "hypothesis": "H-126",
        "strategy": "Version D (FFA + PSE + Crossfade)",
        "style": args.style,
        "story": "面试翻车王 — 职场喜剧",
        "genre": "comedy",
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
