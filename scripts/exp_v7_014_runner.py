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
EXP-V7-014 — 深夜写字楼追逐喜剧 (High Action Density)

Dual track with CONCURRENT Seedance generation.
Phase 1: Anime Seg1 + Realistic Seg1 → parallel
Phase 2: Anime Seg2 + Realistic Seg2 → parallel (after respective Seg1 done)

Usage:
    uv run scripts/exp_v7_014_runner.py
    uv run scripts/exp_v7_014_runner.py --skip-assets
    uv run scripts/exp_v7_014_runner.py --style anime   # single track
"""

import json, os, subprocess, sys, time, re
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-014"

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
# Characters & Prompts
# ---------------------------------------------------------------------------
CHAR_XIAOCHEN = "中国男性，24岁，180cm，偏瘦，蓬松黑色中长发，长脸，皮肤偏白，黑眼圈重，穿黑色连帽卫衣（帽子没戴）深蓝牛仔裤白色运动鞋，脖子上挂黑色大耳机，左手腕银色电子手表，背黑色双肩包"
CHAR_LAOWANG = "中国男性，50岁，172cm，壮实微胖，灰白寸头，方脸，肤色偏黑，穿深蓝色保安制服左胸银色徽章，黑色皮鞋，右手持黑色强光手电筒，腰间别对讲机"

LOCATION_SEG1 = "现代写字楼开放办公区，深夜，只有一个工位台灯和显示器亮着，其他全黑。灰色隔板黑色办公椅白色桌面。走廊应急灯微弱绿光"
LOCATION_SEG2 = "同一写字楼消防楼梯间，水泥墙壁金属扶手，应急灯绿光。一楼大厅玻璃门有铁链锁"

SEG1_PSA = (
    "小陈坐在工位椅上身体前倾面对显示器，左手放键盘右手握鼠标，大耳机挂在脖子上，双肩包放在椅子旁地上。"
    "老王站在办公区玻璃门外走廊，右手举手电筒，左手按在门把手上。"
)

SEG2_PSA = (
    "小陈在楼梯间往下跑，右手抓金属扶手，黑色卫衣帽子被风吹起来盖住后脑，双肩包在背上晃动。"
    "老王在上方一层楼梯口，没了手电筒，双手扶栏杆往下看，制服帽子歪了。"
)

SEG1_PARTS = """[Part 1] 小陈坐在黑暗办公区唯一亮着的工位，台灯光映在脸上，手指在键盘飞快敲击。走廊传来缓慢脚步声。小陈手指停住缓缓摘下脖子上耳机放桌上侧头听。

[Part 2] 办公区玻璃门被推开，老王举手电筒走进来。光柱扫过空荡工位扫到小陈。小陈转过椅子面对老王挤出尴尬笑。小陈 says "我是新来的实习生，加班呢。"

[Part 3] 老王左手从腰间掏出折叠花名册翻开手电照着名单手指一行行看。抬头看小陈。老王 says "实习生六点就走光了，你哪个部门的？" 小陈嘴角抽搐目光快速扫向身后的门。

[Part 4] 小陈猛地从椅子弹起往门口冲，脚绊到椅子腿踉跄一下但没摔。老王追上去手电筒从手里飞出咣当砸在地上滚走。老王低头看了眼手电又抬头看门口，小陈已跑出去。"""

SEG2_PARTS = """[Part 1] 小陈冲进楼梯间手抓金属扶手往下跑，脚步声回响。卫衣帽子被风吹起搭在后脑上。回头看到老王身影出现在上方楼梯口。应急灯绿光映在小陈脸上。

[Part 2] 小陈跑下两层差点撞上墙角红色消防栓身体猛地侧闪贴墙滑过。老王在上方扶栏杆喘气。老王 says "别跑了！站住！" 声音在楼梯间回荡。

[Part 3] 小陈冲到一楼大厅双手推玻璃门推不动低头看到铁链锁。整个人僵住缓缓转身背靠玻璃门。老王不紧不慢走下最后一段楼梯制服帽子歪了。

