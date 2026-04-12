#!/usr/bin/env python3 -u
"""
V7-091: Seg2/3 Prompt Length A/B Test
- A: Full repeat (~700 char per segment)  
- B: Minimal Seg2/3 (~200 char per segment)
- Shared Seg1 (text-to-video)
- 3 Segment extend chain, Genshin style, Chinese TTS
"""

import json, os, subprocess, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLS = Path.home() / "trinity-v7-consistency" / "tools"
sys.path.insert(0, str(TOOLS))
from config_loader import load_keys
from seedance_gen import run_seedance, upload_to_tmpfiles

EXPDIR = Path(__file__).parent
OUTDIR_A = EXPDIR / "output-a"
OUTDIR_B = EXPDIR / "output-b"
OUTDIR_A.mkdir(exist_ok=True)
OUTDIR_B.mkdir(exist_ok=True)

# ── Prompts ──────────────────────────────────────────────

PROMPT_SEG1 = (
    "Genshin Impact 3D anime style, bright daylight. Ancient fantasy town marketplace, "
    "stone-paved street, wooden shops with red lanterns, steam rising from a bun stall. "
    "A young man with short curly black hair, amber eyes, wearing a dark blue robe with "
    "gold belt, a cloth-wrapped sword on his back, walks through the bustling market. "
    "He sniffs the air, turns toward a bun stall where a young woman with brown twin-tails, "
    "round face, red apron over white shirt, waves him over cheerfully. He approaches and "
    "reaches for his coin pouch. Camera: medium shot tracking the man, then settling into "
    "a two-shot at the stall."
)

# A version: full repeat
PROMPT_A_SEG2 = (
    "Continuation of previous scene. Genshin Impact 3D anime style, bright daylight, "
    "ancient marketplace. The young man with short curly black hair, amber eyes, dark blue "
    "robe with gold belt, cloth-wrapped sword on back, takes a big bite of the steamed bun. "
    "His eyes widen with surprise and delight. The young woman with brown twin-tails, round "
    "face, red apron, grins proudly with hands on hips. Suddenly a loud shout echoes from "
    "down the street. The man stops chewing and turns his head sharply toward the sound, "
    "expression turning serious. Camera: close-up on man's face reaction, then pan toward "
    "the sound direction."
)

PROMPT_A_SEG3 = (
    "Continuation of previous scene. Genshin Impact 3D anime style, bright daylight, "
    "ancient marketplace. The young man with short curly black hair, amber eyes, dark blue "
    "robe with gold belt stuffs the remaining bun into his mouth, reaches behind his back "
    "and draws a gleaming sword from the cloth wrapping. He dashes down the stone street "
    "toward the commotion, robe fluttering. The young woman with brown twin-tails, red apron "
    "watches him go, shakes her head with an amused smile, then turns back to her stall. "
    "Camera: dynamic tracking shot following the running man, then cut to medium shot of "
    "woman's reaction."
)

# B version: minimal
PROMPT_B_SEG2 = (
    "Continuation of previous scene. The man takes a big bite of the bun, eyes widen with "
    "surprise. The woman grins proudly. A loud shout from down the street. The man stops "
    "chewing, turns sharply toward the sound, expression serious. Camera: close-up face, "
    "then pan toward sound."
)

PROMPT_B_SEG3 = (
    "Continuation of previous scene. The man stuffs the bun in his mouth, draws his sword "
    "from behind his back, dashes down the street toward the commotion, robe fluttering. "
    "The woman watches him go, shakes her head smiling, turns back to her stall. Camera: "
    "tracking shot following running man, then medium shot of woman."
)

# ── TTS Lines (shared) ──────────────────────────────────

TTS_LINES = {
    "seg1": [
        ("zh-CN-XiaoxiaoNeural", "客官！尝尝我们祖传的灌汤包，保证吃了还想吃！"),
        ("zh-CN-YunxiNeural", "来两个。"),
    ],
    "seg2": [
        ("zh-CN-YunxiNeural", "嗯！这汤汁……绝了！"),
        ("zh-CN-XiaoxiaoNeural", "那当然，三代人的手艺呢！"),
        ("zh-CN-YunyangNeural", "抓住他！别让他跑了！"),
    ],
    "seg3": [
        ("zh-CN-YunxiNeural", "多谢款待，改天再来！"),
        ("zh-CN-XiaoxiaoNeural", "唉，又是一个吃了不给好评的……"),
    ],
}

