#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "requests>=2.28.0", "pillow>=10.0.0"]
# ///
"""
EXP-V7-031 Runner: 都市逆袭 — Illustration-Anchored Dual-Segment Consistency

Dual-track: anime + realistic
Hypothesis: H-120 — Illustration-style refs + Physical State Anchoring → cross-segment consistency

Scene: Young entrepreneur pitches to investors, PPT crashes, shows phone data → investors scramble
Characters:
  李远 (Lǐ Yuǎn) — 25yo Chinese male, startup founder
  王总 (Wáng zǒng) — 50yo Chinese male, lead investor
  投资人B — 40yo Chinese female, co-investor
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJ = Path.home() / "trinity-v7-consistency"
EXP = PROJ / "experiments" / "exp-v7-031"
ASSETS = EXP / "assets"
OUTPUT = EXP / "output"
TOOLS = PROJ / "tools"

os.makedirs(ASSETS, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)
os.chdir(PROJ)

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

KEYS = load_keys()

# ── Character text for Seedance prompts ─────────────────────────────

CHAR_TEXT_ANIME = (
    "A 25-year-old Chinese East Asian man (Li Yuan) with short slightly curly black hair, thick eyebrows, "
    "wearing a dark grey minimalist hoodie and black casual pants. "
    "A 50-year-old Chinese East Asian man (Wang) with salt-and-pepper grey hair combed back, round face, "
    "gold-rimmed glasses, wearing a dark navy suit. "
    "A 40-year-old Chinese East Asian woman (Investor B) with shoulder-length straight black hair, "
    "wearing a grey professional blazer."
)

CHAR_TEXT_REAL = (
    "A 25-year-old Chinese East Asian man (Li Yuan) with short slightly curly black hair, thick eyebrows, "
    "wearing a dark grey minimalist hoodie and black casual pants. "
    "A 50-year-old Chinese East Asian man (Wang) with salt-and-pepper grey hair combed back, round face, "
    "gold-rimmed glasses, wearing a dark navy suit. "
    "A 40-year-old Chinese East Asian woman (Investor B) with shoulder-length straight black hair, "
    "wearing a grey professional blazer. "
    "Photorealistic, real humans, live-action cinematography, "
    "NOT anime, NOT 3D rendering, NOT cartoon, NOT Pixar style."
)

# ── Seedance Prompts ────────────────────────────────────────────────

def make_seg1_prompt(char_text):
    return (
        f"High-end investor meeting room in a modern skyscraper, floor-to-ceiling windows showing city skyline. "
        f"Long conference table with leather chairs. {char_text} "
        f"Li Yuan stands at one end of the table next to a projector screen, giving a presentation. "
        f"Wang sits at the head of the table leaning back with arms crossed, skeptical expression. "
        f"Investor B sits beside Wang, pen in hand tapping the table, stern face. "
        f"Suddenly the projector screen flashes to a blue crash screen (BSOD). "
        f"Wang smirks, Investor B raises an eyebrow. Other side of table, a few more investors chuckle. "
        f"Li Yuan stays completely calm, does not flinch. He reaches into his hoodie pocket, "
        f"pulls out his phone, and holds it up with one hand towards them. "
        f"On the phone screen a line chart curves sharply upward. "
        f"Li Yuan says with a relaxed smile: 'No worries, my product doesn't need a PPT.' "
        f"Wang's smirk freezes. Investor B leans forward slightly, eyes narrowing at the phone. "
        f"All dialogue must finish before second 14. Leave at least 1 second of silence at end. "
        f"Normal speed movement, natural pacing. No slow motion. No facing camera directly. No subtitles. "
        f"Vertical 9:16 framing. Medium-wide shot from slight right angle. All three characters visible. "
        f"Sound: projector buzz, crash sound, chair creaking, ambient office hum."
    )


def make_seg2_prompt(char_text):
    return (
        f"Same high-end investor meeting room, floor-to-ceiling windows, city skyline. {char_text} "
        f"Li Yuan stands confidently at end of table, holding phone out. Wang and Investor B seated, "
        f"now leaning forward with widened eyes staring at the phone screen. "
        f"Li Yuan taps phone screen, the growth curve keeps climbing visibly. "
        f"Wang's jaw drops slightly, he removes his glasses to wipe them in disbelief. "
        f"Investor B's stern expression breaks into shocked admiration, she puts down her pen. "
        f"Li Yuan straightens up, pushes phone into his pocket confidently, and says: "
        f"'Three months, zero to one million users. Want to get on board?' "
        f"Wang scrambles to open his suit jacket inner pocket, pulling out a business card. "
        f"Investor B quickly reaches into her blazer pocket for her card too. "
        f"Li Yuan watches them both with the corner of his mouth curling up in a subtle satisfied smile. "
        f"All dialogue must finish before second 14. Leave at least 1 second of silence at end. "
        f"Normal speed movement, natural pacing. No slow motion. No facing camera directly. No subtitles. "
        f"Same camera angle as previous segment. Medium-wide shot, slight right angle. "
        f"Sound: phone tap, fabric rustling, chair scraping, card being pulled out."
    )


def gen_ref_images(style, prefix):
    """Generate reference images via Gemini with retry on 429."""
    # Check if images already exist
    existing = sorted([str(p) for p in ASSETS.glob(f"*{prefix}*.webp")])
    if len(existing) >= 3:
        print(f"=== {prefix} reference images already exist ({len(existing)} found), skipping ===", flush=True)
        for p in existing:
            sz = os.path.getsize(p) // 1024
            print(f"  ✓ {os.path.basename(p)} ({sz}KB)", flush=True)
        return existing

    specs_path = EXP / f"asset-specs-{prefix}.json"
    for attempt in range(5):
        print(f"=== Generating {prefix} reference images (attempt {attempt+1}) ===", flush=True)
        cmd = [
            "python3", "-u", str(TOOLS / "gemini_chargen.py"),
            "--specs", str(specs_path),
            "--out-dir", str(ASSETS),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                           env={**os.environ, "PYTHONUNBUFFERED": "1"})
        print(r.stdout, flush=True)
        if r.stderr:
            print(r.stderr, file=sys.stderr, flush=True)

        found = sorted([str(p) for p in ASSETS.glob(f"*{prefix}*.webp")])
        if len(found) >= 3:
            for p in found:
                sz = os.path.getsize(p) // 1024
                print(f"  ✓ {os.path.basename(p)} ({sz}KB)", flush=True)
            return found
        print(f"  Only {len(found)} images, waiting 30s before retry...", flush=True)
        time.sleep(30)

    # Return whatever we have
    found = sorted([str(p) for p in ASSETS.glob(f"*{prefix}*.webp")])
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

    # Print full prompt for logging
    print(f"\n  Seedance: {os.path.basename(output)} (prompt: {prompt[:120]}...)", flush=True)
    print(r.stdout, flush=True)

    ok = r.returncode == 0 and os.path.isfile(output)
    err = r.stderr if not ok else ""
    if err:
        print(f"  ✗ Error: {err[:500]}", file=sys.stderr, flush=True)
    if ok:
        sz = os.path.getsize(output) / (1024 * 1024)
        print(f"  ✓ {os.path.basename(output)} ({sz:.1f}MB, {elapsed:.0f}s)", flush=True)
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
    if r.returncode != 0 and r.stderr:
        print(r.stderr, file=sys.stderr, flush=True)
    return os.path.isfile(output)


def main():
    gen_log = {
        "experiment": "EXP-V7-031",
        "hypothesis": ["H-120: Illustration-style refs + Physical State Anchoring → cross-segment consistency"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tracks": {},
    }

    # ── Step 1: Generate reference images for both tracks concurrently ──
    print("\n=== Step 1: Generate reference images (anime + realistic) ===", flush=True)
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_anime = ex.submit(gen_ref_images, "anime", "anime")
        f_real = ex.submit(gen_ref_images, "realistic", "real")
        anime_imgs = f_anime.result()
        real_imgs = f_real.result()

    gen_log["assets"] = {"anime": anime_imgs, "realistic": real_imgs}

    if not anime_imgs or not real_imgs:
        print("⚠️ Missing reference images, cannot proceed!", flush=True)
        gen_log["error"] = "Missing reference images"
        with open(OUTPUT / "generation-log.json", "w") as f:
            json.dump(gen_log, f, indent=2, ensure_ascii=False)
        return

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
                "prompt": (anime_seg1_prompt if track == "anime" else real_seg1_prompt),
                "images": anime_imgs if track == "anime" else real_imgs,
                "result": seg1_results[track],
            }

    # Check for content moderation blocks — abandon immediately per standing order
    for track, res in seg1_results.items():
        err = res.get("error", "")
        if any(kw in err for kw in ["ContentModeration", "PrivacyInformation", "内容审核", "content_filter"]):
            print(f"\n⚠️  CONTENT MODERATION BLOCK on {track} Seg1! Abandoning track per standing order.", flush=True)
            gen_log["tracks"][track]["abandoned"] = True

    # ── Step 3: Generate Seg2 via video extension (concurrent) ──
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
                "prompt": (anime_seg2_prompt if track == "anime" else real_seg2_prompt),
                "result": seg2_results[track],
            }

    # ── Step 4: Concatenate ──
    print("\n=== Step 4: Concatenation ===", flush=True)
    finals = {}
    for track, seg1_p, seg2_p in [
        ("anime", anime_seg1_path, anime_seg2_path),
        ("realistic", real_seg1_path, real_seg2_path),
    ]:
        final = str(OUTPUT / f"{track.split('-')[0]}-final.mp4")
        if track == "realistic":
            final = str(OUTPUT / "real-final.mp4")
        else:
            final = str(OUTPUT / "anime-final.mp4")
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

    audio_failures = [k for k, v in audio_results.items() if not v]
    if audio_failures:
        print(f"\n⚠️  AUDIO FAILURES: {audio_failures}", flush=True)
        gen_log["audio_failures"] = audio_failures

    # Save audio check details per final
    for track_name in ["anime", "real"]:
        final_path = OUTPUT / f"{track_name}-final.mp4"
        if final_path.exists():
            check_data = {
                "seg1_audio": audio_results.get(f"{track_name}-seg1.mp4", False),
                "seg2_audio": audio_results.get(f"{track_name}-seg2.mp4", False),
                "final_audio": audio_results.get(f"{track_name}-final.mp4", False),
            }
            with open(OUTPUT / f"{track_name}-final-audio-check.json", "w") as f:
                json.dump(check_data, f, indent=2)

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

    # Final deliverable size check
    for track_name in ["anime", "real"]:
        fp = OUTPUT / f"{track_name}-final.mp4"
        if fp.exists():
            sz = fp.stat().st_size / (1024 * 1024)
            dur_r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(fp)],
                capture_output=True, text=True, timeout=10
            )
            dur = dur_r.stdout.strip()
            print(f"  {track_name}-final: {sz:.1f}MB, {dur}s", flush=True)


if __name__ == "__main__":
    main()
