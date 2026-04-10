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
EXP-V7-013 — 《合伙人》3-Character Consistency Stress Test

Dual track: anime + realistic
Strategy: Version D (FFA + PSE + Crossfade)
Story: 3合伙人讨论收购，全家桶反转

Usage:
    uv run scripts/exp_v7_013_runner.py --style anime
    uv run scripts/exp_v7_013_runner.py --style realistic
"""

import json, os, subprocess, sys, time, re
from pathlib import Path
from io import BytesIO

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-013"
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
# Characters & Location (3 characters!)
# ---------------------------------------------------------------------------
CHARACTERS = {
    "林远": "中国男性，28岁，178cm，瘦高偏瘦，黑色短发整齐利落，长方脸，戴黑框方形眼镜，皮肤偏白，下巴尖削，眉毛浓密，穿深蓝色修身西装白色衬衫无领带，西装口袋露白色口袋巾",
    "苏晴": "中国女性，26岁，163cm，偏瘦，齐肩黑色短发微卷外翻，瓜子脸，淡妆眉毛细长眼睛明亮，穿灰色宽松卫衣深蓝牛仔裤白色运动鞋，黑色双肩包放在椅子旁",
    "胖虎": "中国男性，30岁，175cm，壮实微胖，寸头黑发，圆脸肉嘟嘟小眼睛，皮肤偏黑，络腮胡茬，穿红蓝花纹夏威夷衬衫卡其短裤棕色人字拖",
}

LOCATION = "创业公司简约现代小会议室，白色墙壁，白板上写满彩色数据流程图，浅木色长方桌4把灰色办公椅，桌上散落笔记本电脑纸杯咖啡文件，左侧玻璃门右侧落地窗看城市天际线日间，暖色调吊灯光线"

SEG1_PHYSICAL_STATE = (
    "林远坐桌子右侧靠窗，身体端正双手交叉放桌上，黑框眼镜反射白板光。"
    "苏晴坐林远对面靠门位置，身体前倾左手撑桌看笔记本屏幕右手划触控板。"
    "胖虎坐桌子短边远端，半躺椅子上右手拿鸡腿啃左手拿手机。"
)

SEG2_PHYSICAL_STATE = (
    "林远坐桌子右侧靠窗（同Seg1），身体微转向门方向，左手搭椅子扶手右手扶黑框眼镜。"
    "苏晴站起半个身子左手撑桌面视线望向玻璃门。"
    "胖虎还是半躺姿势鸡腿骨放桌上纸巾旁双手背在脑后嘴角上翘。"
)

SEG1_PARTS = """[Part 1] 林远坐直身体双手交叉放桌上表情严肃看白板。白板写着"收购要约 ¥5000万"被红笔圈起。林远深吸一口气目光从白板移到苏晴方向。林远 says "我觉得应该拒绝。"

[Part 2] 苏晴猛地从笔记本屏幕抬头左手食指还停在触控板上眉头紧皱。苏晴 says "拒绝？账上的钱只够撑三个月。" 苏晴右手指向笔记本屏幕转向林远方向。苏晴 says "你看看这个现金流。"

[Part 3] 胖虎嘴里嚼着鸡腿含糊不清地插话。胖虎抬起拿鸡腿的右手挥了挥。胖虎 says "钱的事我来搞定。" 林远和苏晴同时转头看胖虎表情半信半疑。

[Part 4] 胖虎慢悠悠掏出手机油乎乎的手指在屏幕上划了两下露出神秘的笑。胖虎 says "我约了个人。" 门外传来门铃声。三人目光同时看向玻璃门方向。"""

SEG2_PARTS = """[Part 1] 玻璃门打开一个穿蓝色制服的外卖小哥探头进来手里提两大袋外卖。苏晴表情从期待变困惑嘴巴微张。林远扶眼镜的手停在半空眨了两下眼。胖虎拍一下大腿站起来。胖虎 says "全家桶到了！"

