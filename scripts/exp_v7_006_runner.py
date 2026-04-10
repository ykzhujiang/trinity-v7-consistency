#!/usr/bin/env python3
"""
EXP-V7-006 — Cross-Segment Consistency A/B/C/D Test

Reuses Seg1 from V7-004, generates Seg2 variants with different strategies:
  A: Baseline (video-extension, already done)
  B: First Frame Anchoring (FFA)
  C: Precise Physical State Echo (PSE) 
  D: FFA + PSE + Crossfade

Usage:
    python3 exp_v7_006_runner.py --version D --style anime
    python3 exp_v7_006_runner.py --version B --style 3d-animated
"""

import argparse, json, os, subprocess, sys, time
from pathlib import Path

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-006"
V7_004_DIR = BASE / "experiments" / "exp-v7-004"
V7_004R_DIR = BASE / "experiments" / "exp-v7-004-realistic"
PIPELINE = BASE / "scripts" / "v7_pipeline.py"

# PSE descriptions based on visual analysis of Seg1 last frames
PSE_ANIME = (
    "Continuing exactly from: [林姐] is standing on the left side of frame, "
    "body slightly turned right toward [小刘], left hand holding her stomach area (laughing), "
    "right hand holding an orange cat food bag at chest height, mouth wide open laughing, "
    "eyes squeezed shut with laugh lines, wearing light blue button-up shirt and black pants, "
    "silver-rimmed glasses, shoulder-length black straight hair. "
    "[小刘] is on the right side of frame, bending forward at the waist, face bright red with "
    "embarrassment, wearing yellow delivery uniform with yellow helmet, white delivery box on his back, "
    "both hands reaching into the delivery box which is now lowered and open in front of him. "
    "Background: modern office lobby with marble floor, green potted plants on left, "
    "glass revolving door behind right, warm natural daylight streaming in."
)

PSE_3D = (
    "Continuing exactly from: [林姐] stands on the left side of frame in Pixar/3D animated style, "
    "body angled slightly toward [小刘], left hand on her stomach (still chuckling), "
    "right hand holding an orange cat food package at mid-torso height, mouth open in a big smile, "
    "wearing light blue collared shirt and dark pants, black-rimmed glasses, shoulder-length black hair. "
    "[小刘] on the right side, leaning forward, face flushed red, wearing yellow delivery jacket with "
    "yellow helmet (闪送 logo), white square delivery box on back, both hands reaching into the open "
    "delivery box in front of him. Background: spacious 3D animated modern lobby, marble floor, "
    "green plant on left, glass revolving door behind, warm golden sunlight, city skyline through windows."
)

# Seg2 storyboard content
SEG2_PARTS = """[Part 1] 小刘手忙脚乱从外卖箱里翻东西，一个蓝色折叠瑜伽垫弹出来掉在大理石地上发出啪的一声。他慌张弯腰捡起塞回去，又掏出一包红色泡面。小刘 says "这也不是...等等啊我找找！"林姐歪头看着他，嘴角上扬忍笑。

[Part 2] 小刘终于从箱子最底部翻出一个印着"鱼香肉丝套餐"字样的外卖袋，双手举过头顶，脸上露出狂喜表情。小刘 says "找到了！！鱼香肉丝套餐！"林姐拍手鼓掌三下，把猫粮递还给他。

[Part 3] 林姐双手接过正确的外卖袋，打开检查里面的餐盒，满意地点头。小刘蹲在地上把瑜伽垫和泡面往箱子里塞，手忙脚乱。林姐 says "对了对了这才是。你那个箱子是百宝箱吧？"

[Part 4] 小刘站起来背好外卖箱，不好意思地右手挠后脑勺露出憨笑。林姐左手拎着外卖袋，右手拍了拍他左肩膀，笑着竖起大拇指。两人并排站着，背景是阳光照进来的大堂。林姐 says "加油啊外卖侠！下次别再送猫粮了！"小刘咧嘴笑着转身朝玻璃门跑去，右手高举挥手告别。"""

CONSISTENCY_SUFFIX = (
    "Maintain exact same character appearances, clothing, and office setting. "
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement. 9:16 vertical format. "
    "Identical background, same marble floor, same plants, same revolving door. "
    "Consistent warm indoor lighting."
)


def get_seg1_path(style):
    if style == "anime":
        return str(V7_004_DIR / "output" / "segment-01.mp4")
    else:
        return str(V7_004R_DIR / "output" / "segment-01.mp4")


def get_last_frame(style):
    version_dir = EXP_DIR / "version-b-ffa" / style
    return str(version_dir / "seg1-last-frame.jpg")


def get_asset_paths(style):
    if style == "anime":
        assets_dir = V7_004_DIR / "output" / "assets"
    else:
        assets_dir = V7_004R_DIR / "output" / "assets"
    paths = []
    for f in sorted(assets_dir.glob("*.png")):
        paths.append(str(f))
    return paths


def upload_to_tmpfiles(local_path):
    import requests
    print(f"  Uploading {local_path}...")
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    page_url = resp.json()["data"]["url"]
    return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")


