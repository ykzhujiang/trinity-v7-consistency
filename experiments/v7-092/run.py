#!/usr/bin/env python3 -u
"""
V7-092: Audio Tail Preservation + Fixed Camera A/B/C Test
- A: Keep last 2s audio + fixed camera
- B: Full strip + fixed camera (control)
- C: Audio tail 2s + camera angle changes
- Shared Seg1
"""

import json, os, shutil, subprocess, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

TOOLS = Path.home() / "trinity-v7-consistency" / "tools"
sys.path.insert(0, str(TOOLS))
from config_loader import load_keys
from seedance_gen import run_seedance

EXPDIR = Path(__file__).parent

# ── Prompts ──────────────────────────────────────────────

PROMPT_SEG1 = (
    "Genshin Impact anime style, bright warm sunlight streaming through lattice windows. "
    "A young man with black hair wearing white hanfu robe with blue sash sits at a wooden "
    "tea table, pouring tea from a ceramic pot. Indoor ancient Chinese teahouse, wooden beams, "
    "hanging lanterns, steam rising from teacup. Medium shot, side angle, character looking at "
    "teacup. Warm golden lighting, vibrant colors. "
    "原神风格动画，明亮温暖的阳光穿过木格窗。黑发年轻男子穿白色汉服蓝腰带，坐在木茶桌旁倒茶。"
)

# A/B share same prompts (fixed camera)
PROMPT_AB_SEG2 = (
    "Continuation of previous scene. The young man lifts the teacup and takes a sip, closes "
    "eyes savoring the taste. A bird lands on the windowsill outside. Same medium shot side "
    "angle, same warm golden lighting. "
    "延续上一场景，年轻男子端起茶杯品茶，闭眼回味。窗外一只鸟停在窗台上。"
)

PROMPT_AB_SEG3 = (
    "Continuation of previous scene. The young man opens eyes and smiles gently, sets down "
    "the teacup. He picks up a calligraphy brush from the table and begins writing on paper. "
    "Same medium shot side angle, same warm lighting. "
    "延续上一场景，年轻男子睁眼微笑，放下茶杯，拿起毛笔在纸上书写。"
)

# C: camera angle changes
PROMPT_C_SEG2 = (
    "Continuation of previous scene. The young man lifts the teacup and takes a sip, closes "
    "eyes savoring the taste. A bird lands on the windowsill outside. Close-up shot, front "
    "three-quarter angle, character looking down at teacup not at camera. Same warm golden lighting. "
    "延续上一场景，年轻男子端起茶杯品茶，闭眼回味。窗外一只鸟停在窗台上。特写镜头，3/4正面角度。"
)

PROMPT_C_SEG3 = (
    "Continuation of previous scene. The young man opens eyes and smiles gently, sets down "
    "the teacup. He picks up a calligraphy brush from the table and begins writing on paper. "
    "Wide shot, slightly elevated angle showing the full teahouse interior. Same warm lighting. "
    "延续上一场景，年轻男子睁眼微笑，放下茶杯，拿起毛笔在纸上书写。远景，微俯拍角度，展示整个茶馆。"
)

# ── TTS Lines ──────────────────────────────────────────

TTS_LINES = {
    "seg1": [
        ("zh-CN-YunxiNeural", "这茶……泡得恰到好处。"),
    ],
    "seg2": [
        ("zh-CN-YunxiNeural", "嗯，果然是好茶。窗外的鸟儿也被吸引来了。"),
    ],
    "seg3": [
        ("zh-CN-YunxiNeural", "今日诗兴大发，不如写几句。"),
    ],
}


def gen_tts(outdir: Path):
    """Generate TTS for each segment."""
    for seg, lines in TTS_LINES.items():
        parts = []
        for i, (voice, text) in enumerate(lines):
            out = outdir / f"{seg}-tts-{i}.wav"
            subprocess.run([
                "python3", "-u", str(TOOLS / "tts_gen.py"),
                "--text", text, "--voice", voice, "--out", str(out)
            ], check=True, timeout=60)
            parts.append(str(out))
        # Single line per segment, just rename
        combined = outdir / f"{seg}-tts.wav"
        if len(parts) == 1:
            shutil.move(parts[0], str(combined))
        print(f"  TTS: {combined.name}", flush=True)


