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
EXP-V7-023 — 重生×创业 双Segment (Phase 2 首发)

TRUE CONCURRENT dual-track: anime + realistic Seg1 submitted simultaneously.
Seg2 depends on Seg1, so Seg1→Seg2 serial per track, but cross-track concurrent.

Hypothesis H-355: Playbook v2 全约束 + T0 题材 → 跨Segment一致性无重大瑕疵 + 朱江≥9.0

Usage:
    uv run scripts/exp_v7_023_runner.py
    uv run scripts/exp_v7_023_runner.py --skip-assets
    uv run scripts/exp_v7_023_runner.py --style anime
    uv run scripts/exp_v7_023_runner.py --style realistic
"""

import json, os, subprocess, sys, time, re, argparse
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-023"
REPO_DIR = BASE  # git repo root

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
# Story Content (from Controller spec CYCLE-1310)
# ---------------------------------------------------------------------------
CHAR_MAIN = "中国男性，22岁，175cm，偏瘦短发黑色，穿旧灰色卫衣和深蓝运动裤白色运动鞋，面容年轻清瘦"

LOCATION_SEG1 = "2005年中国北方大学男生宿舍白天。旧木质上下铺床，桌上放着2005年风格的旧笔记本电脑（厚重灰色），墙上贴满海报。冬日午后阳光从旧窗帘缝隙透入。整体暖色调。"
LOCATION_SEG2 = "同一栋宿舍楼走廊白天。走廊窗户冬日阳光照入暖色调。走廊空旷干净，左侧有宿舍门。远处可见几棵光秃秃的树。"

SEG1_PSA = (
    "主角坐在上铺床沿，双脚悬空。室友在对面下铺蜷缩侧睡只露后背和被子。"
    "冬日阳光从窗帘缝隙透入。"
)
SEG2_PSA = (
    "主角站在走廊靠窗位置，右肩靠窗框，左手持旧手机。"
    "走廊空无一人。冬日阳光从走廊尽头照来。"
)

SEG1_PARTS = """[Part 1] 宿舍内暖黄光线中主角猛然从上铺坐起左手撑床沿右手下意识摸自己脸颊。眼睛睁大嘴微张表情从困惑到震惊。主角 says "这…这是宿舍？"

[Part 2] 特写主角双手手指细长年轻皮肤光滑。主角低头仔细端详双手翻转右手食指按压左手腕感受脉搏。表情从震惊转为困惑。无台词只有走廊远处隐约脚步声。

[Part 3] 中景从窗户方向拍向主角背光剪影效果阳光勾勒轮廓。主角深呼吸胸腔起伏明显然后嘴角缓缓上扬眼神从迷茫变为锐利。主角 says "2005年…互联网的黄金十年还没开始…"

[Part 4] 中全景从侧面拍主角翻身准备下床脚先落地。远处室友翻身但没醒只露背影。主角双手轻撑上铺边缘沉稳翻身下床落地动作轻盈。直起身拿起床头桌上旧手机看一眼面带微笑目光坚定。无台词。"""

SEG2_PARTS = """[Part 1] 走廊落地窗冬日阳光照入。主角右肩靠着窗框左手举起旧手机看屏幕眉头微挑嘴角带笑。主角 says "2005年1月…域名注册还来得及。"

[Part 2] 近景胸部以上微侧面窗外光线打在脸上一半。主角收起手机放进卫衣口袋右手食指在窗框上无意识敲击在思考。眼神望向走廊远处。主角 says "第一步，先把域名注册了。2005年，点com域名还便宜…"

[Part 3] 中景从走廊另一端拍窗外能看到校园操场和光秃秃的树。主角推窗冷空气涌入可见微微呼气白雾。闭眼深吸一口气然后睁眼眼神清澈有力。无台词只有远处操场跑步声。

