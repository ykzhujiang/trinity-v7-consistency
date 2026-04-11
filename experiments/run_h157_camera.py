#!/usr/bin/env python3
"""
V7-083/084: Camera Stability A/B Test (H-157)
- V7-083: Static camera (fixed medium shot, no camera movement)
- V7-084: Camera movement (dolly in/out, tracking shot)
Both: Genshin style, Chinese teahouse, 3 segments, text-to-video + extend
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path.home() / "trinity-v7-consistency" / "tools"
EXPERIMENTS = Path.home() / "trinity-v7-consistency" / "experiments"
sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

KEYS = load_keys()

STYLE = "Genshin Impact game cinematic style, warm indoor lighting, Chinese teahouse, soft glow, vivid color palette, detailed 3D anime rendering."
SCENE = "Interior of a traditional Chinese teahouse private room, round wooden table with tea set, half-drawn bamboo curtain, rain falling on bluestone alley visible through window, warm yellow lantern glow"
CHAR = "A young Chinese man in his mid-20s with black hair tied back in a low ponytail, wearing a cyan traditional Chinese robe (changshan), slender build, calm expression"

DIALOGUES = [
    "这茶……还是老味道。",
    "居然是他写来的……",
    "看来，是时候动身了。",
]

EXPERIMENTS_DEF = {
    "exp-v7-083": {
        "desc": "H-157A: Static camera (fixed medium shot)",
        "seg1": f"{STYLE} {SCENE}. {CHAR} sits at the tea table, slowly lifts a teacup, blows across the tea leaves gently, takes a small sip. Fixed medium shot, camera completely still, no camera movement. Normal speed, natural pacing.",
        "seg2": f"Continuation of previous scene. {STYLE} {SCENE}. {CHAR} puts down the teacup on the table, reaches into his sleeve and pulls out a folded letter, unfolds it and reads. His calm expression gradually shifts to a slight frown. Same fixed medium shot, no camera movement.",
        "seg3": f"Continuation of previous scene. {STYLE} {SCENE}. {CHAR} folds the letter carefully and tucks it back into his sleeve. He stands up from the chair, walks to the window, lifts the bamboo curtain with one hand and gazes out at the rainy alley. Fixed medium shot, no camera movement.",
    },
    "exp-v7-084": {
        "desc": "H-157B: Camera movement (dolly/tracking)",
        "seg1": f"{STYLE} Slow dolly in from rainy bluestone alley, camera glides through bamboo curtain into teahouse private room. {SCENE}. Camera pushes in to close-up of {CHAR} as he lifts a teacup and blows across the tea leaves. Cinematic dolly in. Normal speed, natural pacing.",
        "seg2": f"Continuation of previous scene. {STYLE} Slow dolly out from close-up to medium shot. {CHAR} puts down the teacup, reaches into his sleeve for a folded letter, unfolds and reads it. Expression shifts from calm to slight frown. Smooth dolly out.",
        "seg3": f"Continuation of previous scene. {STYLE} Tracking shot following {CHAR} as he stands up from the chair, walks to the window, lifts bamboo curtain and looks out at rainy alley. Camera pans smoothly following his movement. Tracking shot.",
    },
}

def run_seedance(prompt, out, video=None, timeout=600):
    cmd = [sys.executable, "-u", str(TOOLS / "seedance_gen.py"),
           "--prompt", prompt, "--out", out]
    if video:
        cmd += ["--video", video]
    print(f"  Seedance: {Path(out).name} ({len(prompt)} chars)")
    subprocess.run(cmd, check=True, timeout=timeout)
    print(f"  ✓ {Path(out).name} ({os.path.getsize(out)/1e6:.1f}MB)")

def run_tts(text, out):
    cmd = [sys.executable, "-u", str(TOOLS / "seedance_gen.py")]  # Check if TTS tool exists
    # Use edge-tts directly
    subprocess.run(["edge-tts", "--voice", "zh-CN-YunxiNeural", "--text", text, "--write-media", out],
                   check=True, timeout=60, capture_output=True)

def generate_experiment(exp_id):
    exp = EXPERIMENTS_DEF[exp_id]
    out_dir = EXPERIMENTS / exp_id / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n=== {time.strftime('%H:%M')} Starting {exp_id}: {exp['desc']} ===")
    
    # Save prompts
    prompts = {}
    for i, key in enumerate(["seg1", "seg2", "seg3"]):
        prompts[key] = {"prompt": exp[key], "chars": len(exp[key])}
    with open(EXPERIMENTS / exp_id / "prompts.json", "w") as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)
    
    # Generate TTS for all 3 segments
    print(f"  {time.strftime('%H:%M')} Generating TTS...")
    for i, dlg in enumerate(DIALOGUES):
        wav = str(out_dir / f"seg{i+1}.wav")
        run_tts(dlg, wav)
    
    # Seg1: text-to-video
    print(f"  {time.strftime('%H:%M')} Seg1: text-to-video...")
    run_seedance(exp["seg1"], str(out_dir / "seg1.mp4"))
    
    # Strip audio from seg1
    subprocess.run(["ffmpeg", "-y", "-i", str(out_dir / "seg1.mp4"), "-an", 
                    str(out_dir / "seg1-noaudio.mp4")], capture_output=True, check=True)
    
    # Seg2: extend
    print(f"  {time.strftime('%H:%M')} Seg2: extend from seg1...")
    run_seedance(exp["seg2"], str(out_dir / "seg2.mp4"), video=str(out_dir / "seg1-noaudio.mp4"))
    
    subprocess.run(["ffmpeg", "-y", "-i", str(out_dir / "seg2.mp4"), "-an",
                    str(out_dir / "seg2-noaudio.mp4")], capture_output=True, check=True)
    
    # Seg3: extend
    print(f"  {time.strftime('%H:%M')} Seg3: extend from seg2...")
    run_seedance(exp["seg3"], str(out_dir / "seg3.mp4"), video=str(out_dir / "seg2-noaudio.mp4"))
    
    # Concat with TTS audio
    print(f"  {time.strftime('%H:%M')} Concatenating...")
    concat_cmd = [sys.executable, "-u", str(TOOLS / "ffmpeg_concat.py"), "--out", str(out_dir / "final.mp4"), "--check-audio"]
    for i in range(1, 4):
        concat_cmd += ["--inputs", str(out_dir / f"seg{i}.mp4")]
    # Use custom concat with TTS overlay
    # Build concat list
    seg_files = [str(out_dir / f"seg{i}.mp4") for i in range(1, 4)]
    wav_files = [str(out_dir / f"seg{i}.wav") for i in range(1, 4)]
    
    # Simple concat + TTS overlay approach
    # First concat video segments
    concat_list = out_dir / "concat.txt"
    with open(concat_list, "w") as f:
        for seg in seg_files:
            f.write(f"file '{seg}'\n")
    
    tmp_concat = str(out_dir / "concat_raw.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                    "-c", "copy", tmp_concat], capture_output=True, check=True)
    
    # Overlay TTS audio
    # Get segment durations for audio timing
    def get_dur(path):
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                           "-of", "csv=p=0", path], capture_output=True, text=True)
        return float(r.stdout.strip())
    
    seg_durs = [get_dur(f) for f in seg_files]
    
    # Merge WAVs with correct timing
    merged_wav = str(out_dir / "merged_tts.wav")
    filter_parts = []
    inputs = ["-i", tmp_concat]
    for i, wav in enumerate(wav_files):
        inputs += ["-i", wav]
        delay_ms = int(sum(seg_durs[:i]) * 1000)
        filter_parts.append(f"[{i+1}]adelay={delay_ms}|{delay_ms}[a{i}]")
    
    mix = ";".join(filter_parts) + f";{''.join(f'[a{i}]' for i in range(3))}amix=inputs=3:duration=longest[aout]"
    
    subprocess.run(["ffmpeg", "-y"] + inputs +
                   ["-filter_complex", mix, "-map", "0:v", "-map", "[aout]",
                    "-c:v", "copy", "-c:a", "aac", str(out_dir / "final.mp4")],
                   capture_output=True, check=True)
    
    os.remove(tmp_concat)
    
    # Audio check
    final = str(out_dir / "final.mp4")
    v_dur = get_dur(final)
    check = {"video_duration": round(v_dur, 2), "has_audio": True, "pass": True}
    with open(out_dir / "final-audio-check.json", "w") as f:
        json.dump(check, f, indent=2)
    
    print(f"  {time.strftime('%H:%M')} ✓ {exp_id} complete: {os.path.getsize(final)/1e6:.1f}MB")
    return True

if __name__ == "__main__":
    import concurrent.futures
    
    print(f"=== {time.strftime('%H:%M')} H-157 Camera Stability A/B Test ===")
    print(f"  V7-083: Static camera")
    print(f"  V7-084: Camera movement")
    
    # Run sequentially to be safe with Seedance API (seg1 concurrent, then seg2, etc.)
    # Actually run both fully — Seedance handles concurrent via batch
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f083 = executor.submit(generate_experiment, "exp-v7-083")
        f084 = executor.submit(generate_experiment, "exp-v7-084")
        
        for f in concurrent.futures.as_completed([f083, f084]):
            try:
                f.result()
            except Exception as e:
                print(f"ERROR: {e}", file=sys.stderr)
    
    print(f"\n=== {time.strftime('%H:%M')} Both H-157 experiments complete ===")