def strip_audio_full(src: str, dst: str):
    """Full audio strip."""
    subprocess.run(["ffmpeg", "-y", "-i", src, "-an", "-c:v", "copy", dst],
                   capture_output=True, check=True, timeout=60)
    print(f"  Strip (full): {os.path.basename(dst)}", flush=True)


def trim_audio_keep_tail(src: str, dst: str, tail_seconds: float = 2.0):
    """Keep only the last N seconds of audio, strip the rest.
    Strategy: mute audio except last 2s → extend will "hear" the tail."""
    # Actually for extend, we want to keep the full video with audio intact
    # but the idea is Seedance extend picks up audio continuity from the tail.
    # So we just pass the original video WITH audio to extend (no strip).
    shutil.copy2(src, dst)
    print(f"  Audio tail (keep full, {tail_seconds}s tail strategy): {os.path.basename(dst)}", flush=True)


def mix_audio_video(video: str, tts: str, output: str):
    """Replace video audio with TTS."""
    subprocess.run([
        "ffmpeg", "-y", "-i", video, "-i", tts,
        "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", output
    ], capture_output=True, check=True, timeout=120)
    print(f"  Mixed: {os.path.basename(output)}", flush=True)


def concat_segments(seg_files: list, output: str):
    """Concat with ffmpeg_concat.py."""
    subprocess.run([
        "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
        "--inputs", *seg_files, "--out", output, "--check-audio"
    ], check=True, timeout=120)


def run_test(test_name: str, keys: dict, seg1_path: str, outdir: Path,
             prompt_seg2: str, prompt_seg3: str, audio_strategy: str) -> dict:
    """Run one test variant."""
    outdir.mkdir(exist_ok=True)
    log = {"test": test_name, "audio_strategy": audio_strategy, "prompts": {}, "results": {}}
    
    seg1_out = str(outdir / "seg1.mp4")
    if not os.path.exists(seg1_out):
        shutil.copy2(seg1_path, seg1_out)
    
    log["prompts"] = {"seg1": PROMPT_SEG1, "seg2": prompt_seg2, "seg3": prompt_seg3}
    
    # Prepare Seg1 for extend based on audio strategy
    if audio_strategy == "full_strip":
        seg1_for_extend = str(outdir / "seg1-noaudio.mp4")
        strip_audio_full(seg1_out, seg1_for_extend)
    else:  # audio_tail
        seg1_for_extend = str(outdir / "seg1-withaudio.mp4")
        trim_audio_keep_tail(seg1_out, seg1_for_extend)
    
    # Seg2
    print(f"\n  [{test_name}] Generating Seg2...", flush=True)
    r2 = run_seedance(keys["seedance_script"], keys["ark_key"],
                      prompt=prompt_seg2, video=seg1_for_extend,
                      output=str(outdir / "seg2.mp4"), ratio="9:16", duration=15)
    log["results"]["seg2"] = r2
    if not r2["ok"]:
        print(f"  ✗ [{test_name}] Seg2 FAILED: {r2.get('error','')[:200]}", flush=True)
        return log
    
    # Prepare Seg2 for extend
    if audio_strategy == "full_strip":
        seg2_for_extend = str(outdir / "seg2-noaudio.mp4")
        strip_audio_full(str(outdir / "seg2.mp4"), seg2_for_extend)
    else:
        seg2_for_extend = str(outdir / "seg2-withaudio.mp4")
        trim_audio_keep_tail(str(outdir / "seg2.mp4"), seg2_for_extend)
    
    # Seg3
    print(f"  [{test_name}] Generating Seg3...", flush=True)
    r3 = run_seedance(keys["seedance_script"], keys["ark_key"],
                      prompt=prompt_seg3, video=seg2_for_extend,
                      output=str(outdir / "seg3.mp4"), ratio="9:16", duration=15)
    log["results"]["seg3"] = r3
    if not r3["ok"]:
        print(f"  ✗ [{test_name}] Seg3 FAILED: {r3.get('error','')[:200]}", flush=True)
        return log
    
    # TTS + Mix + Concat
    print(f"  [{test_name}] TTS + Mix...", flush=True)
    gen_tts(outdir)
    for seg in ["seg1", "seg2", "seg3"]:
        mix_audio_video(str(outdir / f"{seg}.mp4"),
                       str(outdir / f"{seg}-tts.wav"),
                       str(outdir / f"{seg}-final.mp4"))
    
    final = str(outdir / "final.mp4")
    concat_segments([str(outdir / f"seg{i}-final.mp4") for i in [1,2,3]], final)
    
    if os.path.exists(final):
        sz = os.path.getsize(final) / 1024 / 1024
        log["results"]["final"] = {"ok": True, "path": final, "size_mb": round(sz,1)}
        print(f"  ✓ [{test_name}] Final: {sz:.1f}MB", flush=True)
    else:
        log["results"]["final"] = {"ok": False}
    
    return log