[Part 4] 全景从走廊拐角方向拍主角在画面中间偏左走廊纵深感强。主角转身步伐轻快但坚定向走廊尽头走去卫衣下摆随步伐摆动不回头。无台词脚步声渐远画面定格在空荡走廊和窗外阳光。"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def upload_to_tmpfiles(local_path: str) -> str:
    import requests
    print(f"  Uploading {local_path} to tmpfiles.org...")
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    page_url = resp.json()["data"]["url"]
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
                    img = Image.open(BytesIO(part.inline_data.data))
                    if img.width > 600:
                        ratio = 600 / img.width
                        img = img.resize((600, int(img.height * ratio)), Image.LANCZOS)
                    img.save(output_path, "WEBP", quality=75)
                    print(f"  → Saved: {output_path} ({os.path.getsize(output_path) // 1024}KB)")
                    return True
            print(f"  ✗ No image (attempt {attempt+1})")
        except Exception as e:
            print(f"  ✗ Gemini error (attempt {attempt+1}): {e}")
            if attempt < 2: time.sleep(5)
    return False


def call_seedance(seedance_script, ark_key, prompt, asset_paths, output_path, input_video=None, duration=15):
    cmd = [
        "python3", seedance_script, "run",
        "--prompt", prompt, "--ratio", "9:16", "--duration", str(duration), "--out", output_path,
    ]
    if input_video:
        if os.path.isfile(input_video) and not input_video.startswith("http"):
            input_video = upload_to_tmpfiles(input_video)
        cmd.extend(["--video", input_video])
    for path in asset_paths:
        if os.path.isfile(path) and not path.startswith("http"):
            path = upload_to_tmpfiles(path)
        cmd.extend(["--image", path])
    env = os.environ.copy()
    env["ARK_API_KEY"] = ark_key
    print(f"  [{os.path.basename(output_path)}] Calling Seedance... (timeout 1800s)")
    print(f"  Prompt: {prompt[:150]}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    except subprocess.TimeoutExpired:
        print(f"  ✗ TIMEOUT")
        return False
    if result.returncode == 0:
        print(f"  ✓ Generated: {output_path}")
        return True
    stderr = result.stderr[:1000] if result.stderr else ""
    print(f"  ✗ Failed: {stderr[:300]}")
    if any(kw in stderr for kw in ["ContentFilterBlock", "审核", "PrivacyInformation", "moderation"]):
        print("  ⛔ MODERATION BLOCK — abandoning per standing order")
        return "BLOCKED"
    return False


def concat_segments(seg1_path, seg2_path, output_path):
    list_file = output_path.replace(".mp4", "-list.txt")
    with open(list_file, "w") as f:
        f.write(f"file '{os.path.abspath(seg1_path)}'\n")
        f.write(f"file '{os.path.abspath(seg2_path)}'\n")
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        "-y", output_path
    ], capture_output=True)
    return os.path.exists(output_path)


def check_audio(video_path):
    try:
        a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=duration", "-of", "csv=p=0", video_path],
            capture_output=True, text=True)
        v = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v",
             "-show_entries", "stream=duration", "-of", "csv=p=0", video_path],
            capture_output=True, text=True)
        return float(a.stdout.strip() or 0), float(v.stdout.strip() or 0)
    except: return 0, 0


def check_segment_audio(seg1_path, seg2_path):
    issues = []
    for label, path in [("Seg1", seg1_path), ("Seg2", seg2_path)]:
        a, v = check_audio(path)
        if a < 1.0:
            issues.append(f"⛔ {label} NO AUDIO (a={a:.1f}s v={v:.1f}s)")
        elif a < v * 0.8:
            issues.append(f"⚠️ {label} audio short (a={a:.1f}s v={v:.1f}s)")
        else:
            print(f"  ✓ {label} audio OK: a={a:.1f}s v={v:.1f}s")
    return issues


def git_push(message):
    """Commit and push to GitHub."""
    try:
        subprocess.run(["git", "add", "-A"], cwd=str(REPO_DIR), capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=str(REPO_DIR), capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=str(REPO_DIR), capture_output=True)
        r = subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_DIR), capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  ✓ Git pushed: {message}")
        else:
            print(f"  ⚠️ Git push issue: {r.stderr[:200]}")
    except Exception as e:
        print(f"  ⚠️ Git error: {e}")


