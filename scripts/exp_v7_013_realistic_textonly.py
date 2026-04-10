#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.28.0",
# ]
# ///
"""
EXP-V7-013 Realistic Track — Text-only (no ref images due to Seedance privacy filter)

Per V7-010 finding: text-only character descriptions produce BETTER cross-segment
consistency than reference images for realistic track.

Usage:
    uv run scripts/exp_v7_013_realistic_textonly.py
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


# 3-character text-only descriptions — all visual anchors embedded in prompt
# Key: each character has 3+ distinguishing visual anchors
# 林远: 黑框眼镜 + 深蓝西装 + 瘦高白色口袋巾
# 苏晴: 齐肩微卷发 + 灰色卫衣 + 双肩包
# 胖虎: 寸头圆脸 + 红蓝花衬衫 + 壮实人字拖

SEG1_PROMPT = (
    "Startup meeting room scene, cinematic realistic style, 9:16 vertical format. "
    "Warm indoor lighting, light wood table, 4 grey office chairs, whiteboard with colorful data diagrams on white wall. "
    "Laptops, coffee cups, papers scattered on table. Glass door on left, floor-to-ceiling window on right with city skyline.\n\n"
    "Physical state of all characters:\n"
    "[林远] Chinese male 28 years old, 178cm tall and thin, neat short black hair, rectangular face, "
    "BLACK SQUARE GLASSES with thick rims, fair skin, sharp chin, thick eyebrows. "
    "Wearing dark blue fitted suit, white dress shirt no tie, WHITE POCKET SQUARE in breast pocket. "
    "Sitting RIGHT side of table by window, body upright, both hands crossed on table, glasses reflecting whiteboard light.\n"
    "[苏晴] Chinese female 26 years old, 163cm thin, shoulder-length BLACK HAIR with slight OUTWARD CURL at ends, "
    "oval face, light natural makeup, thin eyebrows, bright alert eyes. "
    "Wearing GREY OVERSIZED HOODIE, dark blue jeans, white sneakers. Black backpack on floor beside her chair. "
    "Sitting LEFT side of table by door, leaning forward, left hand on table looking at laptop screen, right hand on trackpad.\n"
    "[胖虎] Chinese male 30 years old, 175cm STOCKY and CHUBBY, BUZZ CUT black hair, ROUND CHUBBY FACE, "
    "small eyes, darker skin, stubble on jaw. "
    "Wearing RED-AND-BLUE HAWAIIAN SHIRT, khaki shorts, brown flip-flops. "
    "Sitting FAR END of table, reclining in chair, right hand holding chicken drumstick eating, left hand holding phone.\n\n"
    "Camera: Medium-wide shot from table's long side, all three characters visible. "
    "林远 (glasses, blue suit) right by window, 苏晴 (grey hoodie) left by door, "
    "胖虎 (hawaiian shirt, stocky) at far end. Camera at seated eye level.\n\n"
    "[Part 1] 林远 sits upright, both hands crossed on table, serious expression looking at whiteboard. "
    "Whiteboard shows '收购要约 ¥5000万' circled in red marker. "
    "林远 takes a deep breath, gaze shifts from whiteboard toward 苏晴. "
    "林远 says '我觉得应该拒绝。'\n\n"
    "[Part 2] 苏晴 lifts head abruptly from laptop screen, left index finger still on trackpad, "
    "eyebrows furrowed. 苏晴 says '拒绝？账上的钱只够撑三个月。' "
    "苏晴 right hand points at laptop screen, turning toward 林远. "
    "苏晴 says '你看看这个现金流。'\n\n"
    "[Part 3] 胖虎 chewing chicken drumstick, speaking with mouth full, muffled voice. "
    "胖虎 raises right hand with drumstick, waves it casually. "
    "胖虎 says '钱的事我来搞定。' "
    "林远 and 苏晴 both turn heads toward 胖虎 simultaneously, expressions half-skeptical.\n\n"
    "[Part 4] 胖虎 slowly pulls out phone with greasy fingers, swipes screen twice, shows mysterious smile. "
    "胖虎 says '我约了个人。' Doorbell rings from outside. "
    "All three pairs of eyes look toward glass door direction simultaneously.\n\n"
    "No subtitles, no slow motion, no characters looking at camera. "
    "Natural speed movement, natural pacing. All characters Chinese (East Asian). "
    "Comedy tone — expressive faces, natural comedic timing. "
    "THREE characters always visible: glasses-man (right/window), hoodie-girl (left/door), hawaiian-shirt-guy (far end). "
    "Dialogue must be spoken at normal conversational speed, all dialogue finishes before second 14."
)

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
            print(f"  ⛔ MODERATION BLOCK — abandoning experiment per standing order")
            return "MODERATION_BLOCKED"
        print(f"  ✗ Failed: {stderr[:500]}")
        return False
    
    print(f"  ✓ Video: {output_path}")
    return True


def concat_with_audio_check(seg1, seg2, output, fade=0.4):
    """Crossfade concat with mandatory audio check per standing order."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", seg1],
        capture_output=True, text=True)
    dur = float(probe.stdout.strip())
    offset = dur - fade

    # Pre-concat audio check
    for label, path in [("Seg1", seg1), ("Seg2", seg2)]:
        audio_probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, text=True)
        if not audio_probe.stdout.strip():
            print(f"  ⛔ {label} has NO AUDIO — not deliverable per standing order")
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
        # Final audio verification
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
            print(f"  ⛔ AUDIO CHECK FAILED: audio={a_dur:.1f}s video={v_dur:.1f}s")
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
    os.makedirs(out_dir, exist_ok=True)
    
    # Seg1: text-only, NO reference images
    print(f"\n{'='*60}")
    print(f"EXP-V7-013 Realistic (text-only) — Segment 1: 紧张谈判")
    print(f"{'='*60}")
    
    seg1_path = os.path.join(out_dir, "segment-01.mp4")
    seg1_ok = call_seedance(keys, SEG1_PROMPT, [], seg1_path)
    if seg1_ok == "MODERATION_BLOCKED":
        print("⛔ EXPERIMENT ABANDONED — moderation block on Seg1")
        save_log(out_dir, "ABANDONED", "Seg1 moderation blocked")
        sys.exit(2)
    if not seg1_ok:
        print("FATAL: Segment 1 failed")
        sys.exit(1)
    
    # Extract last frame for FFA
    print("\n--- Extracting last frame for FFA ---")
    last_frame = os.path.join(out_dir, "seg1-last-frame.jpg")
    subprocess.run([
        "ffmpeg", "-sseof", "-0.1", "-i", seg1_path,
        "-frames:v", "1", "-y", last_frame
    ], capture_output=True)
    
    # Seg2: text-only + last frame as FFA + video extension
    print(f"\n{'='*60}")
    print(f"EXP-V7-013 Realistic (text-only) — Segment 2: 全家桶反转")
    print(f"{'='*60}")
    
    # Use last frame as FFA reference (scene image, NOT person image — should pass privacy filter)
    seg2_images = [last_frame]
    
    seg2_ok = call_seedance(keys, SEG2_PROMPT, seg2_images, 
                            os.path.join(out_dir, "segment-02.mp4"),
                            input_video=seg1_path)
    if seg2_ok == "MODERATION_BLOCKED":
        print("⛔ EXPERIMENT ABANDONED — moderation block on Seg2")
        save_log(out_dir, "ABANDONED", "Seg2 moderation blocked")
        sys.exit(2)
    if not seg2_ok:
        print("FATAL: Segment 2 failed")
        sys.exit(1)
    
    # Crossfade concat with audio check
    print("\n--- Crossfade + audio check ---")
    final = os.path.join(out_dir, "final-30s.mp4")
    concat_ok = concat_with_audio_check(seg1_path, os.path.join(out_dir, "segment-02.mp4"), final)
    
    save_log(out_dir, "COMPLETED" if concat_ok else "AUDIO_FAIL", 
             "Text-only realistic dual segment",
             audio_ok=concat_ok)
    
    if concat_ok:
        print(f"\n✓ Final video: {final}")
    else:
        print(f"\n⛔ Video generated but audio check failed")
    print("Done!")


def save_log(out_dir, status, note, audio_ok=None):
    log = {
        "experiment": "EXP-V7-013",
        "hypothesis": "H-132",
        "strategy": "Version D (text-only + FFA + video extension)",
        "style": "realistic",
        "approach": "TEXT-ONLY — no character reference images (privacy filter + better consistency per V7-010 finding)",
        "story": "合伙人 — 3角色创业喜剧",
        "character_count": 3,
        "seg1_prompt_length": len(SEG1_PROMPT),
        "seg2_prompt_length": len(SEG2_PROMPT),
        "crossfade_duration": 0.4,
        "audio_check_passed": audio_ok,
        "status": status,
        "note": note,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = os.path.join(out_dir, "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"  Generation log: {log_path}")


if __name__ == "__main__":
    main()
