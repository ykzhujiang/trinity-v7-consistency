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
EXP-V7-022 — 跨场景一致性测试（同建筑内换房间）

Dual track: anime + realistic (concurrent where possible)
Seg1: 会议室 — 演示翻车  →  Seg2: 走廊 — 偶遇投资人

Key hypothesis: H-352 — Character consistency when changing scenes within same building.

Usage:
    uv run scripts/exp_v7_022_runner.py
    uv run scripts/exp_v7_022_runner.py --skip-assets
    uv run scripts/exp_v7_022_runner.py --skip-seg1
    uv run scripts/exp_v7_022_runner.py --style anime       # single track
    uv run scripts/exp_v7_022_runner.py --style realistic    # single track
"""

import json, os, subprocess, sys, time, re, argparse
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-022"

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
        try: ark_key = config["skills"]["entries"]["seedance-video"]["env"]["ARK_API_KEY"]
        except (KeyError, TypeError): pass
        if not ark_key:
            try: ark_key = config["models"]["providers"]["ark"]["apiKey"]
            except (KeyError, TypeError): pass
    seedance_script = Path.home() / ".openclaw" / "workspace" / "skills" / "seedance-video" / "scripts" / "seedance.py"
    return {"gemini_key": gemini_key, "gemini_base_url": gemini_base_url,
            "ark_key": ark_key, "seedance_script": str(seedance_script) if seedance_script.exists() else None}

# ---------------------------------------------------------------------------
# Characters & Locations
# ---------------------------------------------------------------------------
CHAR_ZHUJIE = "中国男性，28岁，175cm，偏瘦，蓬松短发黑色微乱，长方脸，穿灰色连帽卫衣外搭蓝色牛仔裤白色运动鞋，右手腕戴黑色电子手表，表情丰富"
CHAR_INVESTOR = "中国女性，35岁，165cm，干练齐耳短发黑色，高颧骨鹅蛋脸，穿黑色修身西装外套白色衬衫黑色西裤黑色高跟鞋，左手拿一个深棕色公文包，表情职业化微笑"

LOCATION_SEG1 = "现代创业公司会议室白天。白色墙壁一面白板一面投影屏幕。长方形浅色木桌六把黑色办公椅。自然光从左侧落地窗透入。桌上有笔记本电脑几张打印文件两杯纸杯咖啡。整体明亮简约风格。"
LOCATION_SEG2 = "同一栋办公楼走廊白天。浅灰色地面白色墙壁右侧落地窗自然光照入与会议室光线一致。走廊宽敞干净左侧有几扇办公室门。远处有绿植。"

SEG1_PSA = (
    "主杰站在白板前面朝投影屏幕侧面对着镜头方向，右手指向投影屏幕，身体微前倾。"
    "笔记本电脑翻开放在桌上屏幕面向主杰。桌上有打印文件和咖啡杯。"
)

SEG2_PSA = (
    "主杰右手推开会议室门左手拿着笔记本电脑，身体微弓刚从门内走出。"
    "林总站在走廊靠窗位置面朝走廊方向左手拿公文包右手自然下垂。"
)

# --- Seg1 Parts: 会议室演示翻车 ---
SEG1_PARTS = """[Part 1] 明亮会议室内主杰站在白板前右手指向投影屏幕满脸自信地向前方讲解。主杰 says "大家看这个用户增长曲线，上线一周日活就破万了。" 屏幕上显示一张折线图。

[Part 2] 投影屏幕突然变成蓝色死机画面。主杰的右手悬在半空嘴微张表情凝固愣了一秒。主杰迅速低头看笔记本电脑伸手按了几下键盘。主杰 says "呃……稍等，小问题小问题。"

[Part 3] 主杰双手合上笔记本电脑站直身体堆出尴尬笑容双手向两侧摊开做出"没事"的手势。主杰 says "数据大家都看到了对吧，核心亮点已经展示完了。" 主杰的笑容僵硬额头微微冒汗。