def gen_tts(outdir: Path):
    """Generate all TTS audio files."""
    for seg, lines in TTS_LINES.items():
        parts = []
        for i, (voice, text) in enumerate(lines):
            out = outdir / f"{seg}-tts-{i}.wav"
            subprocess.run([
                "python3", "-u", str(TOOLS / "tts_gen.py"),
                "--text", text, "--voice", voice, "--out", str(out)
            ], check=True, timeout=60)
            parts.append(str(out))
        
        # Concat all TTS parts for this segment with small gaps
        combined = outdir / f"{seg}-tts.wav"
        if len(parts) == 1:
            os.rename(parts[0], str(combined))
        else:
            # Use ffmpeg to concat with 0.3s silence gaps
            filter_parts = []
            inputs = []
            for j, p in enumerate(parts):
                inputs.extend(["-i", p])
                filter_parts.append(f"[{j}:a]")
            
            filter_str = "".join(filter_parts) + f"concat=n={len(parts)}:v=0:a=1[out]"
            subprocess.run([
                "ffmpeg", "-y", *inputs,
                "-filter_complex", filter_str,
                "-map", "[out]", str(combined)
            ], capture_output=True, check=True, timeout=60)
        print(f"  TTS: {combined.name}", flush=True)


def mix_audio_video(video: str, tts: str, output: str):
    """Mix TTS audio onto video (keeping original video audio if any)."""
    # Replace audio entirely with TTS
    subprocess.run([
        "ffmpeg", "-y", "-i", video, "-i", tts,
        "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", output
    ], capture_output=True, check=True, timeout=120)
    print(f"  Mixed: {os.path.basename(output)}", flush=True)


def concat_final(seg_files: list, output: str):
    """Concatenate segments into final video."""
    subprocess.run([
        "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
        "--inputs", *seg_files, "--out", output, "--check-audio"
    ], check=True, timeout=120)


def run_version(version: str, keys: dict, seg1_path: str, outdir: Path, 
                prompt_seg2: str, prompt_seg3: str) -> dict:
    """Run one version (A or B) of the experiment."""
    log = {"version": version, "prompts": {}, "results": {}}
    
    # Copy seg1 to this version's output dir
    seg1_out = str(outdir / "seg1.mp4")
    if not os.path.exists(seg1_out):
        import shutil
        shutil.copy2(seg1_path, seg1_out)
    
    log["prompts"]["seg1"] = PROMPT_SEG1
    log["prompts"]["seg2"] = prompt_seg2
    log["prompts"]["seg3"] = prompt_seg3
    
    # Generate Seg2 (extend from Seg1)
    print(f"\n{'='*60}", flush=True)
    print(f"  [{version}] Generating Seg2 (extend)...", flush=True)
    print(f"  Prompt length: {len(prompt_seg2)} chars", flush=True)
    r2 = run_seedance(
        keys["seedance_script"], keys["ark_key"],
        prompt=prompt_seg2,
        video=seg1_out,
        output=str(outdir / "seg2.mp4"),
        ratio="9:16", duration=15
    )
    log["results"]["seg2"] = r2
    if not r2["ok"]:
        print(f"  ✗ [{version}] Seg2 FAILED: {r2.get('error','')[:200]}", flush=True)
        return log
    
    # Generate Seg3 (extend from Seg2)
    print(f"  [{version}] Generating Seg3 (extend)...", flush=True)
    print(f"  Prompt length: {len(prompt_seg3)} chars", flush=True)
    r3 = run_seedance(
        keys["seedance_script"], keys["ark_key"],
        prompt=prompt_seg3,
        video=str(outdir / "seg2.mp4"),
        output=str(outdir / "seg3.mp4"),
        ratio="9:16", duration=15
    )
    log["results"]["seg3"] = r3
    if not r3["ok"]:
        print(f"  ✗ [{version}] Seg3 FAILED: {r3.get('error','')[:200]}", flush=True)
        return log
    
    # TTS
    print(f"  [{version}] Generating TTS...", flush=True)
    gen_tts(outdir)
    
    # Mix audio with video for each segment
    for seg in ["seg1", "seg2", "seg3"]:
        mix_audio_video(
            str(outdir / f"{seg}.mp4"),
            str(outdir / f"{seg}-tts.wav"),
            str(outdir / f"{seg}-final.mp4")
        )
    
    # Concat final
    final = str(outdir / "final.mp4")
    concat_final(
        [str(outdir / f"seg{i}-final.mp4") for i in [1, 2, 3]],
        final
    )
    
    if os.path.exists(final):
        size_mb = os.path.getsize(final) / 1024 / 1024
        log["results"]["final"] = {"ok": True, "path": final, "size_mb": round(size_mb, 1)}
        print(f"  ✓ [{version}] Final: {final} ({size_mb:.1f}MB)", flush=True)
    else:
        log["results"]["final"] = {"ok": False, "error": "concat failed"}
    
    return log


