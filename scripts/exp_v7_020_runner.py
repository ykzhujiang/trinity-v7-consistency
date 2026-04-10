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
EXP-V7-020 — 音频缓冲 A/B 测试《最后一个 Bug》

A组: Seg1 Part4 纯动作无对白 (~1s buffer) → 台词≤13s
B组: Seg1 Part4 有完整台词 → 台词~14.5s
双轨: anime + realistic = 4 videos

Usage:
    uv run scripts/exp_v7_020_runner.py
    uv run scripts/exp_v7_020_runner.py --skip-assets
    uv run scripts/exp_v7_020_runner.py --group a    # only A group
    uv run scripts/exp_v7_020_runner.py --style anime # only anime
"""

import json, os, subprocess, sys, time, re
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-020"

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
CHAR_LINYUAN = "中国男性，28岁，175cm，中等身材，短黑发整齐侧分，国字脸，皮肤健康小麦色，穿白色衬衫袖子卷到手肘黑色西裤棕色皮鞋，左手腕黑色商务手表，胸口插一支钢笔"
CHAR_SUQING = "中国女性，26岁，163cm，偏瘦，黑色马尾扎高，鹅蛋脸，皮肤白皙戴黑框圆眼镜，穿灰色oversize卫衣牛仔裤白色帆布鞋，右手腕一串彩色编织手绳，左耳戴一个小银耳钉"

LOCATION_SEG1 = "现代创业公司办公室，白天，开放式办公区有4-5张白色桌子，墙上贴着各色便利贴和白板写满代码流程图。两台大显示器，桌上散着咖啡杯和外卖盒。明亮日光从落地窗射入"
LOCATION_SEG2 = "同一栋楼的室外阳台，白天，能看到城市天际线和楼下马路。阳台有不锈钢栏杆，角落有一盆绿植，地上一个烟灰缸。阳光充足微风"

SEG1_PSA = (
    "林远坐在桌前椅子上身体后仰，左手拿咖啡杯右手点鼠标，面对两台显示器，表情轻松。"
    "苏晴站在林远身后偏右，双手抱笔记本电脑贴胸前，低头看屏幕皱眉，眼镜滑到鼻尖。"
)

SEG2_PSA = (
    "林远站在阳台栏杆旁，右手举手机贴右耳，左手肘撑栏杆，衬衫被风吹起下摆。面朝城市天际线。"
    "苏晴不在画面中（在室内修 bug）。"
)

# A组 Seg1: Part4 纯动作无对白 (buffer ~1s)
SEG1_PARTS_A = """[Part 1] 办公室里两台显示器亮着。林远坐在椅子上后仰翘着二郎腿左手端咖啡杯喝了一口放下。苏晴从身后走过来抱着笔记本低头看屏幕眼镜滑到鼻尖。苏晴 says "上线前最后一轮测试，有个支付接口报500了。"

[Part 2] 林远椅子转过来面对苏晴双手交叉放脑后。林远 says "500？重启一下不就好了？经典程序员解法。" 苏晴抬头瞪他推了一下眼镜。苏晴 says "是数据库连接池满了，重启没用。"

[Part 3] 林远从椅子站起来走到白板前拿起马克笔画了个圈。林远 says "那就加个连接池上限呗，三行代码的事儿。" 苏晴 says "你上次说三行代码改出了两个新bug。" 林远转头看苏晴尴尬地笑。

[Part 4] 林远放下马克笔双手插裤兜走到窗边看了眼外面的天际线。深吸一口气转身拍了拍苏晴肩膀竖起大拇指。苏晴摇头但嘴角忍不住微微上扬低头继续敲代码。"""

# B组 Seg1: Part4 有完整台词 (no buffer)
SEG1_PARTS_B = """[Part 1] 办公室里两台显示器亮着。林远坐在椅子上后仰翘着二郎腿左手端咖啡杯喝了一口放下。苏晴从身后走过来抱着笔记本低头看屏幕眼镜滑到鼻尖。苏晴 says "上线前最后一轮测试，有个支付接口报500了。"

[Part 2] 林远椅子转过来面对苏晴双手交叉放脑后。林远 says "500？重启一下不就好了？经典程序员解法。" 苏晴抬头瞪他推了一下眼镜。苏晴 says "是数据库连接池满了，重启没用。"

