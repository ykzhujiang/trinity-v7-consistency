#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0"]
# ///
"""
EXP-V7-009 3D Seg2 retry — text-only (no images, only video extension + PSE).
"""
import json, os, subprocess, sys, time
from pathlib import Path

EXP_DIR = Path.home() / "trinity-v7-consistency" / "experiments" / "exp-v7-009" / "3d-animated"

PSE = (
    "Continuing exactly from the end of the previous video. Scene change: the young man (李明) has left the office and is now in a stainless steel elevator. "
    "李明: Chinese male, 28 years old, thin build, messy short black hair, wearing oversized dark blue cheap suit "
    "with white shirt and crooked tie, holding brown old briefcase in left hand, right shoulder leaning "
    "against stainless steel elevator wall, looking down at the floor with dejected expression. "
    "周老: Chinese male, 65 years old, wiry thin build, grey-white short hair, kind wrinkled face, tanned skin, "
    "wearing grey old T-shirt and black athletic shorts, bright yellow Pikachu slippers on feet, "
    "both hands in T-shirt pockets, relaxed posture leaning against opposite elevator wall, "
    "looking at 李明 with amused curiosity. "
    "Setting: 3D animated Pixar-quality stainless steel elevator interior, warm golden ceiling lights, digital floor display above door."
)

SEG2_PARTS = """[Part 1] The elevator is quiet, only the floor numbers change on the digital display. 李明 sighs, loosening his tie with his right hand. 周老 tilts his head looking at him with a warm squint. 周老 says "小伙子，刚才那句'咖啡比眼光不稳'，是你临场想的？"

[Part 2] 李明 looks up at 周老, notices his Pikachu slippers, expression puzzled. 李明 says "您...听到了？" 周老 pulls his right hand from his T-shirt pocket and waves it casually. 周老 says "隔壁办公室的，隔音不太好。" 周老 grins showing white teeth.

[Part 3] The elevator reaches ground floor, doors open. 周老 pulls a business card from his shorts pocket, holds it between two fingers toward 李明. 周老 says "我觉得你挺有意思。有空来聊聊。" 李明 takes the card, looks down, eyes suddenly widen, corner of mouth starts twitching involuntarily.

[Part 4] 李明 looks up toward 周老, but 周老 is already walking out of the elevator in his Pikachu slippers, right hand behind his back waving goodbye casually. 李明 stands frozen, holding the business card, mouth half-open, eyes wide. The elevator doors begin slowly closing."""

def main():
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    ark_key = os.environ.get("ARK_API_KEY")
    if not ark_key:
        try: ark_key = config["skills"]["entries"]["seedance-video"]["env"]["ARK_API_KEY"]
        except: ark_key = config.get("models",{}).get("providers",{}).get("ark",{}).get("apiKey")
    
    seedance = str(Path.home() / ".openclaw" / "workspace" / "skills" / "seedance-video" / "scripts" / "seedance.py")
    seg1 = str(EXP_DIR / "segment-01.mp4")
    seg2 = str(EXP_DIR / "segment-02.mp4")

    import requests
    print("Uploading seg1...")
    with open(seg1, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    video_url = resp.json()["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    print(f"  → {video_url}")

    prompt = (
        f"Extend @video1 by 15 seconds. "
        f"{PSE}\n\n"
        f"{SEG2_PARTS}\n\n"
        "3D animated Pixar/Disney quality. All characters are Chinese. "
        "No subtitles, no slow motion, no characters looking at camera. "
        "Natural speed movement. 9:16 vertical format. Consistent warm lighting."
    )

    cmd = ["python3", seedance, "run",
           "--prompt", prompt, "--ratio", "9:16", "--duration", "15",
           "--out", seg2, "--video", video_url]
    
    env = os.environ.copy()
    env["ARK_API_KEY"] = ark_key
    
    print(f"Prompt ({len(prompt)} chars, text-only, no images)")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    if result.returncode == 0:
        print(f"✓ Seg2: {seg2}")
    else:
        print(f"✗ Failed: {result.stderr[-500:]}")
        sys.exit(1)

    # Crossfade
    probe = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",seg1], capture_output=True, text=True)
    dur = float(probe.stdout.strip())
    final = str(EXP_DIR / "final-30s.mp4")
    subprocess.run(["ffmpeg","-i",seg1,"-i",seg2,"-filter_complex",f"xfade=transition=fade:duration=0.4:offset={dur-0.4}","-y",final], capture_output=True)
    print(f"✓ Final: {final}")

if __name__ == "__main__":
    main()
