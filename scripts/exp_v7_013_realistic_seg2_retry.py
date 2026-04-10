#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.28.0",
# ]
# ///
"""
EXP-V7-013 Realistic — Seg2 only, pure text + video extension (no image refs)

Seg1 already generated successfully. Seg2 was blocked because FFA last-frame
triggered privacy filter. This version uses ONLY video extension + text prompt.
"""
import json, os, subprocess, sys, time
from pathlib import Path

BASE = Path.home() / "trinity-v7-consistency"
EXP_DIR = BASE / "experiments" / "exp-v7-013"

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


SEG2_PROMPT = (
    "Continuing EXACTLY from previous scene in same startup meeting room, cinematic realistic style, 9:16 vertical format. "
    "Same warm indoor lighting, same light wood table, same whiteboard, same glass door left and window right.\n\n"
    "Physical state of all characters (continuing from end of previous scene):\n"
    "[林远] Chinese male 28yo, tall thin, neat short black hair, rectangular face, BLACK SQUARE GLASSES, "
    "fair skin, sharp chin, thick eyebrows, dark blue fitted suit white shirt no tie, WHITE POCKET SQUARE. "
    "Sitting RIGHT side of table by window, body turned slightly toward door, left hand on armrest, right hand adjusting glasses.\n"
    "[苏晴] Chinese female 26yo, thin, shoulder-length BLACK HAIR with slight OUTWARD CURL, oval face, "
    "light makeup, bright alert eyes, GREY OVERSIZED HOODIE, dark blue jeans, white sneakers. "
    "Standing up halfway from chair, left hand pressing on table surface, looking toward glass door.\n"
    "[胖虎] Chinese male 30yo, STOCKY CHUBBY, BUZZ CUT, ROUND CHUBBY FACE small eyes, "
    "darker skin, stubble, RED-AND-BLUE HAWAIIAN SHIRT, khaki shorts, brown flip-flops. "
    "Still reclining at far end of table, chicken bone on napkin on table, hands behind head, smirking.\n\n"
    "Camera: SAME medium-wide shot, SAME angle as previous scene, no axis crossing. "
    "Three characters in same positions (glasses-man right/window, hoodie-girl left/door, hawaiian-shirt-guy far end).\n\n"
    "[Part 1] Glass door opens, a delivery guy in blue uniform peeks in holding two large bags of takeout food. "
    "苏晴's expression shifts from expectation to confusion, mouth slightly open. "
    "林远's hand adjusting glasses freezes mid-air, blinks twice. "
    "胖虎 slaps his thigh and stands up. 胖虎 says '全家桶到了！'\n\n"
    "[Part 2] Three people back in seats, table now covered with fried chicken bucket and fries. "
    "胖虎 grabs one drumstick in each hand, biting into both. "
    "林远 shakes head helplessly but picks up a chicken wing, takes a small bite. "
    "苏晴 eats fries while looking at laptop. 苏晴 suddenly freezes, finger stops, eyes widen. "
    "苏晴 says '等等。'\n\n"
    "[Part 3] 苏晴 puts down fries, both hands grab laptop, turns it toward 林远, speaking faster with excited eyes. "
    "苏晴 says '我发现一个漏洞，能省百分之四十的成本！' "
    "林远 puts down chicken wing, leans forward to look at screen, glasses reflecting light. "
    "胖虎 with mouth stuffed full of chicken, mumbles. 胖虎 says '我就说吃饱了才能想出好主意。'\n\n"
    "[Part 4] 林远 slowly sits up straight, looks at 胖虎 then at 苏晴, corner of mouth finally breaks into a smile. "
    "林远 says '拒绝收购。' 苏晴 nods, turns back to screen, continues typing. "
    "胖虎 raises drumstick like a microphone. 胖虎 says '合伙人干杯！' "
    "All three raise whatever food they're holding and bump them together, laughing.\n\n"
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement, natural pacing. All characters Chinese (East Asian). "
    "Comedy tone — expressive faces, natural comedic timing. Same meeting room, continuous scene. "
    "THREE characters always visible in same positions. "
    "Dialogue finishes before second 14, leaving ~1s silence buffer at end."
)


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
        if any(kw in stderr for kw in ["内容审核", "content moderation", "审核", "blocked", "SensitiveContent"]):
            print(f"  ⛔ MODERATION BLOCK — abandoning per standing order")
            return "MODERATION_BLOCKED"
        print(f"  ✗ Failed: {stderr[:500]}")
        return False
    
    print(f"  ✓ Video: {output_path}")
    return True