[Part 2] 三人坐回原位桌上摆满炸鸡桶和薯条。胖虎两手各抓一个鸡腿大口啃。林远无奈摇头但还是拿起一块鸡翅小口咬。苏晴一边吃薯条一边看笔记本。苏晴突然手指停住眼睛越睁越大。苏晴 says "等等。"

[Part 3] 苏晴把薯条放下两手抓住笔记本转向林远方向语速加快眼睛发亮。苏晴 says "我发现一个漏洞，能省百分之四十的成本！" 林远放下鸡翅身体前倾凑过去看屏幕眼镜反光。胖虎嘴里塞满鸡肉含糊地说。胖虎 says "我就说吃饱了才能想出好主意。"

[Part 4] 林远慢慢坐直看了一眼胖虎又看苏晴嘴角终于露出笑容。林远 says "拒绝收购。" 苏晴点头转回屏幕继续敲键盘。胖虎举起鸡腿当话筒。胖虎 says "合伙人干杯！" 三人各举手里食物碰在一起笑成一团。"""

# PSE for Segment 2
PSE_ANIME = (
    "Continuing exactly from previous scene in same startup meeting room. "
    "[林远] Chinese male 28yo, tall thin, neat short black hair, rectangular face, BLACK SQUARE GLASSES, "
    "fair skin, sharp chin, thick eyebrows, dark blue fitted suit white shirt no tie, white pocket square. "
    "Sitting right side of table by window, body turned slightly toward door, left hand on armrest, right hand adjusting glasses. "
    "[苏晴] Chinese female 26yo, thin, shoulder-length black hair with slight outward curl, oval face, "
    "light makeup, bright alert eyes, wearing grey oversized hoodie dark blue jeans white sneakers. "
    "Standing up halfway, left hand on table, looking toward glass door. "
    "[胖虎] Chinese male 30yo, stocky chubby, buzz cut black hair, round chubby face small eyes, "
    "dark skin, stubble, wearing RED-BLUE HAWAIIAN SHIRT khaki shorts brown flip-flops. "
    "Reclining in chair at far end of table, chicken bone on napkin on table, hands behind head, smirking. "
    "Background: same startup meeting room, whiteboard with colorful data, light wood table 4 grey chairs, "
    "laptops coffee cups papers on table, glass door left side, floor-to-ceiling window right side city skyline. "
    "Anime style illustration."
)

PSE_REALISTIC = (
    "Continuing exactly from previous scene in same startup meeting room. "
    "[林远] Chinese male 28yo, tall thin, neat short black hair, rectangular face, BLACK SQUARE GLASSES, "
    "fair skin, sharp chin, thick eyebrows, dark blue fitted suit white shirt no tie, white pocket square. "
    "Sitting right side by window, turning toward door, left hand on armrest, right hand on glasses. "
    "[苏晴] Chinese female 26yo, thin, shoulder-length black hair slight outward curl, oval face, "
    "light makeup, bright eyes, grey oversized hoodie dark blue jeans white sneakers. "
    "Standing halfway, left hand on table, looking toward glass door. "
    "[胖虎] Chinese male 30yo, stocky chubby, buzz cut, round face small eyes, "
    "dark skin, stubble, RED-BLUE HAWAIIAN SHIRT khaki shorts brown flip-flops. "
    "Reclining at far end, chicken bone on napkin, hands behind head, smirking. "
    "Same meeting room, whiteboard with data, light wood table, grey chairs, "
    "laptops coffee papers, glass door left, window right city skyline. "
    "Cinematic realistic style."
)

CONSISTENCY_SUFFIX = (
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement, natural pacing. 9:16 vertical format. "
    "Consistent warm indoor lighting throughout. All characters are Chinese (East Asian). "
    "Comedy tone — expressive faces, natural comedic timing. "
    "THREE characters always visible: glasses-man (right/window), hoodie-girl (left/door), hawaiian-shirt-guy (far end)."
)

# ---------------------------------------------------------------------------
# Asset generation
# ---------------------------------------------------------------------------
def generate_asset(gemini_key, prompt, output_path, base_url=None):
    from google import genai
    from google.genai import types
    from PIL import Image
    import signal

    kwargs = {"api_key": gemini_key}
    if base_url:
        kwargs["http_options"] = types.HttpOptions(base_url=base_url, timeout=120000)
    client = genai.Client(**kwargs)

    try:
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
    except Exception as e:
        print(f"  ✗ Gemini error: {e}")
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
        for attempt in range(5):
            ok = generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url"))
            if ok:
                assets[name] = path
                break
            wait = 15 * (attempt + 1)
            print(f"  Retry {attempt+1} for {name}... (waiting {wait}s)")
            time.sleep(wait)

    # Scene: meeting room
    p = os.path.join(out_dir, "scene-meeting.webp")
    prompt = (
        f"{scene_style}. {LOCATION}. 9:16 vertical. No people. "
        "Warm office lighting, whiteboard with colorful data visible."
    )
    print("  Generating: meeting room scene")
    for attempt in range(5):
        if generate_asset(keys["gemini_key"], prompt, p, keys.get("gemini_base_url")):
            assets["scene-meeting"] = p
            break
        wait = 15 * (attempt + 1)
        print(f"  Retry {attempt+1} for scene... (waiting {wait}s)")
        time.sleep(wait)

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
    
    if result.returncode != 0:
        stderr = result.stderr
        # Check for content moderation block
        if "内容审核" in stderr or "content moderation" in stderr.lower() or "审核" in stderr or "blocked" in stderr.lower():
            print(f"  ⛔ MODERATION BLOCK — abandoning this experiment immediately per standing order")
            return "MODERATION_BLOCKED"
        print(f"  ✗ Failed: {stderr[:500]}")
        return False
    
    print(f"  ✓ Video: {output_path}")
    return True


def concat_with_audio_check(seg1, seg2, output, fade=0.4):
    """Crossfade concat with mandatory audio check per standing order."""
    # Get seg1 duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", seg1],
        capture_output=True, text=True)
    dur = float(probe.stdout.strip())
    offset = dur - fade

    # Check each segment has audio BEFORE concat
    for label, path in [("Seg1", seg1), ("Seg2", seg2)]:
        audio_probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, text=True)
        if not audio_probe.stdout.strip():
            print(f"  ⛔ {label} has NO AUDIO TRACK — cannot deliver per standing order")
            return False

    # Re-encode concat (not stream copy, to preserve both audio tracks)
    result = subprocess.run([
        "ffmpeg", "-i", seg1, "-i", seg2,
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={fade}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={fade}[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-y", output
    ], capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: simple concat without crossfade audio
        print(f"  Crossfade audio failed, trying simple concat...")
        concat_list = output.replace(".mp4", "-list.txt")
        with open(concat_list, "w") as f:
            f.write(f"file '{os.path.abspath(seg1)}'\n")
            f.write(f"file '{os.path.abspath(seg2)}'\n")
        result = subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", output
        ], capture_output=True, text=True)

    if result.returncode == 0:
        # Final audio verification
        audio_dur_probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=duration", "-of", "csv=p=0", output],
            capture_output=True, text=True)
        video_dur_probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v",
             "-show_entries", "stream=duration", "-of", "csv=p=0", output],
            capture_output=True, text=True)
        a_dur = float(audio_dur_probe.stdout.strip()) if audio_dur_probe.stdout.strip() else 0
        v_dur = float(video_dur_probe.stdout.strip()) if video_dur_probe.stdout.strip() else 0
        if a_dur < v_dur * 0.9:
            print(f"  ⛔ AUDIO CHECK FAILED: audio={a_dur:.1f}s video={v_dur:.1f}s")
            return False
        print(f"  ✓ Crossfade done: {output} (audio={a_dur:.1f}s video={v_dur:.1f}s)")
        return True

    print(f"  ✗ Concat failed: {result.stderr[:300]}")
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
        print(f"EXP-V7-013 Version D — {args.style} — Step 1: Assets")
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

    # Step 2: Segment 1 — 紧张谈判 (3 characters!)
    print(f"\n{'='*60}")
    print(f"Step 2: Segment 1 — 紧张谈判 ({args.style})")
    print(f"{'='*60}")

    seg1_images = []
    img_refs = []
    idx = 1
    for name in ["林远", "苏晴", "胖虎"]:
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
        f"Camera: Medium-wide shot from table's long side, all three characters visible. "
        f"林远 (glasses, blue suit) right side by window, 苏晴 (hoodie) left side by door, "
        f"胖虎 (hawaiian shirt, stocky) at far end of table. Camera at seated eye level.\n\n"
        f"{SEG1_PARTS}\n\n"
        f"{CONSISTENCY_SUFFIX}"
    )

    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    seg1_ok = call_seedance(keys, seg1_prompt, seg1_images, seg1_path)
    if seg1_ok == "MODERATION_BLOCKED":
        print("⛔ EXPERIMENT ABANDONED — content moderation block")
        save_abandonment_log(out_dir, args.style, "Seg1 moderation blocked")
        sys.exit(2)
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
    print(f"Step 4: Segment 2 — 全家桶反转 ({args.style}, Version D)")
    print(f"{'='*60}")

    pse = PSE_ANIME if args.style == "anime" else PSE_REALISTIC

    seg2_images = [last_frame]  # FFA
    seg2_img_refs = ["@image1 as the first frame of this scene (continue from here)"]
    idx = 2
    for name in ["林远", "苏晴", "胖虎"]:
        if name in assets:
            seg2_images.append(assets[name])
            seg2_img_refs.append(f"@image{idx} as character {name}")
            idx += 1
    if "scene-meeting" in assets:
        seg2_images.append(assets["scene-meeting"])
        seg2_img_refs.append(f"@image{idx} as the meeting room background")

    seg2_prompt = (
        ", ".join(seg2_img_refs) + ". "
        f"Extend @video1 by 15 seconds. "
        f"Continue seamlessly from this exact frame. "
        f"Same meeting room, same three characters, same positions. "
        f"{pse}\n\n"
        f"Camera: Same medium-wide shot, same angle as previous segment (no axis crossing).\n\n"
        f"{SEG2_PARTS}\n\n"
        f"{CONSISTENCY_SUFFIX} "
        "Same startup meeting room, continuous scene."
    )

    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    seg2_ok = call_seedance(keys, seg2_prompt, seg2_images, seg2_path, input_video=seg1_path)
    if seg2_ok == "MODERATION_BLOCKED":
        print("⛔ EXPERIMENT ABANDONED — content moderation block on Seg2")
        save_abandonment_log(out_dir, args.style, "Seg2 moderation blocked")
        sys.exit(2)
    if not seg2_ok:
        print("FATAL: Segment 2 failed")
        sys.exit(1)

    # Step 5: Crossfade concat with audio check
    print("\n--- Crossfade concatenation + audio check ---")
    final = os.path.join(out_dir, "final-30s.mp4")
    concat_ok = concat_with_audio_check(seg1_path, seg2_path, final)
    if not concat_ok:
        print("⛔ AUDIO CHECK FAILED — video not deliverable")
        # Still save the log
    
    # Save generation log
    log = {
        "experiment": "EXP-V7-013",
        "hypothesis": "H-132",
        "strategy": "Version D (FFA + PSE + Crossfade)",
        "style": args.style,
        "story": "合伙人 — 3角色创业喜剧",
        "genre": "comedy/startup",
        "character_count": 3,
        "seg1_prompt": seg1_prompt,
        "seg2_prompt": seg2_prompt,
        "seg1_images": [str(p) for p in seg1_images],
        "seg2_images": [str(p) for p in seg2_images],
        "crossfade_duration": 0.4,
        "audio_check_passed": concat_ok,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = os.path.join(out_dir, "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Generation log: {log_path}")
    if concat_ok:
        print(f"✓ Final video: {final}")
    print("Done!")


def save_abandonment_log(out_dir, style, reason):
    log = {
        "experiment": "EXP-V7-013",
        "style": style,
        "status": "ABANDONED",
        "reason": reason,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = os.path.join(out_dir, "abandonment-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"  Abandonment log: {log_path}")


if __name__ == "__main__":
    main()