[Part 4] 老王走到小陈面前气喘吁吁露出无奈笑容从制服口袋掏出矿泉水递给小陈。老王 says "每个月都有一个像你这样的，来，喝口水。" 小陈接过水瓶两人对视尴尬又好笑地笑了。"""

CONSISTENCY_SUFFIX = (
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement, natural pacing. 9:16 vertical format. "
    "All characters are Chinese (East Asian). Dark nighttime office/stairwell lighting. "
    "TWO characters: hoodie-guy (young, thin, headphones, backpack) and security-guard (older, stocky, blue uniform)."
)

PSE_ANIME_SEG2 = (
    "Continuing from previous scene in same building stairwell. "
    "[小陈] Chinese male 24yo, thin tall, messy medium black hair, pale with dark circles, "
    "BLACK HOODIE (hood blown up covering back of head), dark blue jeans, white sneakers, "
    "BLACK HEADPHONES on neck, silver digital watch left wrist, BLACK BACKPACK bouncing on back. "
    "Running down stairs gripping metal railing with right hand. "
    "[老王] Chinese male 50yo, stocky chubby, grey-white buzz cut, square dark face, "
    "DARK BLUE SECURITY UNIFORM with silver badge on left chest, black shoes, "
    "NO flashlight (dropped it), walkie-talkie on belt, cap tilted askew. "
    "Standing at upper landing leaning on railing looking down. "
    "Concrete stairwell walls, metal railings, green emergency lights. Anime style."
)

PSE_REALISTIC_SEG2 = (
    "Continuing from previous scene in same building stairwell. "
    "[小陈] Chinese male 24yo, thin tall, messy medium black hair, pale with dark circles, "
    "BLACK HOODIE (hood blown back), dark blue jeans, white sneakers, "
    "BLACK HEADPHONES on neck, silver watch left wrist, BLACK BACKPACK on back. "
    "Running down stairs. "
    "[老王] Chinese male 50yo, stocky, grey-white buzz cut, square dark face, "
    "DARK BLUE SECURITY UNIFORM silver badge, black shoes, NO flashlight, cap tilted. "
    "At upper landing leaning on railing. "
    "Concrete stairwell, metal railings, green emergency lights. Cinematic realistic."
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
        kwargs["http_options"] = types.HttpOptions(base_url=base_url, timeout=120000)
    client = genai.Client(**kwargs)
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview", contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]))
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                img = Image.open(BytesIO(part.inline_data.data))
                if img.width > 600:
                    r = 600 / img.width
                    img = img.resize((600, int(img.height * r)), Image.LANCZOS)
                img.save(output_path, "WEBP", quality=75)
                print(f"  → {output_path} ({os.path.getsize(output_path)//1024}KB)")
                return True
        return False
    except Exception as e:
        print(f"  ✗ Gemini error: {e}")
        return False

def generate_assets_for_style(keys, style, out_dir):
    """Generate character + scene assets for one style."""
    os.makedirs(out_dir, exist_ok=True)
    assets = {}
    sd = "Hyper-detailed anime-style illustration" if style == "anime" else "Cinematic semi-realistic CG portrait"
    ss = "Anime-style illustration" if style == "anime" else "Cinematic photorealistic"

    for name, desc in [("小陈", CHAR_XIAOCHEN), ("老王", CHAR_LAOWANG)]:
        path = os.path.join(out_dir, f"char-{name}.webp")
        prompt = (f"{sd} character portrait. 9:16 vertical. Chinese character: {desc}. "
                  "Looking slightly left (NOT at camera). Upper body. Clean bg, studio lighting.")
        print(f"  Generating: {name} ({style})")
        for attempt in range(3):
            if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
                assets[name] = path
                break
            time.sleep(15 * (attempt + 1))

    # Scene
    for seg_name, loc_desc in [("office", LOCATION_SEG1), ("stairwell", LOCATION_SEG2)]:
        path = os.path.join(out_dir, f"scene-{seg_name}.webp")
        prompt = f"{ss}. {loc_desc}. 9:16 vertical. No people. Dramatic lighting."
        print(f"  Generating: {seg_name} ({style})")
        for attempt in range(3):
            if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
                assets[f"scene-{seg_name}"] = path
                break
            time.sleep(15 * (attempt + 1))
    return assets

# ---------------------------------------------------------------------------
# Seedance helpers
# ---------------------------------------------------------------------------
def upload_to_tmpfiles(local_path):
    import requests
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    page_url = resp.json()["data"]["url"]
    return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")

def call_seedance(keys, prompt, images, output_path, input_video=None):
    """Call seedance. Returns True/False/'MODERATION_BLOCKED'."""
    cmd = ["python3", keys["seedance_script"], "run",
           "--prompt", prompt, "--ratio", "9:16", "--duration", "15", "--out", output_path]
    if input_video:
        v = input_video if input_video.startswith("http") else upload_to_tmpfiles(input_video)
        cmd.extend(["--video", v])
    for img in images:
        u = img if img.startswith("http") else upload_to_tmpfiles(img)
        cmd.extend(["--image", u])
    env = os.environ.copy()
    env["ARK_API_KEY"] = keys["ark_key"]
    print(f"  Seedance: {len(prompt)} chars, {len(images)} imgs, video={'yes' if input_video else 'no'}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    if result.returncode != 0:
        if any(kw in result.stderr for kw in ["内容审核", "审核", "moderation", "blocked"]):
            print(f"  ⛔ MODERATION BLOCKED")
            return "MODERATION_BLOCKED"
        print(f"  ✗ Failed: {result.stderr[:300]}")
        return False
    print(f"  ✓ {output_path}")
    return True

def _run_seg1(style, keys, assets, out_dir):
    """Run Seg1 for one style. Returns (style, success, path)."""
    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    images = []
    img_refs = []
    idx = 1
    if style == "anime":
        for name in ["小陈", "老王"]:
            if name in assets:
                images.append(assets[name])
                img_refs.append(f"@image{idx} as {name}")
                idx += 1
        if "scene-office" in assets:
            images.append(assets["scene-office"])
            img_refs.append(f"@image{idx} as the dark office")
    # realistic: text-only (privacy filter blocks images)
    
    ref_prefix = (", ".join(img_refs) + ". ") if img_refs else ""
    prompt = (
        f"{ref_prefix}"
        f"Physical state: {SEG1_PSA}\n"
        f"Camera: Medium shot from office aisle, 小陈(hoodie, headphones on neck) left at desk, "
        f"glass door right. Eye-level, static. Dark nighttime office.\n\n"
        f"{SEG1_PARTS}\n\n{CONSISTENCY_SUFFIX}"
    )
    result = call_seedance(keys, prompt, images, seg1_path)
    return (style, result, seg1_path)

def _run_seg2(style, keys, assets, out_dir, seg1_path):
    """Run Seg2 for one style using video extension. Returns (style, success, path)."""
    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    pse = PSE_ANIME_SEG2 if style == "anime" else PSE_REALISTIC_SEG2
    
    images = []
    img_refs = []
    if style == "anime":
        # Extract last frame for FFA
        last_frame = os.path.join(out_dir, "seg1-last-frame.jpg")
        subprocess.run(["ffmpeg", "-sseof", "-0.1", "-i", seg1_path,
                       "-frames:v", "1", "-y", last_frame], capture_output=True)
        if os.path.exists(last_frame):
            images.append(last_frame)
            img_refs.append("@image1 as first frame (continue from here)")
            idx = 2
            for name in ["小陈", "老王"]:
                if name in assets:
                    images.append(assets[name])
                    img_refs.append(f"@image{idx} as {name}")
                    idx += 1
    
    ref_prefix = (", ".join(img_refs) + ". ") if img_refs else ""
    prompt = (
        f"{ref_prefix}"
        f"Extend @video1 by 15 seconds. Continue seamlessly. "
        f"{pse}\n\nCamera: High-angle looking down stairwell, slight Dutch angle.\n\n"
        f"{SEG2_PARTS}\n\n{CONSISTENCY_SUFFIX} Same building, continuous chase."
    )
    result = call_seedance(keys, prompt, images, seg2_path, input_video=seg1_path)
    return (style, result, seg2_path)

def concat_with_audio_check(seg1, seg2, output):
    """Crossfade concat with audio check."""
    for label, path in [("Seg1", seg1), ("Seg2", seg2)]:
        ap = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                            "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                           capture_output=True, text=True)
        if not ap.stdout.strip():
            print(f"  ⛔ {label} NO AUDIO — not deliverable")
            return False
    # Simple concat (crossfade can fail with different codecs)
    concat_list = output.replace(".mp4", "-list.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{os.path.abspath(seg1)}'\n")
        f.write(f"file '{os.path.abspath(seg2)}'\n")
    r = subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list,
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                        "-y", output], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ✗ Concat failed: {r.stderr[:200]}")
        return False
    # Verify audio
    ad = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                         "-show_entries", "stream=duration", "-of", "csv=p=0", output],
                        capture_output=True, text=True)
    vd = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v",
                         "-show_entries", "stream=duration", "-of", "csv=p=0", output],
                        capture_output=True, text=True)
    a = float(ad.stdout.strip()) if ad.stdout.strip() else 0
    v = float(vd.stdout.strip()) if vd.stdout.strip() else 0
    if a < v * 0.9:
        print(f"  ⛔ AUDIO CHECK FAIL: a={a:.1f}s v={v:.1f}s")
        return False
    print(f"  ✓ {output} (a={a:.1f}s v={v:.1f}s)")
    return True

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["anime", "realistic", "both"], default="both")
    parser.add_argument("--skip-assets", action="store_true")
    args = parser.parse_args()

    keys = load_keys()
    assert keys["gemini_key"], "GEMINI_API_KEY not found"
    assert keys["ark_key"], "ARK_API_KEY not found"
    assert keys["seedance_script"], "seedance.py not found"

    styles = ["anime", "realistic"] if args.style == "both" else [args.style]
    all_assets = {}

    # Step 1: Generate assets (sequential per style, but could parallelize later)
    if not args.skip_assets:
        print(f"\n{'='*60}\nEXP-V7-014 — Step 1: Assets\n{'='*60}")
        for style in styles:
            ad = str(EXP_DIR / "output" / style / "assets")
            all_assets[style] = generate_assets_for_style(keys, style, ad)
            print(f"  {style}: {len(all_assets[style])} assets")
    else:
        for style in styles:
            ad = str(EXP_DIR / "output" / style / "assets")
            all_assets[style] = {}
            if os.path.exists(ad):
                for f in os.listdir(ad):
                    if f.endswith(".webp"):
                        k = f.replace(".webp", "").replace("char-", "")
                        all_assets[style][k] = os.path.join(ad, f)

    # Step 2: CONCURRENT Seg1 generation
    print(f"\n{'='*60}\nStep 2: Segment 1 — CONCURRENT ({' + '.join(styles)})\n{'='*60}")
    seg1_results = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        for style in styles:
            out_dir = str(EXP_DIR / "output" / style)
            os.makedirs(out_dir, exist_ok=True)
            f = pool.submit(_run_seg1, style, keys, all_assets.get(style, {}), out_dir)
            futures[f] = style
        for future in as_completed(futures):
            style, result, path = future.result()
            seg1_results[style] = (result, path)
            status = "✓" if result is True else ("⛔MOD" if result == "MODERATION_BLOCKED" else "✗")
            print(f"  Seg1 {style}: {status}")

    # Check for moderation blocks / failures
    for style in list(styles):
        result, _ = seg1_results.get(style, (False, None))
        if result == "MODERATION_BLOCKED":
            print(f"⛔ {style} ABANDONED — moderation block on Seg1")
            styles.remove(style)
        elif not result:
            print(f"✗ {style} Seg1 FAILED")
            styles.remove(style)

    if not styles:
        print("All tracks failed/blocked. Aborting.")
        sys.exit(2)

    # Step 3: CONCURRENT Seg2 generation (video extension from respective Seg1)
    print(f"\n{'='*60}\nStep 3: Segment 2 — CONCURRENT ({' + '.join(styles)})\n{'='*60}")
    seg2_results = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        for style in styles:
            out_dir = str(EXP_DIR / "output" / style)
            _, seg1_path = seg1_results[style]
            f = pool.submit(_run_seg2, style, keys, all_assets.get(style, {}), out_dir, seg1_path)
            futures[f] = style
        for future in as_completed(futures):
            style, result, path = future.result()
            seg2_results[style] = (result, path)
            status = "✓" if result is True else ("⛔MOD" if result == "MODERATION_BLOCKED" else "✗")
            print(f"  Seg2 {style}: {status}")

    # Step 4: Concat + audio check
    print(f"\n{'='*60}\nStep 4: Concat + Audio Check\n{'='*60}")
    final_videos = {}
    for style in styles:
        r2, _ = seg2_results.get(style, (False, None))
        if r2 == "MODERATION_BLOCKED":
            print(f"  ⛔ {style} Seg2 moderation blocked — abandoned")
            continue
        if not r2:
            print(f"  ✗ {style} Seg2 failed — skipping concat")
            continue
        out_dir = str(EXP_DIR / "output" / style)
        seg1_path = seg1_results[style][1]
        seg2_path = seg2_results[style][1]
        final_path = os.path.join(out_dir, "final-30s.mp4")
        ok = concat_with_audio_check(seg1_path, seg2_path, final_path)
        if ok:
            final_videos[style] = final_path

    # Step 5: Save generation log
    log = {
        "experiment": "EXP-V7-014",
        "hypothesis": "H-133",
        "strategy": "High action density, concurrent dual-track",
        "concurrent": True,
        "styles_attempted": ["anime", "realistic"] if args.style == "both" else [args.style],
        "styles_completed": list(final_videos.keys()),
        "final_videos": final_videos,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = str(EXP_DIR / "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}\nSummary\n{'='*60}")
    for style, path in final_videos.items():
        print(f"  ✓ {style}: {path}")
    if not final_videos:
        print("  ⛔ No videos completed")
    print(f"Log: {log_path}")
    print("Done!")


if __name__ == "__main__":
    main()