def concat_with_audio_check(seg1, seg2, output, fade=0.4):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", seg1],
        capture_output=True, text=True)
    dur = float(probe.stdout.strip())
    offset = dur - fade

    for label, path in [("Seg1", seg1), ("Seg2", seg2)]:
        audio_probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, text=True)
        if not audio_probe.stdout.strip():
            print(f"  ⛔ {label} has NO AUDIO — not deliverable")
            return False

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
        print(f"  Crossfade failed, trying simple concat...")
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
        a_probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=duration", "-of", "csv=p=0", output],
            capture_output=True, text=True)
        v_probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v",
             "-show_entries", "stream=duration", "-of", "csv=p=0", output],
            capture_output=True, text=True)
        a_dur = float(a_probe.stdout.strip()) if a_probe.stdout.strip() else 0
        v_dur = float(v_probe.stdout.strip()) if v_probe.stdout.strip() else 0
        if a_dur < v_dur * 0.9:
            print(f"  ⛔ AUDIO FAIL: audio={a_dur:.1f}s video={v_dur:.1f}s")
            return False
        print(f"  ✓ Concat done: {output} (audio={a_dur:.1f}s video={v_dur:.1f}s)")
        return True

    print(f"  ✗ Concat failed: {result.stderr[:300]}")
    return False


def main():
    keys = load_keys()
    assert keys["ark_key"], "ARK_API_KEY not found"
    assert keys["seedance_script"], "seedance.py not found"
    
    out_dir = str(EXP_DIR / "output" / "realistic")
    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    assert os.path.exists(seg1_path), f"Seg1 must exist: {seg1_path}"
    
    print(f"\n{'='*60}")
    print(f"EXP-V7-013 Realistic — Seg2 retry (video ext only, NO images)")
    print(f"{'='*60}")
    
    seg2_path = os.path.join(out_dir, "segment-02.mp4")
    # PURE video extension + text — NO image refs at all
    seg2_ok = call_seedance(keys, SEG2_PROMPT, [], seg2_path, input_video=seg1_path)
    
    if seg2_ok == "MODERATION_BLOCKED":
        print("⛔ EXPERIMENT ABANDONED — Seg2 moderation block even without images")
        log = {
            "experiment": "EXP-V7-013", "style": "realistic",
            "status": "ABANDONED", "reason": "Seg2 moderation blocked (video-ext only, no images)",
            "note": "Privacy filter blocks video extension with realistic human content",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }
        with open(os.path.join(out_dir, "generation-log.json"), "w") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        sys.exit(2)
    
    if not seg2_ok:
        print("FATAL: Segment 2 failed (non-moderation)")
        sys.exit(1)
    
    # Crossfade
    print("\n--- Crossfade + audio check ---")
    final = os.path.join(out_dir, "final-30s.mp4")
    concat_ok = concat_with_audio_check(seg1_path, seg2_path, final)
    
    log = {
        "experiment": "EXP-V7-013", "hypothesis": "H-132",
        "strategy": "Version D (text-only + video extension, NO image refs)",
        "style": "realistic",
        "approach": "PURE TEXT + VIDEO EXTENSION — zero image references to avoid privacy filter",
        "story": "合伙人 — 3角色创业喜剧", "character_count": 3,
        "seg2_prompt_length": len(SEG2_PROMPT),
        "crossfade_duration": 0.4,
        "audio_check_passed": concat_ok,
        "status": "COMPLETED" if concat_ok else "AUDIO_FAIL",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
    }
    with open(os.path.join(out_dir, "generation-log.json"), "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    
    if concat_ok:
        print(f"\n✓ Final video: {final}")
    print("Done!")


if __name__ == "__main__":
    main()
