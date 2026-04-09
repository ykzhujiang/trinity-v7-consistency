#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0"]
# ///
"""
EXP-V7-009 3D-animated Segment 2 retry — drop FFA last frame (privacy filtered).
Use PSE + video extension + character refs only (Version D minus FFA image).
"""

import json, os, subprocess, sys, time
from pathlib import Path

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-009" / "3d-animated"

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

SEG2_PARTS = """[Part 1] 电梯内安静，只有数字屏上楼层数字在跳。李明低着头叹了口气，右手松了松领带。周老侧头看他，眼睛眯起来带着笑意。周老 says "小伙子，刚才那句'咖啡比眼光不稳'，是你临场想的？"

[Part 2] 李明抬头看向周老，注意到他的皮卡丘拖鞋，表情困惑。李明 says "您...听到了？"周老从T恤口袋里掏出右手摆了摆。周老 says "隔壁办公室的，隔音不太好。"周老咧嘴笑露出白牙。

[Part 3] 电梯到达一楼，门打开。周老从短裤口袋里掏出一张名片，两根手指夹着递向李明。周老 says "我觉得你挺有意思。有空来聊聊。"李明接过名片低头一看，眼睛猛然睁大，嘴角开始不自主抽搐。

[Part 4] 李明抬头看向周老，周老已经踩着皮卡丘拖鞋悠闲走出电梯，右手背在身后摆了摆手。李明站在原地，手拿名片，嘴巴半张，眼睛瞪大。电梯门开始缓缓关闭。"""


def load_keys():
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    ark_key = os.environ.get("ARK_API_KEY")
    if not ark_key:
        try:
            ark_key = config["skills"]["entries"]["seedance-video"]["env"]["ARK_API_KEY"]
        except (KeyError, TypeError):
            ark_key = config.get("models", {}).get("providers", {}).get("ark", {}).get("apiKey")
    seedance_script = Path.home() / ".openclaw" / "workspace" / "skills" / "seedance-video" / "scripts" / "seedance.py"
    return ark_key, str(seedance_script)


def upload_to_tmpfiles(local_path):
    import requests
    print(f"  Uploading {local_path}...")
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    page_url = resp.json()["data"]["url"]
    return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")


def main():
    ark_key, seedance_script = load_keys()
    assert ark_key and seedance_script

    seg1 = str(EXP_DIR / "segment-01.mp4")
    seg2_out = str(EXP_DIR / "segment-02.mp4")

    # Character refs only (no last-frame FFA to avoid privacy filter)
    assets_dir = str(EXP_DIR / "assets")
    images = []
    for name in ["char-李明.webp", "char-周老.webp", "scene-elevator.webp"]:
        p = os.path.join(assets_dir, name)
        if os.path.exists(p):
            images.append(p)

    img_refs = ["@image1 as character 李明", "@image2 as character 周老", "@image3 as the elevator interior"]
    
    prompt = (
        ", ".join(img_refs[:len(images)]) + ". "
        f"Extend @video1 by 15 seconds. "
        f"Continue seamlessly from the end of the previous video. "
        f"Scene transition: 李明 walked from the office to the elevator. "
        f"{PSE_3D}\n\n"
        f"Camera: Medium shot, inside elevator, camera in the corner opposite the door.\n\n"
        f"{SEG2_PARTS}\n\n"
        f"All characters are Chinese. 3D animated Pixar quality style. "
        "No subtitles, no slow motion, no characters looking at camera. "
        "Natural speed movement. 9:16 vertical format. "
        "Stainless steel elevator interior, warm overhead lighting, digital floor display. "
        "Consistent lighting throughout."
    )

    video_url = upload_to_tmpfiles(seg1)

    cmd = ["python3", seedance_script, "run",
           "--prompt", prompt, "--ratio", "9:16",
           "--duration", "15", "--out", seg2_out,
           "--video", video_url]
    for img in images:
        cmd.extend(["--image", img])

    env = os.environ.copy()
    env["ARK_API_KEY"] = ark_key

    print(f"Prompt ({len(prompt)} chars): {prompt[:300]}...")
    print(f"Images: {len(images)} (no last-frame FFA), Video ref: True")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    if result.returncode == 0:
        print(f"✓ Segment 2: {seg2_out}")
    else:
        print(f"✗ Failed: {result.stderr[:500]}")
        sys.exit(1)

    # Crossfade concat
    seg1_mp4 = str(EXP_DIR / "segment-01.mp4")
    final = str(EXP_DIR / "final-30s.mp4")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", seg1_mp4],
        capture_output=True, text=True)
    dur = float(probe.stdout.strip())
    offset = dur - 0.4
    subprocess.run([
        "ffmpeg", "-i", seg1_mp4, "-i", seg2_out,
        "-filter_complex", f"xfade=transition=fade:duration=0.4:offset={offset}",
        "-y", final
    ], capture_output=True, text=True)
    print(f"✓ Final: {final}")


if __name__ == "__main__":
    main()