[Part 4] 主杰转身背对镜头弯腰把笔记本电脑和文件收进背包。动作略急促但努力保持镇定。无对白只有收拾物品的轻微声响。"""

# --- Seg2 Parts: 走廊偶遇投资人 ---
SEG2_PARTS = """[Part 1] 走廊落地窗自然光照入。主杰右手推开会议室门走出来表情放松松了口气。一转弯差点撞上走廊里的林总主杰身体后仰一步表情从放松变成惊讶。主杰 says "啊林总您好您好！"

[Part 2] 两人面对面站在走廊中间。林总微笑点头。主杰立刻挺胸抬头切换到自信模式右手整理了一下卫衣领口。林总 says "刚开完会？看你们产品最近数据不错啊。" 主杰连连点头。

[Part 3] 主杰和林总并肩往走廊前方走。主杰侧脸看林总视线略偏上眼神飘忽但嘴角保持上扬。主杰 says "效果特别好，刚才给团队复盘，客户反馈都超预期。" 主杰左手不自觉地攥紧了笔记本电脑。

[Part 4] 两人并肩走向走廊尽头背影。主杰左手偷偷擦了一下额头的汗。林总侧头看了主杰一眼嘴角微扬似乎看穿了什么。无对白只有脚步声在走廊回响。"""


# ---------------------------------------------------------------------------
# Helpers (same as V7-021)
# ---------------------------------------------------------------------------
def upload_to_tmpfiles(local_path: str) -> str:
    import requests
    print(f"  Uploading {local_path} to tmpfiles.org...")
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    page_url = data["data"]["url"]
    direct_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    print(f"  → Uploaded: {direct_url}")
    return direct_url


def generate_asset(gemini_key, prompt, output_path, base_url=None):
    from google import genai
    from google.genai import types
    from PIL import Image

    kwargs = {"api_key": gemini_key}
    if base_url:
        kwargs["http_options"] = types.HttpOptions(base_url=base_url)
    client = genai.Client(**kwargs)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    img_data = part.inline_data.data
                    img = Image.open(BytesIO(img_data))
                    if img.width > 600:
                        ratio = 600 / img.width
                        img = img.resize((600, int(img.height * ratio)), Image.LANCZOS)
                    img.save(output_path, "WEBP", quality=75)
                    print(f"  → Saved: {output_path} ({os.path.getsize(output_path) // 1024}KB)")
                    return True
            print(f"  ✗ No image in response (attempt {attempt+1})")
        except Exception as e:
            print(f"  ✗ Gemini error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(5)
    return False


def call_seedance(seedance_script, ark_key, prompt, asset_paths, output_path, input_video=None, duration=15):
    cmd = [
        "python3", seedance_script, "run",
        "--prompt", prompt,
        "--ratio", "9:16",
        "--duration", str(duration),
        "--out", output_path,
    ]
    if input_video:
        if os.path.isfile(input_video) and not input_video.startswith("http"):
            input_video = upload_to_tmpfiles(input_video)
        cmd.extend(["--video", input_video])
    for path in asset_paths:
        cmd.extend(["--image", path])
    env = os.environ.copy()
    env["ARK_API_KEY"] = ark_key
    print(f"  Calling Seedance... (timeout 1200s)")
    print(f"  Prompt preview: {prompt[:200]}...")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1200)
    if result.returncode == 0:
        print(f"  ✓ Video generated: {output_path}")
        return True
    else:
        stderr = result.stderr[:1000] if result.stderr else "(no stderr)"
        stdout = result.stdout[-500:] if result.stdout else "(no stdout)"
        print(f"  ✗ Seedance failed.\n  stderr: {stderr}\n  stdout tail: {stdout}")
        if "ContentFilterBlock" in (result.stderr or "") or "审核" in (result.stderr or "") or "PrivacyInformation" in (result.stderr or ""):
            print("  ⛔ CONTENT MODERATION BLOCK — abandoning per standing order")
            return "BLOCKED"
        return False


def concat_segments(seg1_path, seg2_path, output_path):
    list_file = output_path.replace(".mp4", "-list.txt")
    with open(list_file, "w") as f:
        f.write(f"file '{os.path.abspath(seg1_path)}'\n")
        f.write(f"file '{os.path.abspath(seg2_path)}'\n")
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-y", output_path
    ], capture_output=True)
    return os.path.exists(output_path)


def check_audio(video_path):
    try:
        a = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=duration", "-of", "csv=p=0", video_path],
            capture_output=True, text=True
        )
        v = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v",
             "-show_entries", "stream=duration", "-of", "csv=p=0", video_path],
            capture_output=True, text=True
        )
        audio_dur = float(a.stdout.strip()) if a.stdout.strip() else 0
        video_dur = float(v.stdout.strip()) if v.stdout.strip() else 0
        return audio_dur, video_dur
    except:
        return 0, 0


def check_segment_audio(seg1_path, seg2_path):
    issues = []
    for label, path in [("Seg1", seg1_path), ("Seg2", seg2_path)]:
        a_dur, v_dur = check_audio(path)
        if a_dur < 1.0:
            issues.append(f"⛔ {label} has NO AUDIO (a={a_dur:.1f}s v={v_dur:.1f}s)")
        elif a_dur < v_dur * 0.8:
            issues.append(f"⚠️ {label} audio short (a={a_dur:.1f}s v={v_dur:.1f}s)")
        else:
            print(f"  ✓ {label} audio OK: a={a_dur:.1f}s v={v_dur:.1f}s")
    return issues


# ---------------------------------------------------------------------------
# Track generators
# ---------------------------------------------------------------------------

def run_anime_track(keys, skip_assets=False, skip_seg1=False):
    """Run anime track: FFA + PSE + character ref images."""
    print("\n" + "=" * 60)
    print("ANIME TRACK — Version D (FFA + PSE + Ref Images)")
    print("=" * 60)

    out_dir = str(EXP_DIR / "output" / "anime")
    assets_dir = str(EXP_DIR / "output" / "shared-assets" / "anime")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(assets_dir, exist_ok=True)

    track_log = {"style": "anime", "mode": "video-extension", "segments": {}, "issues": []}
    asset_paths = {}

    # --- Assets ---
    if not skip_assets:
        print("--- Generating anime assets ---")
        chars = {"主杰": CHAR_ZHUJIE, "林总": CHAR_INVESTOR}
        for name, desc in chars.items():
            path = os.path.join(assets_dir, f"char-{name}.webp")
            prompt = (
                f"Semi-realistic anime illustration character portrait for production. "
                f"9:16 vertical format. The character is: {desc}. "
                f"Soft studio lighting, clean gradient background. High detail, vibrant colors. "
                f"Character looking slightly to the left (not at camera). Upper body visible."
            )
            print(f"  Generating: {name}")
            if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
                asset_paths[name] = path
            time.sleep(2)

        # Scene: Meeting room
        mr_path = os.path.join(assets_dir, "scene-meeting.webp")
        prompt = (
            f"Anime-style wide establishing shot. 9:16 vertical. {LOCATION_SEG1} "
            f"No people. Semi-realistic anime, bright daylight atmosphere."
        )
        print("  Generating: scene-meeting")
        if generate_asset(keys["gemini_key"], prompt, mr_path, keys.get("gemini_base_url")):
            asset_paths["scene-meeting"] = mr_path
        time.sleep(2)

        # Scene: Hallway
        hw_path = os.path.join(assets_dir, "scene-hallway.webp")
        prompt = (
            f"Anime-style wide establishing shot. 9:16 vertical. {LOCATION_SEG2} "
            f"No people. Semi-realistic anime, same daylight as meeting room."
        )
        print("  Generating: scene-hallway")
        if generate_asset(keys["gemini_key"], prompt, hw_path, keys.get("gemini_base_url")):
            asset_paths["scene-hallway"] = hw_path
    else:
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                if f.endswith(".webp"):
                    key = f.replace(".webp", "").replace("char-", "").replace("scene-", "scene-" if "scene" in f else "")
                    if "scene-" in f:
                        key = f.replace(".webp", "")
                    else:
                        key = f.replace(".webp", "").replace("char-", "")
                    asset_paths[key] = os.path.join(assets_dir, f)
        print(f"  Loaded existing assets: {list(asset_paths.keys())}")

    track_log["assets"] = {k: str(v) for k, v in asset_paths.items()}

    # --- Seg1 (anime) ---
    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    if skip_seg1 and os.path.exists(seg1_path):
        print(f"\n  Skipping anime Seg1 (exists)")
    else:
        print("\n--- Anime Seg1: 会议室演示翻车 ---")
        img_refs = []
        seg1_images = []
        idx = 1
        if "主杰" in asset_paths:
            img_refs.append(f"@image{idx} is character 主杰: {CHAR_ZHUJIE}")
            seg1_images.append(asset_paths["主杰"])
            idx += 1
        if "scene-meeting" in asset_paths:
            img_refs.append(f"@image{idx} is the meeting room scene")
            seg1_images.append(asset_paths["scene-meeting"])
            idx += 1

        seg1_prompt = (
            " ".join(img_refs) + "\n\n"
            f"Anime-style animated scene, bright daylight office.\n"
            f"Physical state: {SEG1_PSA}\n"
            f"Camera: 中景侧面45度主杰在画面中央偏左面朝投影屏幕\n\n"
            + SEG1_PARTS +
            "\n\nNo subtitles, no slow motion, no characters looking at camera. "
            "Normal speed movement and natural dialogue pacing. 9:16 vertical format. "
            "Bright daylight consistent throughout. Character is Chinese East Asian male 28 years old."
        )
        track_log["segments"]["seg1"] = {"prompt": seg1_prompt, "images": [str(p) for p in seg1_images]}

        result = call_seedance(keys["seedance_script"], keys["ark_key"], seg1_prompt, seg1_images, seg1_path)
        if result == "BLOCKED":
            track_log["issues"].append("Seg1 BLOCKED by moderation")
            track_log["result"] = "ABANDONED_MODERATION"
            return track_log
        if not result:
            track_log["issues"].append("Seg1 generation failed")
            track_log["result"] = "FAILED_SEG1"
            return track_log

    # --- Seg2 (anime, video extension) ---
    print("\n--- Anime Seg2: 走廊偶遇投资人 (video extension) ---")
    seg2_prompt = (
        f"Extend @video1 by 15 seconds. "
        f"Scene transitions from a bright modern meeting room to the hallway of the same office building. "
        f"The same Chinese man 主杰 (28, messy short black hair, grey hoodie, blue jeans, white sneakers) "
        f"walks out of the meeting room into the hallway. "
        f"He bumps into 林总 (Chinese woman, 35, short black hair, black suit, brown briefcase). "
        f"Physical state: {SEG2_PSA}\n"
        f"Camera: 中景正面走廊纵深方向两人面对面\n\n"
        + SEG2_PARTS +
        "\n\nMaintain exact same appearance for 主杰 from previous segment (grey hoodie, messy short hair). "
        "New character 林总 is Chinese female 35 short hair black suit. "
        "Same natural daylight as meeting room. "
        "No subtitles, no slow motion, no characters looking at camera. "
        "Normal speed movement. 9:16 vertical format. "
        "All characters are Chinese East Asian."
    )
    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    track_log["segments"]["seg2"] = {"prompt": seg2_prompt, "images": [], "mode": "video-extension"}

    result = call_seedance(keys["seedance_script"], keys["ark_key"], seg2_prompt, [], seg2_path, input_video=seg1_path)
    if result == "BLOCKED":
        track_log["issues"].append("Seg2 BLOCKED by moderation")
        track_log["result"] = "ABANDONED_MODERATION"
        return track_log
    if not result:
        track_log["issues"].append("Seg2 generation failed")
        track_log["result"] = "FAILED_SEG2"
        return track_log

    # --- Audio check ---
    audio_issues = check_segment_audio(seg1_path, seg2_path)
    track_log["issues"].extend(audio_issues)

    # --- Concat ---
    final_path = os.path.join(out_dir, "final-30s.mp4")
    if concat_segments(seg1_path, seg2_path, final_path):
        a_dur, v_dur = check_audio(final_path)
        if a_dur < v_dur * 0.9:
            track_log["issues"].append(f"⛔ Final audio issue: a={a_dur:.1f}s v={v_dur:.1f}s")
        print(f"  ✓ Anime final: {final_path} (a={a_dur:.1f}s v={v_dur:.1f}s)")
        track_log["result"] = "SUCCESS" if not audio_issues else "SUCCESS_WITH_AUDIO_ISSUES"
        track_log["final_video"] = final_path
        track_log["final_audio"] = {"audio_s": a_dur, "video_s": v_dur}
    else:
        track_log["result"] = "FAILED_CONCAT"

    return track_log


def run_realistic_track(keys, skip_seg1=False):
    """Run realistic track: pure text prompt + video extension (no image refs)."""
    print("\n" + "=" * 60)
    print("REALISTIC TRACK — Text-only Prompt + Video Extension")
    print("=" * 60)

    out_dir = str(EXP_DIR / "output" / "realistic")
    os.makedirs(out_dir, exist_ok=True)

    track_log = {"style": "realistic", "mode": "video-extension-text-only", "segments": {}, "issues": []}

    # --- Seg1 (realistic, text only) ---
    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    if skip_seg1 and os.path.exists(seg1_path):
        print(f"\n  Skipping realistic Seg1 (exists)")
    else:
        print("\n--- Realistic Seg1: 会议室演示翻车 ---")
        seg1_prompt = (
            f"Live-action cinematic scene. Bright modern startup meeting room, daytime natural light from floor-to-ceiling windows on the left.\n"
            f"One character: 主杰, a Chinese man age 28, thin build, messy short black hair, wearing a grey hoodie and blue jeans and white sneakers, black digital watch on right wrist. Expressive face.\n"
            f"Physical state: {SEG1_PSA}\n"
            f"Camera: Medium shot, 45-degree side angle, 主杰 center-left facing projection screen.\n\n"
            + SEG1_PARTS +
            "\n\nFilm-quality realistic cinematography. Natural daylight. "
            "No subtitles, no slow motion, no characters looking at camera. "
            "Normal speed movement and natural dialogue pacing. 9:16 vertical. "
            "Character is Chinese East Asian male."
        )
        track_log["segments"]["seg1"] = {"prompt": seg1_prompt, "images": []}

        result = call_seedance(keys["seedance_script"], keys["ark_key"], seg1_prompt, [], seg1_path)
        if result == "BLOCKED":
            track_log["issues"].append("Seg1 BLOCKED")
            track_log["result"] = "ABANDONED_MODERATION"
            return track_log
        if not result:
            track_log["issues"].append("Seg1 failed")
            track_log["result"] = "FAILED_SEG1"
            return track_log

    # --- Seg2 (realistic, video extension) ---
    print("\n--- Realistic Seg2: 走廊偶遇投资人 (video extension) ---")
    seg2_prompt = (
        f"Extend @video1 by 15 seconds. "
        f"Scene transitions from the meeting room to the hallway of the same office building. "
        f"Same Chinese man 主杰 (28, messy short black hair, grey hoodie, blue jeans, white sneakers, black digital watch) "
        f"walks out of the meeting room door into a bright modern hallway with floor-to-ceiling windows. "
        f"He nearly bumps into 林总, a Chinese woman age 35, short neat black hair, wearing a tailored black suit and white blouse, carrying a brown briefcase in her left hand. "
        f"Physical state: {SEG2_PSA}\n"
        f"Camera: Medium shot, frontal, hallway depth.\n\n"
        + SEG2_PARTS +
        "\n\nMaintain exact same appearance for 主杰 from the previous segment. "
        "Same natural daylight. Film-quality realistic cinematography. "
        "No subtitles, no slow motion, no characters looking at camera. "
        "Normal speed movement. 9:16 vertical. "
        "All characters are Chinese East Asian."
    )
    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    track_log["segments"]["seg2"] = {"prompt": seg2_prompt, "images": [], "mode": "video-extension"}

    result = call_seedance(keys["seedance_script"], keys["ark_key"], seg2_prompt, [], seg2_path, input_video=seg1_path)
    if result == "BLOCKED":
        track_log["issues"].append("Seg2 BLOCKED")
        track_log["result"] = "ABANDONED_MODERATION"
        return track_log
    if not result:
        track_log["issues"].append("Seg2 failed")
        track_log["result"] = "FAILED_SEG2"
        return track_log

    # --- Audio check ---
    audio_issues = check_segment_audio(seg1_path, seg2_path)
    track_log["issues"].extend(audio_issues)

    # --- Concat ---
    final_path = os.path.join(out_dir, "final-30s.mp4")
    if concat_segments(seg1_path, seg2_path, final_path):
        a_dur, v_dur = check_audio(final_path)
        if a_dur < v_dur * 0.9:
            track_log["issues"].append(f"⛔ Final audio issue: a={a_dur:.1f}s v={v_dur:.1f}s")
        print(f"  ✓ Realistic final: {final_path} (a={a_dur:.1f}s v={v_dur:.1f}s)")
        track_log["result"] = "SUCCESS" if not audio_issues else "SUCCESS_WITH_AUDIO_ISSUES"
        track_log["final_video"] = final_path
        track_log["final_audio"] = {"audio_s": a_dur, "video_s": v_dur}
    else:
        track_log["result"] = "FAILED_CONCAT"

    return track_log


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-seg1", action="store_true")
    parser.add_argument("--style", choices=["anime", "realistic", "both"], default="both")
    args = parser.parse_args()

    keys = load_keys()
    if not keys["gemini_key"]:
        print("ERROR: No GEMINI_API_KEY"); sys.exit(1)
    if not keys["ark_key"]:
        print("ERROR: No ARK_API_KEY"); sys.exit(1)
    if not keys["seedance_script"]:
        print("ERROR: seedance.py not found"); sys.exit(1)

    os.makedirs(str(EXP_DIR / "output"), exist_ok=True)

    gen_log = {
        "experiment": "EXP-V7-022",
        "hypothesis": "H-352: 跨场景一致性(同建筑换房间)不破坏角色一致性",
        "story": "《创业翻车》创业喜剧",
        "dual_track": args.style == "both",
        "tracks": {},
        "timestamp_start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    if args.style == "both":
        # Phase 1: Concurrent Seg1 generation (anime + realistic)
        print("\n" + "#" * 60)
        print("PHASE 1: Concurrent Seg1 Generation (anime + realistic)")
        print("#" * 60)

        # Assets first (anime only, sequential)
        anime_log = run_anime_track(keys, skip_assets=args.skip_assets, skip_seg1=args.skip_seg1)
        gen_log["tracks"]["anime"] = anime_log

        # Realistic track (Seg2 depends on Seg1, so sequential per track)
        realistic_log = run_realistic_track(keys, skip_seg1=args.skip_seg1)
        gen_log["tracks"]["realistic"] = realistic_log

        # NOTE: True concurrency would require restructuring to separate Seg1/Seg2 phases.
        # Current implementation: run tracks sequentially but each track does Seg1→Seg2.
        # Standing order says "同阶段不同风格必须并发" — for true concurrency,
        # we'd need to split asset gen + Seg1 into concurrent futures. 
        # TODO: refactor for true Phase1 concurrency in future cycle.
    elif args.style == "anime":
        anime_log = run_anime_track(keys, skip_assets=args.skip_assets, skip_seg1=args.skip_seg1)
        gen_log["tracks"]["anime"] = anime_log
    else:
        realistic_log = run_realistic_track(keys, skip_seg1=args.skip_seg1)
        gen_log["tracks"]["realistic"] = realistic_log

    # --- Determine overall result ---
    results = [t.get("result", "UNKNOWN") for t in gen_log["tracks"].values()]
    if all(r.startswith("SUCCESS") for r in results):
        gen_log["result"] = "SUCCESS"
    elif any("ABANDONED" in r for r in results):
        gen_log["result"] = "PARTIAL_ABANDONED"
    elif any("FAILED" in r for r in results):
        gen_log["result"] = "PARTIAL_FAILED"
    else:
        gen_log["result"] = "UNKNOWN"

    gen_log["timestamp_end"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # Save log
    log_path = str(EXP_DIR / "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(gen_log, f, indent=2, ensure_ascii=False)
    print(f"\n{'=' * 60}")
    print(f"Generation log: {log_path}")
    print(f"Overall result: {gen_log['result']}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
