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
EXP-V7-021 — 情绪梯度跨Segment一致性 《融资大冒险》

Anime only (per Controller spec). Video-extension mode.
Seg1: 轻松幽默(咖啡馆)  →  Seg2: 紧张悬念(投资人办公室)

Key: Emotion gradient across segments. Different scenes + 1 new character in Seg2.

Usage:
    uv run scripts/exp_v7_021_runner.py
    uv run scripts/exp_v7_021_runner.py --skip-assets
    uv run scripts/exp_v7_021_runner.py --skip-seg1    # if seg1 already generated
"""

import json, os, subprocess, sys, time, re, argparse
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-021"

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
CHAR_CHENFEI = "中国男性，25岁，170cm，偏瘦，短寸头黑发，国字脸，戴黑框方形眼镜，穿蓝色格子衬衫外扎进浅色牛仔裤棕色皮带白色运动鞋，表情丰富"
CHAR_WANGLEI = "中国男性，27岁，178cm，微壮，中长发微卷蓬松黑色，圆脸，穿黑色连帽衫黑色运动裤白色跑鞋，双手常插兜或交叉抱胸，表情淡定"
CHAR_ZHAOZONG = "中国女性，40岁，165cm，短发齐耳干练利落黑色，方脸高颧骨，穿深灰色西装外套白色衬衫黑色铅笔裙黑色高跟鞋，右手戴银色手表，表情严肃"

LOCATION_SEG1 = "日式简约风格咖啡馆内部白天，靠窗双人座阳光透过落地玻璃窗洒在木桌上。桌上有两杯拿铁一台翻开的笔记本电脑几张写满字的A4纸。背景有其他顾客虚化暖黄色灯光木质装修。"
LOCATION_SEG2 = "现代写字楼高层会议室，深色长桌三面座椅。冷白色LED灯光，落地窗外城市天际线天色阴沉。桌上几份文件一瓶矿泉水。墙上挂着公司标志。"

SEG1_PSA = (
    "陈飞坐在靠窗位左侧身体前倾双手撑桌面上，笔记本电脑屏幕朝向自己。"
    "王磊坐在对面右侧身体后靠椅背双手抱胸表情无聊看着窗外。"
    "桌上有两杯拿铁和几张写满字的A4纸。"
)

SEG2_PSA = (
    "陈飞坐在会议桌左侧椅子上身体僵硬挺直双手交叉放桌面上笔记本电脑翻开放面前。"
    "王磊坐在陈飞右侧微微驼背双手放膝盖上低头看桌面。"
    "赵总坐在对面正中位置双手交叠放桌上表情严肃直视二人。"
)

# Seg1 Parts — 轻松幽默
SEG1_PARTS = """[Part 1] 咖啡馆暖黄灯光下陈飞身体前倾双手拍桌面兴奋地看着王磊。陈飞 says "咱这个项目绝对能融到钱，AI帮大学生写论文，刚需！" 王磊慢慢把目光从窗外移回来看着陈飞微微挑眉。

[Part 2] 王磊双手抱胸靠着椅背歪头看陈飞。王磊 says "上个月你说AI遛狗是刚需，上上个月说AI算命是刚需。" 陈飞一愣然后用手推了推眼镜嘿嘿笑了两声低头翻A4纸。

[Part 3] 陈飞从A4纸堆里抽出一张举到王磊面前用食指点着上面的数字。陈飞 says "你看这个市场规模，三千亿！我算过了第一年就能回本。" 王磊伸手把纸拿过来扫了一眼嘴角抽了一下。王磊 says "你这个三千亿是把全球大学生都算进去了吧。"

[Part 4] 陈飞站起来双手握拳放胸前摆出加油的姿势。陈飞 says "明天见投资人，你就负责技术讲解，我来画饼。" 王磊没动继续靠椅背。王磊抬手端起拿铁喝了一口放下杯子。"""

# Seg2 Parts — 紧张悬念（不同场景 + 新角色赵总）
SEG2_PARTS = """[Part 1] 冷白灯光下会议室安静。陈飞吞了一下口水双手在桌面下搓了搓转头看了王磊一眼。王磊微微点头。陈飞转回来清嗓子看向赵总。陈飞 says "赵总您好，我们的项目叫智学通。"

