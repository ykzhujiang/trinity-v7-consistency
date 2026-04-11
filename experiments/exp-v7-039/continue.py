#!/usr/bin/env python3 -u
"""EXP-V7-039 continuation — step by step with proper timeouts."""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
EXP = Path(__file__).resolve().parent
OUT = EXP / "output"
ASSETS = EXP / "assets"

CHAR_EN = "28-year-old Chinese male programmer Lin Hao, slim and tall, short black hair, black-framed glasses, wearing grey hoodie and jeans"
SCENE1_EN = "late-night internet cafe, dim lighting, rows of computer desks, blue screen glow"
SCENE2_EN = "city rooftop, daytime, bright sunlight, overlooking urban buildings, iron railing"
SCENE3_EN = "small shabby rental room, nighttime, dim desk lamp, old wooden desk, single bed, peeling walls"

def gen_batch(batch_items, label, timeout=1200):
    batch_f = EXP / f"{label}-batch.json"
    batch_f.write_text(json.dumps(batch_items, ensure_ascii=False, indent=2))
    print(f"\n[{label}] Running {len(batch_items)} items...", flush=True)
    r = subprocess.run(
        ["python3", "-u", str(TOOLS/"seedance_gen.py"), "--batch", str(batch_f), "--out-dir", str(OUT)],
        capture_output=True, text=True, timeout=timeout)
    print(r.stdout[-600:] if r.stdout else "", flush=True)
    if r.returncode != 0:
        print(f"STDERR: {r.stderr[-300:]}", flush=True)
    return r.returncode == 0

# ── Anime Seg1 (if missing) ──
if not (OUT/"anime-seg1.mp4").exists():
    gen_batch([{
        "id": "anime-seg1",
        "prompt": (f"A {CHAR_EN}, sitting at a computer desk in a {SCENE1_EN}. "
                   "He stares at the screen typing code. His phone buzzes. He picks it up and answers. "
                   "His expression shifts from focused to shocked. He slowly puts the phone down, stares blankly. "
                   "He takes a deep breath, shuts down the computer, stands up and walks toward the exit. "
                   "Camera: side medium shot to medium close-up on phone call to pull back as he stands. "
                   "Japanese anime digital animation style. Normal speed, natural pacing. "
                   "No subtitles, no slow motion, no facing camera directly. 9:16 vertical."),
        "images": [str(ASSETS/"char-linhao-anime.webp"), str(ASSETS/"scene-wangba-anime.webp")],
        "out": "anime-seg1.mp4"
    }], "anime-seg1-retry")
else:
    print("anime-seg1.mp4 exists, skipping", flush=True)

# ── Seg2 (video extension from seg1) ──
seg2_items = []
for style, suffix, char, scene in [
    ("anime", "Japanese anime digital animation style.", "char-linhao-anime.webp", "scene-rooftop-anime.webp"),
    ("real", "DSLR photograph, 35mm lens, bright natural daylight. No 3D, no CG, no Pixar.", "char-linhao-real.webp", "scene-rooftop-real.webp"),
]:
    seg1 = OUT / f"{style}-seg1.mp4"
    if seg1.exists() and not (OUT/f"{style}-seg2.mp4").exists():
        seg2_items.append({
            "id": f"{style}-seg2",
            "prompt": (f"Continuing from previous scene: The same {CHAR_EN} stands on a {SCENE2_EN}. "
                       "Wind blows through his hoodie. He grips the iron railing, looking out at the city. "
                       "He mutters to himself with frustration. He pulls out phone, glances at screen. "
                       "He shoves it back in pocket, lifts head, slight determined smile forms. "
                       f"Camera: behind medium shot to side close-up to front medium shot. {suffix} "
                       "Normal speed, natural pacing. No subtitles, no slow motion, no facing camera directly. 9:16 vertical."),
            "images": [str(ASSETS/char), str(ASSETS/scene)],
            "video": str(seg1),
            "out": f"{style}-seg2.mp4"
        })
if seg2_items:
    gen_batch(seg2_items, "seg2", timeout=1500)

# ── Seg3 (video extension from seg2) ──
seg3_items = []
for style, suffix, char, scene in [
    ("anime", "Japanese anime digital animation style.", "char-linhao-anime.webp", "scene-rental-anime.webp"),
    ("real", "DSLR photograph, 35mm lens, dim warm desk lamp. No 3D, no CG, no Pixar.", "char-linhao-real.webp", "scene-rental-real.webp"),
]:
    seg2 = OUT / f"{style}-seg2.mp4"
    if seg2.exists() and not (OUT/f"{style}-seg3.mp4").exists():
        seg3_items.append({
            "id": f"{style}-seg3",
            "prompt": (f"Continuing from previous scene: The same {CHAR_EN} pushes open door of a {SCENE3_EN}. "
                       "He drops backpack on bed, sits at old wooden desk. Opens laptop, screen light on tired face. "
                       "He starts typing, brow furrowed. Rubs eyes but keeps coding, faint smile forming. "
                       f"Camera: doorway medium shot to over-shoulder on laptop to side close-up face. {suffix} "
                       "Normal speed, natural pacing. No subtitles, no slow motion, no facing camera directly. 9:16 vertical."),
            "images": [str(ASSETS/char), str(ASSETS/scene)],
            "video": str(seg2),
            "out": f"{style}-seg3.mp4"
        })
if seg3_items:
    gen_batch(seg3_items, "seg3", timeout=1500)

# ── Concat ──
print("\n[CONCAT]", flush=True)
for style in ["anime", "real"]:
    segs = [OUT/f"{style}-seg{i}.mp4" for i in [1,2,3] if (OUT/f"{style}-seg{i}.mp4").exists()]
    if len(segs) >= 2:
        final = OUT / f"{style}-final-{len(segs)*15}s.mp4"
        r = subprocess.run(
            ["python3", "-u", str(TOOLS/"ffmpeg_concat.py"), "--inputs"] + [str(s) for s in segs] +
            ["--out", str(final), "--check-audio", "--check-per-segment"],
            capture_output=True, text=True, timeout=120)
        print(r.stdout[-300:] if r.stdout else "", flush=True)
        if final.exists():
            print(f"  ✓ {final.name} ({final.stat().st_size//1024}KB)", flush=True)
    else:
        print(f"  {style}: only {len(segs)} segs, skip concat", flush=True)

print("\n[DONE] Output files:", flush=True)
for f in sorted(OUT.iterdir()):
    if f.is_file():
        print(f"  {f.name} — {f.stat().st_size//1024}KB", flush=True)