[Part 3] 林远从椅子站起来走到白板前拿起马克笔画了个圈。林远 says "那就加个连接池上限呗，三行代码的事儿。" 苏晴 says "你上次说三行代码改出了两个新bug。" 林远转头看苏晴尴尬地笑。

[Part 4] 林远放下马克笔双手插裤兜走到窗边。林远 says "放心吧，这次我亲自盯着，不会蓝屏的。" 苏晴摇头低头继续敲代码。苏晴 says "你上次也是这么说的，结果服务器炸了三小时。" """

# Seg2 相同（两组）
SEG2_PARTS = """[Part 1] 林远推开阳台门走出来，阳光照在脸上微微眯眼。右手从裤兜掏出手机拨号举到右耳。左手肘撑在不锈钢栏杆上。风吹起衬衫下摆。

[Part 2] 林远看着远处城市天际线笑着说。林远 says "王总，产品明天上线，就差最后一个小bug，能不能宽限一天？" 停顿听电话点了点头。林远 says "放心，明天一定能上。"

[Part 3] 林远挂掉电话把手机收回裤兜。双手撑栏杆低头看楼下马路上的车流长呼一口气。身后阳台门被猛地推开。

[Part 4] 苏晴冲出阳台门双手举着笔记本电脑，屏幕朝林远。苏晴 says "修好了！连接池的问题，是配置文件写错了一个零。" 林远转身双手抓住苏晴肩膀笑。林远 says "一个零！？我就说嘛，三行代码的事！" 两人在阳台上笑。"""

CONSISTENCY_SUFFIX = (
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement, natural pacing. 9:16 vertical format. "
    "All characters are Chinese (East Asian). Bright daytime office/balcony. "
    "TWO characters: 林远(shirt, pen in pocket, business watch) and 苏晴(grey hoodie, glasses, hair in ponytail)."
)

PSE_ANIME_SEG2 = (
    "Continuing from previous scene, same building outdoor balcony. "
    "[林远] Chinese male 28yo, medium build, short neat black hair side-parted, tan skin, "
    "WHITE SHIRT sleeves rolled to elbows, BLACK SLACKS, brown shoes, "
    "black business watch left wrist, pen in chest pocket. "
    "Standing at steel balcony railing, right hand holding phone to right ear, left elbow on railing. "
    "Wind blowing shirt hem. "
    "[苏晴] NOT in initial frame (arrives in Part 4). "
    "City skyline in background, sunny daylight, potted plant in corner. Anime style."
)

PSE_REALISTIC_SEG2 = (
    "Continuing from previous scene, same building outdoor balcony. "
    "[林远] Chinese male 28yo, medium build, short neat black hair side-parted, tan skin, "
    "WHITE SHIRT sleeves rolled, BLACK SLACKS, brown shoes, "
    "black watch left wrist, pen in pocket. "
    "Standing at railing with phone. "
    "[苏晴] NOT in initial frame. "
    "City skyline background, bright daylight. Cinematic realistic."
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
    os.makedirs(out_dir, exist_ok=True)
    assets = {}
    sd = "Hyper-detailed anime-style illustration" if style == "anime" else "Cinematic semi-realistic CG portrait"
    ss = "Anime-style illustration" if style == "anime" else "Cinematic photorealistic"

    for name, desc in [("林远", CHAR_LINYUAN), ("苏晴", CHAR_SUQING)]:
        path = os.path.join(out_dir, f"char-{name}.webp")
        prompt = (f"{sd} character portrait. 9:16 vertical. Chinese character: {desc}. "
                  "Looking slightly left (NOT at camera). Upper body. Clean bg, studio lighting.")
        print(f"  Generating: {name} ({style})")
        for attempt in range(3):
            if generate_asset(keys["gemini_key"], prompt, path, keys.get("gemini_base_url")):
                assets[name] = path
                break
            time.sleep(15 * (attempt + 1))

    for seg_name, loc_desc in [("office", LOCATION_SEG1), ("balcony", LOCATION_SEG2)]:
        path = os.path.join(out_dir, f"scene-{seg_name}.webp")
        prompt = f"{ss}. {loc_desc}. 9:16 vertical. No people. Bright daylight."
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
        if any(kw in result.stderr for kw in ["内容审核", "审核", "moderation", "blocked", "Sensitive"]):
            print(f"  ⛔ MODERATION BLOCKED")
            return "MODERATION_BLOCKED"
        print(f"  ✗ Failed: {result.stderr[:300]}")
        return False
    print(f"  ✓ {output_path}")
    return True

# ---------------------------------------------------------------------------
# Video generation per group/style
# ---------------------------------------------------------------------------
def run_seg1(group, style, keys, assets, out_dir):
    """Generate Seg1. group='a' or 'b'."""
    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    parts = SEG1_PARTS_A if group == "a" else SEG1_PARTS_B
    
    images = []
    img_refs = []
    idx = 1
    if style == "anime":
        for name in ["林远", "苏晴"]:
            if name in assets:
                images.append(assets[name])
                img_refs.append(f"@image{idx} as {name}")
                idx += 1
        if "scene-office" in assets:
            images.append(assets["scene-office"])
            img_refs.append(f"@image{idx} as the office")
    
    ref_prefix = (", ".join(img_refs) + ". ") if img_refs else ""
    prompt = (
        f"{ref_prefix}"
        f"Physical state: {SEG1_PSA}\n"
        f"Camera: Medium shot from office aisle, 林远(white shirt, pen pocket) left at desk, "
        f"苏晴(grey hoodie, glasses) right standing behind. Eye-level, static. Bright daytime office.\n\n"
        f"{parts}\n\n{CONSISTENCY_SUFFIX}"
    )
    result = call_seedance(keys, prompt, images, seg1_path)
    return result, seg1_path

def run_seg2(group, style, keys, assets, out_dir, seg1_path):
    """Generate Seg2 via video extension."""
    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    pse = PSE_ANIME_SEG2 if style == "anime" else PSE_REALISTIC_SEG2
    
    images = []
    img_refs = []
    if style == "anime":
        last_frame = os.path.join(out_dir, "seg1-last-frame.jpg")
        subprocess.run(["ffmpeg", "-sseof", "-0.1", "-i", seg1_path,
                       "-frames:v", "1", "-y", last_frame], capture_output=True)
        if os.path.exists(last_frame):
            images.append(last_frame)
            img_refs.append("@image1 as first frame (continue from here)")
            idx = 2
            for name in ["林远", "苏晴"]:
                if name in assets:
                    images.append(assets[name])
                    img_refs.append(f"@image{idx} as {name}")
                    idx += 1
    
    ref_prefix = (", ".join(img_refs) + ". ") if img_refs else ""
    prompt = (
        f"{ref_prefix}"
        f"Extend @video1 by 15 seconds. Continue seamlessly. "
        f"{pse}\n\nCamera: Medium shot, eye-level, 林远 center frame at balcony railing.\n\n"
        f"{SEG2_PARTS}\n\n{CONSISTENCY_SUFFIX} Same building, continuous story."
    )
    result = call_seedance(keys, prompt, images, seg2_path, input_video=seg1_path)
    return result, seg2_path

def concat_with_audio_check(seg1, seg2, output):
    for label, path in [("Seg1", seg1), ("Seg2", seg2)]:
        ap = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                            "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                           capture_output=True, text=True)
        if not ap.stdout.strip():
            print(f"  ⛔ {label} NO AUDIO — not deliverable")
            return False
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
    parser.add_argument("--group", choices=["a", "b", "both"], default="both")
    parser.add_argument("--skip-assets", action="store_true")
    args = parser.parse_args()

    keys = load_keys()
    assert keys["gemini_key"], "GEMINI_API_KEY not found"
    assert keys["ark_key"], "ARK_API_KEY not found"
    assert keys["seedance_script"], "seedance.py not found"

    styles = ["anime", "realistic"] if args.style == "both" else [args.style]
    groups = ["a", "b"] if args.group == "both" else [args.group]

    # Step 1: Generate assets (shared across A/B, separate per style)
    all_assets = {}
    if not args.skip_assets:
        print(f"\n{'='*60}\nEXP-V7-020 — Step 1: Assets\n{'='*60}")
        for style in styles:
            ad = str(EXP_DIR / "output" / "shared-assets" / style)
            all_assets[style] = generate_assets_for_style(keys, style, ad)
            print(f"  {style}: {len(all_assets[style])} assets")
    else:
        for style in styles:
            ad = str(EXP_DIR / "output" / "shared-assets" / style)
            all_assets[style] = {}
            if os.path.exists(ad):
                for f in os.listdir(ad):
                    if f.endswith(".webp"):
                        k = f.replace(".webp", "").replace("char-", "").replace("scene-", "scene-" if "scene-" in f else "")
                        # re-parse properly
                        if f.startswith("char-"):
                            k = f[5:].replace(".webp", "")
                        elif f.startswith("scene-"):
                            k = f.replace(".webp", "")
                        all_assets[style][k] = os.path.join(ad, f)

    # Step 2: For each group, generate Seg1 concurrently across styles
    final_videos = {}
    generation_log = []

    for group in groups:
        group_label = "A-buffer" if group == "a" else "B-nobuffer"
        print(f"\n{'='*60}\n{group_label}: Seg1 — CONCURRENT ({' + '.join(styles)})\n{'='*60}")
        
        seg1_results = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {}
            for style in styles:
                out_dir = str(EXP_DIR / "output" / f"{'a-buffer' if group == 'a' else 'b-nobuffer'}" / style)
                os.makedirs(out_dir, exist_ok=True)
                f = pool.submit(run_seg1, group, style, keys, all_assets.get(style, {}), out_dir)
                futures[f] = style
            for future in as_completed(futures):
                style = futures[future]
                result, path = future.result()
                seg1_results[style] = (result, path)
                status = "✓" if result is True else ("⛔MOD" if result == "MODERATION_BLOCKED" else "✗")
                print(f"  Seg1 {group_label}/{style}: {status}")

        active_styles = []
        for style in styles:
            result, _ = seg1_results.get(style, (False, None))
            if result == "MODERATION_BLOCKED":
                print(f"  ⛔ {group_label}/{style} ABANDONED — moderation")
                generation_log.append({"group": group, "style": style, "status": "moderation_blocked", "stage": "seg1"})
            elif result is True:
                active_styles.append(style)
            else:
                print(f"  ✗ {group_label}/{style} Seg1 FAILED")
                generation_log.append({"group": group, "style": style, "status": "failed", "stage": "seg1"})

        if not active_styles:
            print(f"  All {group_label} Seg1 failed. Skipping Seg2.")
            continue

        # Step 3: Seg2 concurrent
        print(f"\n{'='*60}\n{group_label}: Seg2 — CONCURRENT ({' + '.join(active_styles)})\n{'='*60}")
        seg2_results = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {}
            for style in active_styles:
                out_dir = str(EXP_DIR / "output" / f"{'a-buffer' if group == 'a' else 'b-nobuffer'}" / style)
                _, seg1_path = seg1_results[style]
                f = pool.submit(run_seg2, group, style, keys, all_assets.get(style, {}), out_dir, seg1_path)
                futures[f] = style
            for future in as_completed(futures):
                style = futures[future]
                result, path = future.result()
                seg2_results[style] = (result, path)
                status = "✓" if result is True else ("⛔MOD" if result == "MODERATION_BLOCKED" else "✗")
                print(f"  Seg2 {group_label}/{style}: {status}")

        # Step 4: Concat
        print(f"\n{'='*60}\n{group_label}: Concat + Audio Check\n{'='*60}")
        for style in active_styles:
            r2, _ = seg2_results.get(style, (False, None))
            if r2 != True:
                gen_status = "moderation_blocked" if r2 == "MODERATION_BLOCKED" else "failed"
                generation_log.append({"group": group, "style": style, "status": gen_status, "stage": "seg2"})
                continue
            out_dir = str(EXP_DIR / "output" / f"{'a-buffer' if group == 'a' else 'b-nobuffer'}" / style)
            seg1_path = seg1_results[style][1]
            seg2_path = seg2_results[style][1]
            final_path = os.path.join(out_dir, "final-30s.mp4")
            ok = concat_with_audio_check(seg1_path, seg2_path, final_path)
            if ok:
                key = f"{group_label}/{style}"
                final_videos[key] = final_path
                generation_log.append({"group": group, "style": style, "status": "success", "path": final_path})
            else:
                generation_log.append({"group": group, "style": style, "status": "audio_check_failed", "stage": "concat"})

    # Step 5: Save generation log
    log = {
        "experiment": "EXP-V7-020",
        "hypothesis": "H-120",
        "strategy": "Audio buffer A/B test, concurrent dual-track",
        "concurrent": True,
        "groups": groups,
        "styles": styles,
        "final_videos": final_videos,
        "details": generation_log,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = str(EXP_DIR / "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}\nSummary\n{'='*60}")
    for key, path in final_videos.items():
        print(f"  ✓ {key}: {path}")
    if not final_videos:
        print("  ⛔ No videos completed")
    print(f"Log: {log_path}")
    print("Done!")


if __name__ == "__main__":
    main()