# ---------------------------------------------------------------------------
# Build prompts
# ---------------------------------------------------------------------------

def build_seg1_prompt_anime(asset_paths):
    refs = []
    images = []
    idx = 1
    if "主角" in asset_paths:
        refs.append(f"@image{idx} is character 主角: {CHAR_MAIN}")
        images.append(asset_paths["主角"])
        idx += 1
    if "scene-dorm" in asset_paths:
        refs.append(f"@image{idx} is the 2005 university dormitory scene")
        images.append(asset_paths["scene-dorm"])
        idx += 1

    prompt = (
        " ".join(refs) + "\n\n"
        "Anime-style animated scene, 2005 Chinese university dormitory, warm winter afternoon light.\n"
        f"Physical state: {SEG1_PSA}\n"
        "Camera: 中景偏俯从宿舍门口方向拍主角在上铺\n\n"
        + SEG1_PARTS +
        "\n\nNo subtitles, no slow motion, no characters looking at camera. "
        "Normal speed movement and natural dialogue pacing. 9:16 vertical format. "
        "Warm winter afternoon light. Character is Chinese East Asian male 22 years old. "
        "All dialogue must finish before the 14 second mark, leaving ~1s silence buffer at end."
    )
    return prompt, images


def build_seg1_prompt_realistic():
    prompt = (
        "Live-action cinematic scene. 2005 Chinese university dormitory, winter afternoon. "
        "Warm natural light filtering through old curtains.\n"
        f"One character: Chinese male, 22 years old, thin build, short black hair, wearing an old grey hoodie and dark blue sweatpants and white sneakers. Young clean-shaven face.\n"
        f"Physical state: {SEG1_PSA}\n"
        "Camera: Medium shot slightly overhead, from dormitory doorway direction.\n\n"
        + SEG1_PARTS +
        "\n\nFilm-quality realistic cinematography. Warm winter daylight. "
        "No subtitles, no slow motion, no characters looking at camera. "
        "Normal speed movement and natural dialogue pacing. 9:16 vertical. "
        "Character is Chinese East Asian male. Period-accurate 2005 setting (old CRT monitors, flip phones). "
        "All dialogue must finish before the 14 second mark, leaving ~1s silence buffer at end."
    )
    return prompt


def build_seg2_prompt(style):
    """Build Seg2 video-extension prompt (same for both styles)."""
    style_note = "Anime-style animation" if style == "anime" else "Live-action cinematic"
    prompt = (
        f"Extend @video1 by 15 seconds. {style_note}.\n"
        f"Scene transitions from university dormitory room to dormitory hallway of the same building. "
        f"Same Chinese male (22, short black hair, old grey hoodie, dark blue sweatpants, white sneakers) "
        f"now stands in the hallway by a window.\n"
        f"Physical state: {SEG2_PSA}\n"
        "Camera: 中景从走廊一端向主角拍主角在画面右1/3处靠窗\n\n"
        + SEG2_PARTS +
        "\n\nMaintain exact same character appearance from previous segment. "
        "Same warm winter daylight. Dormitory hallway of the same building. "
        "No subtitles, no slow motion, no characters looking at camera. "
        "Normal speed movement. 9:16 vertical. Character is Chinese East Asian male. "
        "Period-accurate 2005 setting (old flip phone, no smartphones). "
        "All dialogue must finish before the 14 second mark, leaving ~1s silence buffer at end."
    )
    return prompt


# ---------------------------------------------------------------------------
# Main pipeline with TRUE CONCURRENCY
# ---------------------------------------------------------------------------