[Part 2] 赵总双手交叠不动表情没变眼神锐利盯着陈飞。赵总 says "你们的技术壁垒在哪里？市面上同类产品至少有二十个。" 陈飞嘴巴张了张没发出声音额头冒出细汗。

[Part 3] 王磊看到陈飞卡住坐直身体双手撑桌面开口。王磊 says "我们用了自研的语义分析引擎准确率比市面高15个百分点。" 赵总目光转向王磊微微眯眼嘴角没有任何变化。

[Part 4] 赵总沉默三秒低头翻了一页文件又抬头看着二人。陈飞和王磊对视一眼都咽了一下口水。赵总右手食指轻轻敲了一下桌面。赵总 says "说一个理由，让我在一分钟内不把你们赶出去。" """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def upload_to_tmpfiles(local_path: str) -> str:
    """Upload a local file to tmpfiles.org and return the direct download URL."""
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
    """Generate an image using Gemini."""
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
    """Call seedance.py to generate video."""
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
        # Check for content moderation block
        if "ContentFilterBlock" in (result.stderr or "") or "审核" in (result.stderr or "") or "PrivacyInformation" in (result.stderr or ""):
            print("  ⛔ CONTENT MODERATION BLOCK — abandoning this experiment per standing order")
            return "BLOCKED"
        return False


def concat_segments(seg1_path, seg2_path, output_path):
    """Concatenate two segments with re-encoding (fix audio concat)."""
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
    """Check if video has audio and return (audio_dur, video_dur)."""
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
    """Verify each segment individually has audio — standing order."""
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
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-seg1", action="store_true", help="Skip seg1 if already exists")
    args = parser.parse_args()

    keys = load_keys()
    if not keys["gemini_key"]:
        print("ERROR: No GEMINI_API_KEY"); sys.exit(1)
    if not keys["ark_key"]:
        print("ERROR: No ARK_API_KEY"); sys.exit(1)
    if not keys["seedance_script"]:
        print("ERROR: seedance.py not found"); sys.exit(1)

    out_dir = str(EXP_DIR / "output" / "anime")
    assets_dir = str(EXP_DIR / "output" / "shared-assets" / "anime")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(assets_dir, exist_ok=True)

    gen_log = {
        "experiment": "EXP-V7-021",
        "hypothesis": "H-351: 跨Segment情绪梯度对比(轻松→紧张)不会破坏角色/场景一致性",
        "story": "《融资大冒险》创业融资轻喜剧",
        "style": "anime",
        "mode": "video-extension",
        "concurrent": False,
        "segments": {},
        "issues": [],
        "timestamp_start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    # --- Step 1: Generate assets ---
    asset_paths = {}
    chars = {
        "陈飞": CHAR_CHENFEI,
        "王磊": CHAR_WANGLEI,
        "赵总": CHAR_ZHAOZONG,
    }
    if not args.skip_assets:
        print("=" * 60)
        print("Step 1: Generate character + scene assets (anime)")
        print("=" * 60)

        for name, desc in chars.items():
            path = os.path.join(assets_dir, f"char-{name}.webp")
            prompt = (
                f"Semi-realistic anime illustration character portrait for production. "
                f"9:16 vertical format. The character is: {desc}. "
                f"Soft studio lighting, clean gradient background. High detail, vibrant colors, cinematic anime quality. "
                f"Character is looking slightly to the left (not at camera). Upper body visible."
            )
            print(f"Generating: {name}")
            if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
                asset_paths[name] = path
            time.sleep(2)

        # Scene: Cafe
        cafe_path = os.path.join(assets_dir, "scene-cafe.webp")
        prompt = (
            f"Anime-style wide establishing shot of a cozy Japanese-style cafe interior. "
            f"9:16 vertical format. {LOCATION_SEG1} "
            f"No people in the scene. Semi-realistic anime illustration, warm color palette."
        )
        print("Generating: scene-cafe")
        if generate_asset(keys["gemini_key"], prompt, cafe_path, keys.get("gemini_base_url")):
            asset_paths["scene-cafe"] = cafe_path

        time.sleep(2)

        # Scene: Office
        office_path = os.path.join(assets_dir, "scene-office.webp")
        prompt = (
            f"Anime-style wide establishing shot of a modern cold-toned meeting room. "
            f"9:16 vertical format. {LOCATION_SEG2} "
            f"No people in the scene. Semi-realistic anime illustration, cool blue-grey color palette, tense atmosphere."
        )
        print("Generating: scene-office")
        if generate_asset(keys["gemini_key"], prompt, office_path, keys.get("gemini_base_url")):
            asset_paths["scene-office"] = office_path
    else:
        # Load existing assets
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                if f.endswith(".webp"):
                    if f.startswith("scene-"):
                        key = f.replace(".webp", "")
                    else:
                        key = f.replace(".webp", "").replace("char-", "")
                    asset_paths[key] = os.path.join(assets_dir, f)
        print(f"Loaded existing assets: {list(asset_paths.keys())}")

    gen_log["assets"] = {k: str(v) for k, v in asset_paths.items()}

    # --- Step 2: Generate Seg1 (anime) ---
    seg1_path = os.path.join(out_dir, "segment-01.mp4")

    if args.skip_seg1 and os.path.exists(seg1_path):
        print(f"\n--- Skipping Seg1 (already exists: {seg1_path}) ---")
    else:
        print("\n" + "=" * 60)
        print("Step 2: Generate Segment 1 — 咖啡馆轻松场景 (anime)")
        print("=" * 60)

        # Build Seg1 prompt
        img_refs = []
        seg1_images = []
        idx = 1
        for name in ["陈飞", "王磊"]:
            if name in asset_paths:
                img_refs.append(f"@image{idx} is character {name}: {chars.get(name, '')}")
                seg1_images.append(asset_paths[name])
                idx += 1
        if "scene-cafe" in asset_paths:
            img_refs.append(f"@image{idx} is the cafe scene background")
            seg1_images.append(asset_paths["scene-cafe"])
            idx += 1

        seg1_prompt = (
            " ".join(img_refs) + "\n\n"
            f"Anime-style animated scene, warm color palette, cozy cafe.\n"
            f"Physical state: {SEG1_PSA}\n"
            f"Camera: 中景侧面45度两人同框陈飞在左王磊在右\n\n"
            + SEG1_PARTS +
            "\n\nNo subtitles, no slow motion, no characters looking at camera. "
            "Normal speed movement and natural dialogue pacing. 9:16 vertical format. "
            "Warm interior lighting consistent throughout. All characters are Chinese East Asian."
        )
        gen_log["segments"]["seg1"] = {"prompt": seg1_prompt, "images": [str(p) for p in seg1_images]}

        seg1_ok = call_seedance(keys["seedance_script"], keys["ark_key"], seg1_prompt, seg1_images, seg1_path)
        if seg1_ok == "BLOCKED":
            gen_log["issues"].append("Seg1 blocked by content moderation — ABANDONING")
            gen_log["result"] = "ABANDONED_MODERATION"
            log_path = str(EXP_DIR / "generation-log.json")
            with open(log_path, "w") as f:
                json.dump(gen_log, f, indent=2, ensure_ascii=False)
            print("⛔ Experiment abandoned due to content moderation block")
            sys.exit(1)
        if not seg1_ok:
            gen_log["issues"].append("Seg1 generation failed")
            gen_log["result"] = "FAILED_SEG1"
            log_path = str(EXP_DIR / "generation-log.json")
            with open(log_path, "w") as f:
                json.dump(gen_log, f, indent=2, ensure_ascii=False)
            print("✗ Seg1 failed. Aborting.")
            sys.exit(1)

    # --- Step 3: Generate Seg2 (anime) — video extension ---
    print("\n" + "=" * 60)
    print("Step 3: Generate Segment 2 — 投资人办公室紧张场景 (anime, video extension)")
    print("=" * 60)

    # V7-020 lesson: anime Seg2 with image refs triggers PrivacyInformation block
    # Use video-only extension (no image refs)
    seg2_prompt = (
        f"Extend @video1 by 15 seconds. "
        f"Scene transitions from a warm cafe to a cold-toned modern meeting room. "
        f"The same two young Chinese men (陈飞 in blue plaid shirt, 王磊 in black hoodie) "
        f"now sit nervously at a meeting table facing a stern Chinese businesswoman in her 40s "
        f"(赵总: short black hair, dark grey suit). "
        f"Physical state: {SEG2_PSA}\n"
        f"Camera: 中景正面偏左，陈飞和王磊坐在近侧并排赵总在对面\n\n"
        + SEG2_PARTS +
        "\n\nMaintain exact same character appearances for 陈飞 and 王磊 from the previous segment. "
        "New character 赵总 is Chinese female 40s short hair grey suit. "
        "Cold blue-white lighting. Tense atmosphere. "
        "No subtitles, no slow motion, no characters looking at camera. "
        "Normal speed movement. 9:16 vertical format. "
        "All characters are Chinese East Asian."
    )

    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    gen_log["segments"]["seg2"] = {"prompt": seg2_prompt, "images": [], "mode": "video-extension-no-imageref"}

    seg2_ok = call_seedance(keys["seedance_script"], keys["ark_key"], seg2_prompt, [], seg2_path, input_video=seg1_path)

    if seg2_ok == "BLOCKED":
        gen_log["issues"].append("Seg2 blocked by content moderation — ABANDONING")
        gen_log["result"] = "ABANDONED_MODERATION"
        log_path = str(EXP_DIR / "generation-log.json")
        with open(log_path, "w") as f:
            json.dump(gen_log, f, indent=2, ensure_ascii=False)
        print("⛔ Experiment abandoned due to content moderation block")
        sys.exit(1)

    if not seg2_ok:
        gen_log["issues"].append("Seg2 generation failed")
        gen_log["result"] = "FAILED_SEG2"
        log_path = str(EXP_DIR / "generation-log.json")
        with open(log_path, "w") as f:
            json.dump(gen_log, f, indent=2, ensure_ascii=False)
        print("✗ Seg2 failed.")
        sys.exit(1)

    # --- Step 4: Audio checks ---
    print("\n--- Audio Checks ---")
    audio_issues = check_segment_audio(seg1_path, seg2_path)
    if audio_issues:
        for issue in audio_issues:
            print(f"  {issue}")
        gen_log["issues"].extend(audio_issues)

    # --- Step 5: Concatenate ---
    print("\n--- Concatenate ---")
    final_path = os.path.join(out_dir, "final-30s.mp4")
    if concat_segments(seg1_path, seg2_path, final_path):
        a_dur, v_dur = check_audio(final_path)
        if a_dur < v_dur * 0.9:
            msg = f"⛔ FINAL AUDIO CHECK FAILED: audio={a_dur:.1f}s video={v_dur:.1f}s"
            print(f"  {msg}")
            gen_log["issues"].append(msg)
        else:
            print(f"  ✓ Final audio OK: a={a_dur:.1f}s v={v_dur:.1f}s")
        print(f"  ✓ Final video: {final_path}")
        gen_log["result"] = "SUCCESS" if not audio_issues else "SUCCESS_WITH_AUDIO_ISSUES"
        gen_log["final_video"] = final_path
        gen_log["final_audio"] = {"audio_s": a_dur, "video_s": v_dur}
    else:
        gen_log["result"] = "FAILED_CONCAT"
        gen_log["issues"].append("Concatenation failed")

    # --- Save generation log ---
    gen_log["timestamp_end"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    log_path = str(EXP_DIR / "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(gen_log, f, indent=2, ensure_ascii=False)
    print(f"\nGeneration log: {log_path}")
    print("Done!")


if __name__ == "__main__":
    main()
