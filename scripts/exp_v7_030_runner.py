#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "requests>=2.28.0", "pillow>=10.0.0"]
# ///
"""
EXP-V7-030 Runner: Photorealistic Fix + Audio-Visual Sync Verification

Dual-track: anime + realistic
Key hypothesis:
  H-368: Explicit negative prompts + photo-level ref images → eliminate 3D/Pixar drift
  H-369: Audio-visual strict sync → higher immersion

Scene: Startup founder meets investor in coffee shop (modern urban China)
Characters:
  李然 (Lǐ Rán) — 28yo Chinese male programmer/startup founder
  赵总 (Zhào zǒng) — 45yo Chinese female investor, sharp short hair, suit
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJ = Path.home() / "trinity-v7-consistency"
EXP = PROJ / "experiments" / "exp-v7-030"
ASSETS = EXP / "assets"
OUTPUT = EXP / "output"
TOOLS = PROJ / "tools"

os.makedirs(ASSETS, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)
os.chdir(PROJ)

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

KEYS = load_keys()

# ── Character / Scene Descriptions ──────────────────────────────────

# ANIME versions (digital painting style, safe for Seedance)
ANIME_MAN_DESC = (
    "Digital painting portrait of a 28-year-old Chinese man with short messy black hair, "
    "rectangular glasses, slightly tired but bright eyes, wearing a dark grey hoodie over a plain white t-shirt. "
    "Slim build, focused expression. 3D rendered illustration style, soft studio lighting, clean background. "
    "NOT a photograph. Anime-inspired semi-realistic digital art."
)
ANIME_WOMAN_DESC = (
    "Digital painting portrait of a 45-year-old Chinese woman with sharp short black bob haircut, "
    "confident expression, wearing a tailored navy blue blazer over white silk blouse. "
    "Lean face, high cheekbones, small silver stud earrings. "
    "3D rendered illustration style, soft studio lighting, clean background. "
    "NOT a photograph. Anime-inspired semi-realistic digital art."
)
ANIME_CAFE_DESC = (
    "Digital painting of a modern minimalist coffee shop interior. Large window with afternoon sunlight. "
    "A corner table with a laptop, coffee cups. Industrial-chic decor: exposed brick, pendant lights. "
    "Warm golden light. Illustrated environment concept art style."
)

# REALISTIC versions (photo-level, DSLR-quality)
REAL_MAN_DESC = (
    "Professional DSLR photograph of a 28-year-old Chinese East Asian man with short messy black hair, "
    "rectangular glasses, wearing a dark grey hoodie over a plain white t-shirt. "
    "Natural indoor lighting, shallow depth of field, shot on Canon EOS R5, 85mm lens. "
    "Real person, NOT illustration, NOT 3D render, NOT anime. Photojournalistic portrait style."
)
REAL_WOMAN_DESC = (
    "Professional DSLR photograph of a 45-year-old Chinese East Asian woman with sharp short black bob haircut, "
    "wearing a tailored navy blue blazer over white silk blouse. "
    "Confident expression, small silver stud earrings. "
    "Natural indoor lighting, shallow depth of field, shot on Canon EOS R5, 85mm lens. "
    "Real person, NOT illustration, NOT 3D render, NOT anime. Photojournalistic portrait style."
)
REAL_CAFE_DESC = (
    "Professional photograph of a modern minimalist coffee shop interior. Large window with afternoon sunlight. "
    "Corner table with laptop and coffee cups. Industrial-chic decor: exposed brick, pendant lights. "
    "Shot on wide-angle lens, natural warm lighting. Real photograph, NOT illustration, NOT 3D."
)

# ── Character text for Seedance prompts ─────────────────────────────
CHAR_TEXT_ANIME = (
    "A 28-year-old Chinese East Asian man with short messy black hair, rectangular glasses, "
    "wearing a dark grey hoodie over a white t-shirt. "
    "A 45-year-old Chinese East Asian woman with sharp short black bob haircut, "
    "wearing a tailored navy blue blazer over white silk blouse, small silver earrings."
)

CHAR_TEXT_REAL = (
    "A 28-year-old Chinese East Asian man with short messy black hair, rectangular glasses, "
    "wearing a dark grey hoodie over a white t-shirt. "
    "A 45-year-old Chinese East Asian woman with sharp short black bob haircut, "
    "wearing a tailored navy blue blazer over white silk blouse, small silver earrings. "
    "Photorealistic, real human, live-action cinematography, "
    "NOT anime, NOT 3D rendering, NOT cartoon, NOT Pixar style."
)

# ── Seedance Prompts ────────────────────────────────────────────────

def make_seg1_prompt(char_text):
    return (
        f"A modern minimalist coffee shop, afternoon sunlight through large window, corner table with laptop. "
        f"{char_text} "
        f"The man (Li Ran) sits at the corner table typing on his laptop, a half-empty coffee beside him. "
        f"The woman (Zhao) walks in from the right, sharp heels clicking on wooden floor, scanning the room. "
        f"She spots Li Ran, walks towards him with purposeful steps. "
        f"Li Ran notices movement, looks up from laptop, slightly startled. "
        f"Zhao stops at his table, tilts her head slightly, lips curl into a half-smile. "
        f"She pulls out the chair opposite him, sits down in one smooth motion, places her leather portfolio on the table. "
        f"Li Ran closes laptop halfway, pushes glasses up his nose nervously. "
        f"Zhao leans forward, elbows on table, fingers interlaced, studying him with sharp eyes. "
        f"Normal speed movement, natural pacing. No slow motion. No facing camera directly. No subtitles. "
        f"Vertical 9:16 framing. Medium shot, camera slightly right 10 degrees. Both characters in frame. "
        f"Sound: keyboard typing, heels on wood floor, chair scraping, ambient cafe chatter."
    )

def make_seg2_prompt(char_text):
    return (
        f"Continuing in the same modern coffee shop. {char_text} "
        f"They are seated at the corner table, the woman (Zhao) leaning forward attentively. "
        f"Li Ran opens his laptop fully, turns it to show her the screen, pointing at it with his right hand. "
        f"Zhao's eyes widen, she leans closer to the screen, eyebrows rising. "
        f"She nods slowly, a genuine smile forming, tapping her index finger on the table thoughtfully. "
        f"Li Ran watches her reaction, his nervous posture gradually relaxing, sitting up straighter. "
        f"Zhao reaches into her blazer pocket, pulls out a business card, slides it across the table towards him. "
        f"Li Ran picks up the card, reads it, looks up at her with surprised delight. "
        f"Zhao stands up, extends her right hand for a handshake. Li Ran stands, shakes her hand firmly. "
        f"Normal speed movement, natural pacing. No slow motion. No facing camera directly. No subtitles. "
        f"Same camera angle as previous segment. Medium shot, slightly right 10 degrees. "
        f"Sound: laptop hinge opening, finger tapping on table, card sliding on wood, chair pushing back."
    )


def gen_ref_images(style, descs, prefix):
    """Generate reference images via Gemini."""
    specs = [
        {"name": f"{prefix}-man", "type": "character", "style": style, "desc": descs["man"]},
        {"name": f"{prefix}-woman", "type": "character", "style": style, "desc": descs["woman"]},
        {"name": f"{prefix}-cafe", "type": "scene", "style": style, "desc": descs["cafe"]},
    ]
    specs_path = EXP / f"asset-specs-{prefix}.json"
    with open(specs_path, "w") as f:
        json.dump(specs, f, indent=2, ensure_ascii=False)

    cmd = [
        "python3", "-u", str(TOOLS / "gemini_chargen.py"),
        "--specs", str(specs_path),
        "--out-dir", str(ASSETS),
    ]
    print(f"=== Generating {prefix} reference images ===", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                       env={**os.environ, "PYTHONUNBUFFERED": "1"})
    print(r.stdout, flush=True)
    if r.stderr:
        print(r.stderr, file=sys.stderr, flush=True)

    expected = [
        ASSETS / f"char-{prefix}-man.webp",
        ASSETS / f"char-{prefix}-woman.webp",
        ASSETS / f"scene-{prefix}-cafe.webp",
    ]
    found = []
    for p in expected:
        if p.exists():
            print(f"  ✓ {p.name} ({p.stat().st_size // 1024}KB)", flush=True)
            found.append(str(p))
        else:
            print(f"  ✗ MISSING {p.name}", flush=True)
    return found


def run_seedance(prompt, images=None, video=None, output="output.mp4"):
    """Run seedance_gen.py for one video."""
    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--prompt", prompt,
        "--ratio", "9:16",
        "--duration", "15",
        "--out", output,
    ]
    if video:
        cmd.extend(["--video", video])
    for img in (images or []):
        cmd.extend(["--image", img])

    print(f"  Seedance → {os.path.basename(output)}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800,
                       env={**os.environ, "PYTHONUNBUFFERED": "1"})
    elapsed = time.time() - t0
    print(r.stdout, flush=True)
    ok = r.returncode == 0 and os.path.isfile(output)
    err = r.stderr if not ok else ""
    if err:
        print(f"  ✗ Error: {err[:500]}", file=sys.stderr, flush=True)
    return {"ok": ok, "path": output, "elapsed": elapsed, "error": err[:1000]}


def check_audio(path):
    """Check if video has audio track via ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=30
        )
        has_audio = "audio" in r.stdout
        print(f"  Audio check {os.path.basename(path)}: {'✓' if has_audio else '✗ NO AUDIO'}", flush=True)
        return has_audio
    except Exception as e:
        print(f"  Audio check error: {e}", flush=True)
        return False