def generate_assets(keys):
    """Generate anime assets (realistic track uses text-only, no assets needed)."""
    assets_dir = str(EXP_DIR / "output" / "shared-assets" / "anime")
    os.makedirs(assets_dir, exist_ok=True)
    asset_paths = {}

    # Character portrait
    path = os.path.join(assets_dir, "char-主角.webp")
    prompt = (
        "Semi-realistic anime illustration character portrait for production. "
        f"9:16 vertical format. The character is: {CHAR_MAIN}. "
        "Soft studio lighting, clean gradient background. High detail, vibrant warm colors. "
        "Character looking slightly to the left (not at camera). Upper body visible. "
        "2005 era Chinese university student style."
    )
    print("  Generating: 主角 portrait")
    if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
        asset_paths["主角"] = path
    time.sleep(2)

    # Scene: Dormitory
    path = os.path.join(assets_dir, "scene-dorm.webp")
    prompt = (
        f"Anime-style wide establishing shot. 9:16 vertical. {LOCATION_SEG1} "
        "No people. Semi-realistic anime, warm winter afternoon light, nostalgic 2005 atmosphere."
    )
    print("  Generating: scene-dorm")
    if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
        asset_paths["scene-dorm"] = path

    return asset_paths


def run_full_track(keys, style, asset_paths, skip_seg1=False):
    """Run a complete track (Seg1→Seg2→concat). Called from thread for concurrency."""
    out_dir = str(EXP_DIR / "output" / style)
    os.makedirs(out_dir, exist_ok=True)

    track_log = {"style": style, "segments": {}, "issues": [], "timing": {}}
    t_start = time.time()

    # --- Seg1 ---
    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    if skip_seg1 and os.path.exists(seg1_path):
        print(f"\n  [{style}] Skipping Seg1 (exists)")
    else:
        print(f"\n  [{style}] === Seg1: 宿舍觉醒 ===")
        t_seg1 = time.time()
        if style == "anime":
            prompt, images = build_seg1_prompt_anime(asset_paths)
        else:
            prompt = build_seg1_prompt_realistic()
            images = []

        track_log["segments"]["seg1"] = {"prompt": prompt, "images": [str(p) for p in images]}
        result = call_seedance(keys["seedance_script"], keys["ark_key"], prompt, images, seg1_path)
        track_log["timing"]["seg1_seconds"] = time.time() - t_seg1

        if result == "BLOCKED":
            track_log["issues"].append("Seg1 BLOCKED")
            track_log["result"] = "ABANDONED_MODERATION"
            return track_log
        if not result:
            track_log["issues"].append("Seg1 failed")
            track_log["result"] = "FAILED_SEG1"
            return track_log

    # --- Seg2 (video extension, depends on Seg1) ---
    print(f"\n  [{style}] === Seg2: 走廊布局 (video extension) ===")
    t_seg2 = time.time()
    seg2_prompt = build_seg2_prompt(style)
    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    track_log["segments"]["seg2"] = {"prompt": seg2_prompt, "mode": "video-extension"}

    result = call_seedance(keys["seedance_script"], keys["ark_key"], seg2_prompt, [], seg2_path, input_video=seg1_path)
    track_log["timing"]["seg2_seconds"] = time.time() - t_seg2

    if result == "BLOCKED":
        track_log["issues"].append("Seg2 BLOCKED")
        track_log["result"] = "ABANDONED_MODERATION"
        return track_log
    if not result:
        track_log["issues"].append("Seg2 failed")
        track_log["result"] = "FAILED_SEG2"
        return track_log

    # --- Audio check per segment ---
    audio_issues = check_segment_audio(seg1_path, seg2_path)
    track_log["issues"].extend(audio_issues)

    # --- Concat ---
    final_path = os.path.join(out_dir, "final-30s.mp4")
    if concat_segments(seg1_path, seg2_path, final_path):
        a_dur, v_dur = check_audio(final_path)
        if a_dur < v_dur * 0.9:
            track_log["issues"].append(f"⛔ Final audio: a={a_dur:.1f}s v={v_dur:.1f}s")
        print(f"  ✓ [{style}] Final: {final_path} (a={a_dur:.1f}s v={v_dur:.1f}s)")
        track_log["result"] = "SUCCESS" if not audio_issues else "SUCCESS_WITH_AUDIO_ISSUES"
        track_log["final_video"] = final_path
        track_log["final_audio"] = {"audio_s": a_dur, "video_s": v_dur}
    else:
        track_log["result"] = "FAILED_CONCAT"

    track_log["timing"]["total_seconds"] = time.time() - t_start
    return track_log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-seg1", action="store_true")
    parser.add_argument("--style", choices=["anime", "realistic", "both"], default="both")
    args = parser.parse_args()

    keys = load_keys()
    if not keys["gemini_key"]: print("ERROR: No GEMINI_API_KEY"); sys.exit(1)
    if not keys["ark_key"]: print("ERROR: No ARK_API_KEY"); sys.exit(1)
    if not keys["seedance_script"]: print("ERROR: seedance.py not found"); sys.exit(1)

    os.makedirs(str(EXP_DIR / "output"), exist_ok=True)

    gen_log = {
        "experiment": "EXP-V7-023",
        "hypothesis": "H-355: Playbook v2全约束 + T0题材重生×创业 → 一致性+评分≥9.0",
        "story": "《重生2005：域名注册》",
        "concurrent_dual_track": args.style == "both",
        "tracks": {},
        "timestamp_start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    # --- Step 1: Generate anime assets (realistic uses text-only) ---
    asset_paths = {}
    if not args.skip_assets and args.style in ("anime", "both"):
        print("\n--- Step 1: Generate Anime Assets ---")
        asset_paths = generate_assets(keys)
        git_push("[operator] EXP-V7-023: anime assets generated")

    # --- Step 2: TRUE CONCURRENT dual-track generation ---
    if args.style == "both":
        print("\n" + "#" * 60)
        print("TRUE CONCURRENT DUAL-TRACK: anime + realistic Seg1 simultaneously")
        print("#" * 60)

        # Run both tracks in parallel threads
        # Each track runs Seg1→Seg2 internally (Seg2 depends on Seg1)
        # But anime.Seg1 and realistic.Seg1 run at the same time!
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_anime = pool.submit(run_full_track, keys, "anime", asset_paths, args.skip_seg1)
            future_realistic = pool.submit(run_full_track, keys, "realistic", {}, args.skip_seg1)

            for future, style in [(future_anime, "anime"), (future_realistic, "realistic")]:
                try:
                    track_log = future.result(timeout=3600)
                    gen_log["tracks"][style] = track_log
                except Exception as e:
                    gen_log["tracks"][style] = {"result": f"EXCEPTION: {e}", "issues": [str(e)]}

    elif args.style == "anime":
        gen_log["tracks"]["anime"] = run_full_track(keys, "anime", asset_paths, args.skip_seg1)
    else:
        gen_log["tracks"]["realistic"] = run_full_track(keys, "realistic", {}, args.skip_seg1)

    # --- Overall result ---
    results = [t.get("result", "UNKNOWN") for t in gen_log["tracks"].values()]
    if all(r.startswith("SUCCESS") for r in results):
        gen_log["result"] = "SUCCESS"
    elif any("ABANDONED" in str(r) for r in results):
        gen_log["result"] = "PARTIAL_ABANDONED"
    elif any("FAILED" in str(r) for r in results):
        gen_log["result"] = "PARTIAL_FAILED"
    else:
        gen_log["result"] = "UNKNOWN"

    gen_log["timestamp_end"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # Save log
    log_path = str(EXP_DIR / "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(gen_log, f, indent=2, ensure_ascii=False)

    # Git push
    git_push(f"[operator] EXP-V7-023: {gen_log['result']}")

    print(f"\n{'=' * 60}")
    print(f"EXP-V7-023 COMPLETE: {gen_log['result']}")
    for style, track in gen_log["tracks"].items():
        r = track.get("result", "?")
        t = track.get("timing", {}).get("total_seconds", 0)
        print(f"  {style}: {r} ({t:.0f}s)")
    print(f"Log: {log_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