def call_seedance(prompt, images, output_path, input_video=None, duration=15):
    """Call seedance directly."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    
    ark_key = os.environ.get("ARK_API_KEY")
    if not ark_key:
        try:
            ark_key = config["skills"]["entries"]["seedance-video"]["env"]["ARK_API_KEY"]
        except (KeyError, TypeError):
            ark_key = config.get("models", {}).get("providers", {}).get("ark", {}).get("apiKey")
    
    seedance_script = str(Path.home() / ".openclaw" / "workspace" / "skills" / "seedance-video" / "scripts" / "seedance.py")
    
    cmd = ["python3", seedance_script, "run",
           "--prompt", prompt, "--ratio", "9:16",
           "--duration", str(duration), "--out", output_path]
    
    if input_video:
        if os.path.isfile(input_video):
            input_video = upload_to_tmpfiles(input_video)
        cmd.extend(["--video", input_video])
    
    for img in images:
        cmd.extend(["--image", img])
    
    env = os.environ.copy()
    if ark_key:
        env["ARK_API_KEY"] = ark_key
    
    print(f"  Prompt: {prompt[:300]}...")
    print(f"  Images: {len(images)}, Video: {input_video is not None}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1200)
    
    if result.returncode == 0:
        print(f"  ✓ Video: {output_path}")
        return True
    else:
        print(f"  ✗ Failed: {result.stderr[:500]}")
        return False


def build_prompt_version_b(style):
    """FFA: last frame as @image1 + video extension"""
    pse = ""  # no PSE for version B
    return (
        f"@image1 as the first frame of this scene. "
        f"Extend @video1 by 15 seconds. "
        f"Continue the scene seamlessly from this exact frame.\n\n"
        f"{SEG2_PARTS}\n\n{CONSISTENCY_SUFFIX}"
    )


def build_prompt_version_c(style):
    """PSE: precise physical state echo + video extension"""
    pse = PSE_ANIME if style == "anime" else PSE_3D
    return (
        f"Extend @video1 by 15 seconds. "
        f"{pse}\n\n"
        f"{SEG2_PARTS}\n\n{CONSISTENCY_SUFFIX}"
    )


def build_prompt_version_d(style):
    """FFA + PSE + video extension (crossfade applied in post)"""
    pse = PSE_ANIME if style == "anime" else PSE_3D
    return (
        f"@image1 as the first frame of this scene. "
        f"Extend @video1 by 15 seconds. "
        f"Continue seamlessly from this exact frame. "
        f"{pse}\n\n"
        f"{SEG2_PARTS}\n\n{CONSISTENCY_SUFFIX}"
    )


def concat_with_crossfade(seg1, seg2, output, fade_duration=0.4):
    """Concatenate with crossfade transition."""
    # Get seg1 duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", seg1],
        capture_output=True, text=True
    )
    seg1_dur = float(probe.stdout.strip())
    offset = seg1_dur - fade_duration
    
    cmd = [
        "ffmpeg", "-i", seg1, "-i", seg2,
        "-filter_complex",
        f"xfade=transition=fade:duration={fade_duration}:offset={offset}",
        "-y", output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✓ Crossfade concat: {output}")
        return True
    else:
        print(f"  ✗ Crossfade failed: {result.stderr[:300]}")
        return False


def concat_hard_cut(seg1, seg2, output):
    """Simple hard-cut concatenation."""
    concat_list = output + ".concat.txt"
    with open(concat_list, "w") as f:
        f.write(f"file '{os.path.abspath(seg1)}'\n")
        f.write(f"file '{os.path.abspath(seg2)}'\n")
    result = subprocess.run(
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart",
         "-y", output],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return False
    # Verify audio covers full duration
    check = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=duration", "-of", "csv=p=0", output],
        capture_output=True, text=True
    )
    audio_dur = float(check.stdout.strip()) if check.stdout.strip() else 0
    vcheck = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v",
         "-show_entries", "stream=duration", "-of", "csv=p=0", output],
        capture_output=True, text=True
    )
    video_dur = float(vcheck.stdout.strip()) if vcheck.stdout.strip() else 0
    if audio_dur < video_dur * 0.9:
        print(f"  ⛔ AUDIO CHECK FAILED: audio={audio_dur:.1f}s video={video_dur:.1f}s")
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", choices=["B", "C", "D"], required=True)
    parser.add_argument("--style", choices=["anime", "3d-animated"], required=True)
    args = parser.parse_args()

    version_map = {"B": "version-b-ffa", "C": "version-c-pse", "D": "version-d-combined"}
    out_dir = EXP_DIR / version_map[args.version] / args.style
    out_dir.mkdir(parents=True, exist_ok=True)

    seg1 = get_seg1_path(args.style)
    seg2_out = str(out_dir / "segment-02.mp4")
    
    # Copy seg1 for reference
    subprocess.run(["cp", seg1, str(out_dir / "segment-01.mp4")])

    # Build prompt based on version
    if args.version == "B":
        prompt = build_prompt_version_b(args.style)
        images = [get_last_frame(args.style)] + get_asset_paths(args.style)
        input_video = seg1
    elif args.version == "C":
        prompt = build_prompt_version_c(args.style)
        images = get_asset_paths(args.style)
        input_video = seg1
    elif args.version == "D":
        prompt = build_prompt_version_d(args.style)
        images = [get_last_frame(args.style)] + get_asset_paths(args.style)
        input_video = seg1

    print(f"\n{'='*60}")
    print(f"EXP-V7-006 Version {args.version} — {args.style}")
    print(f"{'='*60}")

    # Generate Seg2
    ok = call_seedance(prompt, images, seg2_out, input_video=input_video)
    
    if not ok:
        print("FAILED: Seg2 generation failed")
        sys.exit(1)

    # Concatenate
    final = str(out_dir / "final-30s.mp4")
    if args.version == "D":
        concat_with_crossfade(str(out_dir / "segment-01.mp4"), seg2_out, final)
    else:
        concat_hard_cut(str(out_dir / "segment-01.mp4"), seg2_out, final)

    # Save generation log
    log = {
        "experiment": "EXP-V7-006",
        "version": args.version,
        "style": args.style,
        "prompt": prompt,
        "images": images,
        "input_video": seg1,
        "crossfade": args.version == "D",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = str(out_dir / "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Results in {out_dir}")


if __name__ == "__main__":
    main()