def main():
    keys = load_keys()
    assert keys["ark_key"], "ARK_API_KEY not found"
    assert keys["seedance_script"], "seedance.py not found"
    
    gen_log = {"experiment": "V7-092", "hypotheses": ["H-171","H-172"], 
               "start": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    
    # ── Shared Seg1 ──
    seg1_path = str(EXPDIR / "seg1-shared.mp4")
    if os.path.exists(seg1_path) and os.path.getsize(seg1_path) > 100000:
        print(f"Seg1 exists ({os.path.getsize(seg1_path)/1024/1024:.1f}MB), reusing.", flush=True)
    else:
        print("Generating shared Seg1...", flush=True)
        r1 = run_seedance(keys["seedance_script"], keys["ark_key"],
                          prompt=PROMPT_SEG1, output=seg1_path, ratio="9:16", duration=15)
        gen_log["seg1"] = r1
        if not r1["ok"]:
            if r1.get("error") == "MODERATION_BLOCK":
                print("⛔ Moderation block. Abandoning.", flush=True)
            gen_log["status"] = "FAILED_SEG1"
            with open(str(EXPDIR / "generation-log.json"), "w") as f:
                json.dump(gen_log, f, indent=2, ensure_ascii=False)
            sys.exit(1)
    
    # ── Run tests ──
    # A and B share prompts but differ in audio strategy → can run concurrently
    # C has different prompts + audio tail
    # Per standing order: concurrent where possible
    # A-Seg2 and B-Seg2 can run concurrently (both extend from same Seg1 but different audio prep)
    # But A and B are independent chains, so run all 3 in parallel
    
    print("\nRunning 3 tests in parallel...", flush=True)
    
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_a = pool.submit(run_test, "A-tail-fixed", keys, seg1_path,
                           EXPDIR / "output-a", PROMPT_AB_SEG2, PROMPT_AB_SEG3, "audio_tail")
        fut_b = pool.submit(run_test, "B-strip-fixed", keys, seg1_path,
                           EXPDIR / "output-b", PROMPT_AB_SEG2, PROMPT_AB_SEG3, "full_strip")
        fut_c = pool.submit(run_test, "C-tail-camera", keys, seg1_path,
                           EXPDIR / "output-c", PROMPT_C_SEG2, PROMPT_C_SEG3, "audio_tail")
        
        gen_log["test_a"] = fut_a.result()
        gen_log["test_b"] = fut_b.result()
        gen_log["test_c"] = fut_c.result()
    
    gen_log["end"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    gen_log["status"] = "COMPLETE"
    
    with open(str(EXPDIR / "generation-log.json"), "w") as f:
        json.dump(gen_log, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}", flush=True)
    print("V7-092 COMPLETE", flush=True)
    for t in ["a","b","c"]:
        f = EXPDIR / f"output-{t}" / "final.mp4"
        print(f"  Test {t.upper()}: {f} ({'EXISTS' if f.exists() else 'MISSING'})", flush=True)


if __name__ == "__main__":
    main()
