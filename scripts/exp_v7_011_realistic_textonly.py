#!/usr/bin/env python3
"""
EXP-V7-011 Realistic Track — Text-only fallback (no ref images due to privacy filter)
"""
import json, os, subprocess, sys, time
from pathlib import Path

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-011"

def load_keys():
    config = {}
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    ark_key = os.environ.get("ARK_API_KEY")
    if not ark_key:
        try: ark_key = config["skills"]["entries"]["seedance-video"]["env"]["ARK_API_KEY"]
        except: pass
        if not ark_key:
            try: ark_key = config["models"]["providers"]["ark"]["apiKey"]
            except: pass
    seedance_script = Path.home() / ".openclaw" / "workspace" / "skills" / "seedance-video" / "scripts" / "seedance.py"
    return {"ark_key": ark_key, "seedance_script": str(seedance_script) if seedance_script.exists() else None}

SEG1_PROMPT = (
    "Interview room scene, cinematic realistic style. "
    "Physical state: [小赵] Chinese male 25 years old, thin, soft slightly curly black short hair, "
    "round baby face, single eyelid small eyes, fair skin, wearing plaid shirt tucked into khaki pants "
    "brown sneakers, sitting in grey chair left side of white table, hands on knees, slightly hunched, "
    "black backpack on floor beside chair, looking down at table. "
    "[HR姐姐] Chinese female 30 years old, medium build, black shoulder-length bob cut, "
    "long face high cheekbones thin lips, fair skin, grey professional blazer black turtleneck, "
    "black stilettos, sitting opposite side, upright posture, left hand flipping printed resume on table, "
    "right hand holding black pen, looking down at resume. "
    "Camera: Medium shot, interview room interior, camera on right side angled toward 小赵. "
    "Both characters visible.\n\n"
    "[Part 1] 小赵 sits nervously, right fingers rubbing trouser seam, left hand gripping knee, "
    "shoulders slightly raised. HR姐姐 flips resume, taps pen on table twice.\n"
    "[Part 2] HR姐姐 looks up with serious professional expression. HR姐姐 says '说说你最大的优点？' "
    "小赵 blurts out '我特别会摸鱼。' immediately claps both hands over mouth, eyes wide.\n"
    "[Part 3] HR姐姐 mouth twitches, grabs resume to hide face pretending to read. "
    "小赵 waves hands frantically. 小赵 says '我是说我效率特别高，空闲时间比较多……'\n"
    "[Part 4] HR姐姐 puts resume down, face slightly red, forces serious expression. "
    "HR姐姐 says '下一个问题——你为什么从上家离职？' 小赵 swallows nervously.\n\n"
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed, 9:16 vertical. Cool white office lighting. All characters Chinese (East Asian). "
    "Comedy tone, expressive faces. "
    "Minimalist white interview room, white table, grey chairs, resume and water on table, "
    "floor-to-ceiling window with blurred city skyline."
)

SEG2_PROMPT = (
    "Continuing exactly from previous scene in same interview room, cinematic realistic style. "
    "[小赵] Chinese male 25 years old, thin, soft curly black short hair, round baby face, "
    "single eyelid, fair skin, plaid shirt khaki pants, sitting left side, leaning back, hands on armrests, thinking. "
    "[HR姐姐] Chinese female 30 years old, black bob, grey blazer black turtleneck, "
    "sitting opposite, leaning forward, left elbow on table, right hand with pen above resume, suppressing smile. "
    "Same interview room.\n\n"
    "[Part 1] 小赵 tilts head thinking, then sits up straight with earnest expression. "
    "小赵 says '因为我发现老板的代码写得比我还烂。' HR姐姐's pen slips and drops onto table.\n"
    "[Part 2] 小赵 shrinks into chair, shoulders up to ears. HR姐姐 bends to pick up pen, "
    "laughs behind table cover, shoulders visibly shaking.\n"
    "[Part 3] HR姐姐 sits up, takes deep breath, forces professional face. "
    "HR姐姐 says '最后一个问题，你的期望薪资？' 小赵 thinks, nods sincerely. 小赵 says '够还花呗就行。'\n"
    "[Part 4] HR姐姐 finally bursts out laughing, slaps table. HR姐姐 says '你被录用了。' "
    "小赵 stunned. 小赵 says '啊？真的？' HR姐姐 waves pen at him. HR姐姐 says '我们就缺一个敢说真话的。' "
    "小赵's face slowly breaks into a goofy grin.\n\n"
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed, 9:16 vertical. Same cool white lighting. All Chinese. Comedy tone. Same room."
)

def upload_to_tmpfiles(local_path):
    import requests
    print(f"  Uploading {local_path}...")
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    page_url = resp.json()["data"]["url"]
    return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")

def call_seedance(keys, prompt, output_path, input_video=None):
    cmd = ["python3", keys["seedance_script"], "run",
           "--prompt", prompt, "--ratio", "9:16",
           "--duration", "15", "--out", output_path]
    if input_video:
        if os.path.isfile(input_video):
            input_video = upload_to_tmpfiles(input_video)
        cmd.extend(["--video", input_video])
    env = os.environ.copy()
    if keys["ark_key"]:
        env["ARK_API_KEY"] = keys["ark_key"]
    print(f"  Prompt ({len(prompt)} chars): {prompt[:200]}...")
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

def main():
    keys = load_keys()
    assert keys["ark_key"], "ARK_API_KEY not found"
    assert keys["seedance_script"], "seedance.py not found"

    out_dir = str(EXP_DIR / "output" / "realistic")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print("EXP-V7-011 Realistic — Text-only (privacy filter fallback)")
    print(f"{'='*60}")

    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    print("\n--- Segment 1 ---")
    if not call_seedance(keys, SEG1_PROMPT, seg1_path):
        print("FATAL: Segment 1 failed"); sys.exit(1)

    # FFA
    last_frame = os.path.join(out_dir, "seg1-last-frame.jpg")
    subprocess.run(["ffmpeg", "-sseof", "-0.1", "-i", seg1_path,
                    "-frames:v", "1", "-y", last_frame], capture_output=True)
    print(f"  → FFA: {last_frame}")

    print("\n--- Segment 2 (video ext + PSE) ---")
    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    if not call_seedance(keys, SEG2_PROMPT, seg2_path, input_video=seg1_path):
        print("FATAL: Segment 2 failed"); sys.exit(1)

    print("\n--- Crossfade ---")
    final = os.path.join(out_dir, "final-30s.mp4")
    concat_crossfade(seg1_path, seg2_path, final)

    log = {
        "experiment": "EXP-V7-011", "hypothesis": "H-126",
        "strategy": "Text-only + video ext + PSE (privacy filter fallback)",
        "style": "realistic", "story": "面试翻车王 — 职场喜剧",
        "seg1_prompt": SEG1_PROMPT, "seg2_prompt": SEG2_PROMPT,
        "note": "No ref images — Seedance privacy filter blocked realistic character refs",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    with open(os.path.join(out_dir, "generation-log.json"), "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Final: {final}")
    print("Done!")

if __name__ == "__main__":
    main()