def concat_segments(seg1, seg2, output):
    """Concatenate two segments."""
    cmd = [
        "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
        "--inputs", seg1, seg2,
        "--out", output,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                       env={**os.environ, "PYTHONUNBUFFERED": "1"})
    print(r.stdout, flush=True)
    return os.path.isfile(output)


def main():
    gen_log = {
        "experiment": "EXP-V7-030",
        "hypothesis": ["H-368: negative prompts + photo-level refs → no 3D drift",
                       "H-369: audio-visual sync → higher immersion"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tracks": {},
    }

    # ── Step 1: Generate reference images for both tracks concurrently ──
    print("\n=== Step 1: Generate reference images (anime + realistic) ===", flush=True)
    anime_imgs = []
    real_imgs = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_anime = ex.submit(gen_ref_images, "anime", {
            "man": ANIME_MAN_DESC, "woman": ANIME_WOMAN_DESC, "cafe": ANIME_CAFE_DESC
        }, "anime")
        f_real = ex.submit(gen_ref_images, "realistic", {
            "man": REAL_MAN_DESC, "woman": REAL_WOMAN_DESC, "cafe": REAL_CAFE_DESC
        }, "real")
        anime_imgs = f_anime.result()
        real_imgs = f_real.result()

    gen_log["assets"] = {"anime": anime_imgs, "realistic": real_imgs}

    # ── Step 2: Generate Seg1 for both tracks concurrently ──
    print("\n=== Step 2: Generating Seg1 (anime + realistic concurrent) ===", flush=True)
    anime_seg1_prompt = make_seg1_prompt(CHAR_TEXT_ANIME)
    real_seg1_prompt = make_seg1_prompt(CHAR_TEXT_REAL)

    anime_seg1_path = str(OUTPUT / "anime-seg1.mp4")
    real_seg1_path = str(OUTPUT / "real-seg1.mp4")

    seg1_results = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {
            ex.submit(run_seedance, anime_seg1_prompt, anime_imgs, None, anime_seg1_path): "anime",
            ex.submit(run_seedance, real_seg1_prompt, real_imgs, None, real_seg1_path): "realistic",
        }
        for fut in as_completed(futures):
            track = futures[fut]
            seg1_results[track] = fut.result()
            gen_log["tracks"].setdefault(track, {})["seg1"] = {
                "prompt": (anime_seg1_prompt if track == "anime" else real_seg1_prompt)[:300] + "...",
                "images": anime_imgs if track == "anime" else real_imgs,
                "result": seg1_results[track],
            }

    # Check for content moderation blocks
    for track, res in seg1_results.items():
        err = res.get("error", "")
        if "ContentModerationError" in err or "PrivacyInformation" in err or "内容审核" in err:
            print(f"\n⚠️  CONTENT MODERATION BLOCK on {track} Seg1! Abandoning this track.", flush=True)
            gen_log["tracks"][track]["abandoned"] = True

    # ── Step 3: Generate Seg2 via video extension (concurrent for both tracks) ──
    print("\n=== Step 3: Generating Seg2 via video extension ===", flush=True)
    anime_seg2_prompt = make_seg2_prompt(CHAR_TEXT_ANIME)
    real_seg2_prompt = make_seg2_prompt(CHAR_TEXT_REAL)

    anime_seg2_path = str(OUTPUT / "anime-seg2.mp4")
    real_seg2_path = str(OUTPUT / "real-seg2.mp4")

    seg2_results = {}
    seg2_tasks = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        if seg1_results.get("anime", {}).get("ok") and not gen_log["tracks"].get("anime", {}).get("abandoned"):
            seg2_tasks[ex.submit(run_seedance, anime_seg2_prompt, anime_imgs, anime_seg1_path, anime_seg2_path)] = "anime"
        else:
            print("  ✗ Skipping anime Seg2 (Seg1 failed or abandoned)", flush=True)

        if seg1_results.get("realistic", {}).get("ok") and not gen_log["tracks"].get("realistic", {}).get("abandoned"):
            seg2_tasks[ex.submit(run_seedance, real_seg2_prompt, real_imgs, real_seg1_path, real_seg2_path)] = "realistic"
        else:
            print("  ✗ Skipping realistic Seg2 (Seg1 failed or abandoned)", flush=True)

        for fut in as_completed(seg2_tasks):
            track = seg2_tasks[fut]
            seg2_results[track] = fut.result()
            gen_log["tracks"][track]["seg2"] = {
                "prompt": (anime_seg2_prompt if track == "anime" else real_seg2_prompt)[:300] + "...",
                "result": seg2_results[track],
            }

    # ── Step 4: Concatenate ──
    print("\n=== Step 4: Concatenation ===", flush=True)
    finals = {}
    for track, seg1_p, seg2_p in [
        ("anime", anime_seg1_path, anime_seg2_path),
        ("realistic", real_seg1_path, real_seg2_path),
    ]:
        final = str(OUTPUT / f"{track}-final.mp4")
        if os.path.isfile(seg1_p) and os.path.isfile(seg2_p):
            ok = concat_segments(seg1_p, seg2_p, final)
            finals[track] = final if ok else None
            print(f"  {track} concat: {'✓' if ok else '✗'}", flush=True)
        else:
            print(f"  {track} concat: SKIP (missing segments)", flush=True)

    # ── Step 5: Audio check on ALL segments ──
    print("\n=== Step 5: Audio Check ===", flush=True)
    audio_results = {}
    for f in sorted(Path(OUTPUT).glob("*.mp4")):
        audio_results[f.name] = check_audio(str(f))
    gen_log["audio_check"] = audio_results

    # Flag any segment without audio
    audio_failures = [k for k, v in audio_results.items() if not v]
    if audio_failures:
        print(f"\n⚠️  AUDIO FAILURES: {audio_failures}", flush=True)
        print("  These videos are NOT deliverable per standing orders.", flush=True)
        gen_log["audio_failures"] = audio_failures

    # Save generation log
    gen_log["finals"] = finals
    log_path = OUTPUT / "generation-log.json"
    with open(log_path, "w") as f:
        json.dump(gen_log, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Generation log saved: {log_path}", flush=True)

    # ── Summary ──
    print("\n=== Summary ===", flush=True)
    for track in ["anime", "realistic"]:
        s1_ok = seg1_results.get(track, {}).get("ok", False)
        s2_ok = seg2_results.get(track, {}).get("ok", False)
        final_ok = track in finals and finals[track]
        abandoned = gen_log["tracks"].get(track, {}).get("abandoned", False)
        status = "ABANDONED" if abandoned else ("✓" if final_ok else "✗")
        print(f"  {track}: Seg1={'✓' if s1_ok else '✗'} Seg2={'✓' if s2_ok else '✗'} Final={status}", flush=True)


if __name__ == "__main__":
    main()