def main():
    keys = load_keys()
    if not keys["ark_key"]:
        print("ERROR: ARK_API_KEY not found", file=sys.stderr); sys.exit(1)
    if not keys["seedance_script"]:
        print("ERROR: seedance.py not found", file=sys.stderr); sys.exit(1)
    
    gen_log = {"experiment": "V7-091", "hypothesis": "H-171", "start": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    
    # ── Step 1: Generate shared Seg1 ──
    seg1_path = str(EXPDIR / "seg1-shared.mp4")
    if os.path.exists(seg1_path) and os.path.getsize(seg1_path) > 100000:
        print(f"Seg1 already exists ({os.path.getsize(seg1_path)/1024/1024:.1f}MB), reusing.", flush=True)
    else:
        print("Generating shared Seg1 (text-to-video)...", flush=True)
        print(f"  Prompt length: {len(PROMPT_SEG1)} chars", flush=True)
        r1 = run_seedance(
            keys["seedance_script"], keys["ark_key"],
            prompt=PROMPT_SEG1,
            output=seg1_path,
            ratio="9:16", duration=15
        )
        gen_log["seg1"] = r1
        if not r1["ok"]:
            if r1.get("error") == "MODERATION_BLOCK":
                print("⛔ Seg1 moderation blocked. Abandoning experiment per standing order.", flush=True)
            else:
                print(f"✗ Seg1 failed: {r1.get('error','')[:200]}", flush=True)
            gen_log["status"] = "FAILED_SEG1"
            with open(str(EXPDIR / "generation-log.json"), "w") as f:
                json.dump(gen_log, f, indent=2, ensure_ascii=False)
            sys.exit(1)
    
    # ── Step 2: Run A and B versions (Seg2/3 can be concurrent per standing order) ──
    # A-Seg2 + B-Seg2 concurrently, then A-Seg3 + B-Seg3 concurrently
    # But since Seg3 depends on Seg2, we run A and B fully in parallel threads
    
    print("\n" + "="*60, flush=True)
    print("Running A (full repeat) and B (minimal) in parallel...", flush=True)
    
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(run_version, "A-full", keys, seg1_path, OUTDIR_A, PROMPT_A_SEG2, PROMPT_A_SEG3)
        fut_b = pool.submit(run_version, "B-minimal", keys, seg1_path, OUTDIR_B, PROMPT_B_SEG2, PROMPT_B_SEG3)
        
        log_a = fut_a.result()
        log_b = fut_b.result()
    
    gen_log["version_a"] = log_a
    gen_log["version_b"] = log_b
    gen_log["end"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    gen_log["status"] = "COMPLETE"
    
    # Prompt length comparison
    gen_log["prompt_lengths"] = {
        "seg1": len(PROMPT_SEG1),
        "a_seg2": len(PROMPT_A_SEG2), "a_seg3": len(PROMPT_A_SEG3),
        "b_seg2": len(PROMPT_B_SEG2), "b_seg3": len(PROMPT_B_SEG3),
    }
    
    with open(str(EXPDIR / "generation-log.json"), "w") as f:
        json.dump(gen_log, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}", flush=True)
    print("V7-091 COMPLETE", flush=True)
    print(f"  A final: {OUTDIR_A / 'final.mp4'}", flush=True)
    print(f"  B final: {OUTDIR_B / 'final.mp4'}", flush=True)
    print(f"  Log: {EXPDIR / 'generation-log.json'}", flush=True)


if __name__ == "__main__":
    main()
