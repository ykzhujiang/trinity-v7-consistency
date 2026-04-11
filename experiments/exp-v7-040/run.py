#!/usr/bin/env python3 -u
"""
EXP-V7-040 Runner — Camera Angle Constraint + Asset Upload Dual-Track Test
Story: 外卖小哥的隐藏身份 (Delivery Rider's Hidden Identity) — 李飞, 25yo
Key tests:
  1. Camera angle delta ≤15° between Seg1-P4 and Seg2-P1
  2. Independent concat (B1 mode) — NOT video extension
  3. Asset upload to Volcano Engine → asset:// URIs
  4. Two characters: 李飞 + 老大爷
  5. Single scene: commercial street

Steps:
  1. Generate reference assets (gemini_chargen.py) — 6 images concurrent
  2. Upload assets to Volcano Engine (ark_asset_upload.py) → asset:// URIs
  3. Seg1 generation (anime+realistic concurrent)
  4. Seg2 generation (anime+realistic concurrent) — INDEPENDENT, not extension
  5. Concat + per-segment audio check
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
EXP_DIR = Path(__file__).resolve().parent
ASSETS = EXP_DIR / "assets"
OUTPUT = EXP_DIR / "output"
ASSETS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

# ============================================================
# Character + Scene descriptions
# ============================================================
LIFEI_CN = "25岁中国男性外卖小哥，精瘦但有隐藏肌肉线条，短寸头，黄色外卖制服，深色长裤，锐利但常带笑意的眼神"
LIFEI_EN = "25-year-old Chinese male delivery rider, lean but muscular build, buzz cut hair, yellow delivery uniform, dark trousers, sharp eyes with a habitual smile"

GRANDPA_CN = "70岁中国老大爷，灰色外套，拄拐杖，慈祥面容，白发稀疏"
GRANDPA_EN = "70-year-old Chinese elderly man in grey coat with walking cane, kind face, thinning white hair"

SCENE_CN = "繁忙的中国城市商业街，午餐时间，阳光明媚，各种中文店铺招牌，人流如织"
SCENE_EN = "busy Chinese urban commercial street at lunch time, bright sunlight, Chinese shop signs, crowded pedestrians"

# ============================================================
# Seg1 Prompts — Camera angles: 30°→25°→20°→15° (left side)
# ============================================================
SEG1_PROMPT_ANIME = (
    f"Japanese anime style digital animation. A {LIFEI_EN} stands beside his electric scooter on a {SCENE_EN}. "
    "Camera: side medium shot from left 30 degrees. "
    "He looks at his phone with a frown, then hangs the delivery bag on the scooter while muttering. "
    "Camera slowly pushes to medium close-up, angle shifting to left 20 degrees. "
    f"Suddenly a van screeches to a halt nearby, almost hitting a {GRANDPA_EN} crossing the road. "
    "The delivery rider instantly dashes forward and grabs the old man's arm, pulling him to safety with inhuman reflexes. "
    "Camera pulls back to medium shot, left 15 degrees. Bystanders stare in shock. "
    "The rider's speed is unnaturally fast for a normal person. "
    "Dialogue (Chinese, must end before second 12): "
    "[李飞]'又来这种不可能的单...' [李飞]'超时扣钱，不接没钱，这是什么人生。' [李飞]'大爷小心！' [路人]'这外卖小哥反应也太快了吧？' "
    "All dialogue must be in Chinese Mandarin. Normal speed movement, natural pacing. "
    "Characters never face camera directly. 180-degree rule: 李飞 always on left side of frame. "
    "No subtitles, no slow motion. 9:16 vertical."
)

SEG1_PROMPT_REAL = (
    f"DSLR photograph, 35mm lens. A {LIFEI_EN} stands beside his electric scooter on a {SCENE_EN}. "
    "Camera: side medium shot from left 30 degrees. "
    "He looks at his phone with a frown, then hangs the delivery bag on the scooter while muttering. "
    "Camera slowly pushes to medium close-up, angle shifting to left 20 degrees. "
    f"Suddenly a van screeches to a halt nearby, almost hitting a {GRANDPA_EN} crossing the road. "
    "The delivery rider instantly dashes forward and grabs the old man's arm, pulling him to safety with inhuman reflexes. "
    "Camera pulls back to medium shot, left 15 degrees. Bystanders stare in shock. "
    "The rider's speed is unnaturally fast for a normal person. "
    "Dialogue (Chinese, must end before second 12): "
    "[李飞]'又来这种不可能的单...' [李飞]'超时扣钱，不接没钱，这是什么人生。' [李飞]'大爷小心！' [路人]'这外卖小哥反应也太快了吧？' "
    "All dialogue must be in Chinese Mandarin. Normal speed movement, natural pacing. "
    "Characters never face camera directly. 180-degree rule: 李飞 always on left side of frame. "
    "No subtitles, no slow motion. 9:16 vertical. Cinematic realistic style."
)

# ============================================================
# Seg2 Prompts — Camera angles: 15°→20°→25°→30° (mirror of Seg1)
# ============================================================
SEG2_PROMPT_ANIME = (
    f"Japanese anime style digital animation. On the same {SCENE_EN}. "
    f"A {LIFEI_EN} is supporting a {GRANDPA_EN} standing by the roadside. Bystanders watch. "
    "Camera: side medium shot from left 15 degrees (MATCHING previous segment ending angle). "
    "The old man pats the rider's hand gratefully. The rider smiles and waves it off. "
    "Camera shifts to left 20 degrees. The rider's expression flickers with something complex before returning to a smile. "
    "Camera pushes to medium close-up at left 25 degrees as he walks back to his scooter, checks his phone — 5 minutes lost. "
    "Camera pulls to medium shot at left 30 degrees. He mounts the scooter, takes a deep breath, "
    "and his eyes flash with a sharp intensity that doesn't match a delivery rider. "
    "Dialogue (Chinese, must end before second 12): "
    "[李飞]'没事没事，赶紧走人行道。' [老大爷]'小伙子，你以前练过功夫吧？' "
    "[李飞]'哪有，就是送外卖跑多了，腿脚利索。' [李飞]'糟了，还剩25分钟，3.8公里...' [李飞]'那就...认真跑一次。' "
    "All dialogue must be in Chinese Mandarin. Normal speed movement, natural pacing. "
    "Characters never face camera directly. 180-degree rule: 李飞 always on left side of frame. "
    "No subtitles, no slow motion. 9:16 vertical."
)

SEG2_PROMPT_REAL = (
    f"DSLR photograph, 35mm lens. On the same {SCENE_EN}. "
    f"A {LIFEI_EN} is supporting a {GRANDPA_EN} standing by the roadside. Bystanders watch. "
    "Camera: side medium shot from left 15 degrees (MATCHING previous segment ending angle). "
    "The old man pats the rider's hand gratefully. The rider smiles and waves it off. "
    "Camera shifts to left 20 degrees. The rider's expression flickers with something complex before returning to a smile. "
    "Camera pushes to medium close-up at left 25 degrees as he walks back to his scooter, checks his phone — 5 minutes lost. "
    "Camera pulls to medium shot at left 30 degrees. He mounts the scooter, takes a deep breath, "
    "and his eyes flash with a sharp intensity that doesn't match a delivery rider. "
    "Dialogue (Chinese, must end before second 12): "
    "[李飞]'没事没事，赶紧走人行道。' [老大爷]'小伙子，你以前练过功夫吧？' "
    "[李飞]'哪有，就是送外卖跑多了，腿脚利索。' [李飞]'糟了，还剩25分钟，3.8公里...' [李飞]'那就...认真跑一次。' "
    "All dialogue must be in Chinese Mandarin. Normal speed movement, natural pacing. "
    "Characters never face camera directly. 180-degree rule: 李飞 always on left side of frame. "
    "No subtitles, no slow motion. 9:16 vertical. Cinematic realistic style."
)


def step1_generate_assets(keys):
    """Generate 6 reference assets using gemini_chargen.py (concurrent)."""
    print("\n" + "="*60)
    print("STEP 1: Generate Reference Assets")
    print("="*60, flush=True)
    
    specs_path = EXP_DIR / "asset_specs.json"
    cmd = [
        "python3", "-u", str(TOOLS / "gemini_chargen.py"),
        "--specs", str(specs_path),
        "--out-dir", str(ASSETS)
    ]
    r = subprocess.run(cmd, timeout=600)
    if r.returncode != 0:
        print(f"[ERROR] Asset generation failed with code {r.returncode}", flush=True)
        return False
    
    # Check all 6 assets exist
    expected = ["char-lifei-anime", "char-lifei-realistic", "char-grandpa-anime", "char-grandpa-realistic",
                "scene-street-anime", "scene-street-realistic"]
    missing = []
    for name in expected:
        found = list(ASSETS.glob(f"{name}.*"))
        if not found:
            missing.append(name)
        else:
            print(f"  ✅ {name}: {found[0].name} ({found[0].stat().st_size // 1024}KB)", flush=True)
    
    if missing:
        print(f"  ❌ Missing assets: {missing}", flush=True)
        return False
    return True


def step2_upload_assets(keys):
    """Upload assets to Volcano Engine trusted asset library."""
    print("\n" + "="*60)
    print("STEP 2: Upload Assets to Volcano Engine")
    print("="*60, flush=True)
    
    asset_ids = {}
    asset_files = sorted(ASSETS.glob("*.*"))
    
    if not asset_files:
        print("[ERROR] No asset files found", flush=True)
        return None
    
    # Try Volcano upload first
    vol_ak = os.environ.get("VOLCANO_ACCESS_KEY")
    vol_sk = os.environ.get("VOLCANO_ACCESS_SECRET")
    
    if vol_ak and vol_sk:
        print("  Using Volcano Engine asset upload...", flush=True)
        for af in asset_files:
            cmd = [
                "python3", "-u", str(TOOLS / "ark_asset_upload.py"),
                "--image", str(af),
                "--group-name", "exp-v7-040"
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and "asset://" in r.stdout:
                for line in r.stdout.strip().split("\n"):
                    if "asset://" in line:
                        asset_id = line.strip().split()[-1]
                        asset_ids[af.stem] = asset_id
                        print(f"  ✅ {af.stem} → {asset_id}", flush=True)
                        break
            else:
                print(f"  ❌ Upload failed for {af.name}: {r.stderr[:200]}", flush=True)
    
    if not asset_ids:
        # Fallback: upload to tmpfiles.org for URL-based Seedance input
        print("  Volcano keys not available. Using tmpfiles.org fallback...", flush=True)
        import requests
        for af in asset_files:
            try:
                with open(af, "rb") as f:
                    resp = requests.post("https://tmpfiles.org/api/v1/upload",
                                        files={"file": f}, timeout=120)
                resp.raise_for_status()
                page_url = resp.json()["data"]["url"]
                direct_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                asset_ids[af.stem] = direct_url
                print(f"  ✅ {af.stem} → {direct_url}", flush=True)
            except Exception as e:
                print(f"  ❌ Upload failed for {af.name}: {e}", flush=True)
    
    # Save asset IDs
    ids_path = EXP_DIR / "asset_ids.json"
    with open(ids_path, "w") as f:
        json.dump(asset_ids, f, indent=2)
    print(f"  Saved {len(asset_ids)} asset IDs to {ids_path}", flush=True)
    return asset_ids


def step3_generate_seg1(keys, asset_ids):
    """Generate Seg1 for anime+realistic concurrently."""
    print("\n" + "="*60)
    print("STEP 3: Generate Seg1 (anime + realistic concurrent)")
    print("="*60, flush=True)
    
    seedance = keys.get("seedance_script")
    ark_key = keys.get("ark_key")
    if not seedance:
        print("[ERROR] seedance.py not found", flush=True)
        return False
    
    # Build image lists for each track
    anime_images = [v for k, v in asset_ids.items() if "anime" in k]
    real_images = [v for k, v in asset_ids.items() if "realistic" in k]
    print(f"  Anime images: {len(anime_images)}, Realistic images: {len(real_images)}", flush=True)
    
    batch = [
        {
            "id": "anime-seg1",
            "prompt": SEG1_PROMPT_ANIME,
            "images": anime_images,
            "out": str(OUTPUT / "anime-seg1.mp4")
        },
        {
            "id": "real-seg1",
            "prompt": SEG1_PROMPT_REAL,
            "images": real_images,
            "out": str(OUTPUT / "real-seg1.mp4")
        }
    ]
    
    batch_path = EXP_DIR / "seg1_batch.json"
    with open(batch_path, "w") as f:
        json.dump(batch, f, indent=2, ensure_ascii=False)
    
    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--batch", str(batch_path),
        "--out-dir", str(OUTPUT)
    ]
    r = subprocess.run(cmd, timeout=900)
    
    ok = True
    for track in ["anime-seg1", "real-seg1"]:
        mp4 = OUTPUT / f"{track}.mp4"
        if mp4.exists() and mp4.stat().st_size > 10000:
            print(f"  ✅ {track}: {mp4.stat().st_size // 1024}KB", flush=True)
        else:
            print(f"  ❌ {track}: missing or too small", flush=True)
            ok = False
    return ok


def step4_generate_seg2(keys, asset_ids):
    """Generate Seg2 for anime+realistic concurrently — INDEPENDENT (not video extension)."""
    print("\n" + "="*60)
    print("STEP 4: Generate Seg2 INDEPENDENTLY (anime + realistic concurrent)")
    print("="*60, flush=True)
    
    seedance = keys.get("seedance_script")
    if not seedance:
        print("[ERROR] seedance.py not found", flush=True)
        return False
    
    anime_images = [v for k, v in asset_ids.items() if "anime" in k]
    real_images = [v for k, v in asset_ids.items() if "realistic" in k]
    
    batch = [
        {
            "id": "anime-seg2",
            "prompt": SEG2_PROMPT_ANIME,
            "images": anime_images,
            "out": str(OUTPUT / "anime-seg2.mp4")
        },
        {
            "id": "real-seg2",
            "prompt": SEG2_PROMPT_REAL,
            "images": real_images,
            "out": str(OUTPUT / "real-seg2.mp4")
        }
    ]
    
    batch_path = EXP_DIR / "seg2_batch.json"
    with open(batch_path, "w") as f:
        json.dump(batch, f, indent=2, ensure_ascii=False)
    
    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--batch", str(batch_path),
        "--out-dir", str(OUTPUT)
    ]
    r = subprocess.run(cmd, timeout=900)
    
    ok = True
    for track in ["anime-seg2", "real-seg2"]:
        mp4 = OUTPUT / f"{track}.mp4"
        if mp4.exists() and mp4.stat().st_size > 10000:
            print(f"  ✅ {track}: {mp4.stat().st_size // 1024}KB", flush=True)
        else:
            print(f"  ❌ {track}: missing or too small", flush=True)
            ok = False
    return ok


def step5_concat_and_check(keys):
    """Concatenate segments and check audio integrity."""
    print("\n" + "="*60)
    print("STEP 5: Concat + Audio Check")
    print("="*60, flush=True)
    
    results = {}
    for track in ["anime", "real"]:
        seg1 = OUTPUT / f"{track}-seg1.mp4"
        seg2 = OUTPUT / f"{track}-seg2.mp4"
        final = OUTPUT / f"{track}-final.mp4"
        
        if not seg1.exists() or not seg2.exists():
            print(f"  ⏭️ {track}: missing segments, skipping", flush=True)
            results[track] = {"ok": False, "reason": "missing segments"}
            continue
        
        cmd = [
            "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
            "--inputs", str(seg1), str(seg2),
            "--out", str(final),
            "--check-audio"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(r.stdout, flush=True)
        if r.stderr:
            print(r.stderr, flush=True)
        
        if final.exists() and final.stat().st_size > 20000:
            print(f"  ✅ {track}-final: {final.stat().st_size // 1024}KB", flush=True)
            
            # Per-segment audio check (standing order)
            audio_ok = True
            for seg_name in [f"{track}-seg1.mp4", f"{track}-seg2.mp4"]:
                seg_path = OUTPUT / seg_name
                probe = subprocess.run([
                    "ffprobe", "-v", "error", "-select_streams", "a",
                    "-show_entries", "stream=duration", "-of", "csv=p=0",
                    str(seg_path)
                ], capture_output=True, text=True)
                try:
                    dur = float(probe.stdout.strip().split("\n")[0])
                    if dur < 1.0:
                        print(f"  ❌ {seg_name}: audio too short ({dur:.1f}s)", flush=True)
                        audio_ok = False
                    else:
                        print(f"  ✅ {seg_name}: audio {dur:.1f}s", flush=True)
                except (ValueError, IndexError):
                    print(f"  ❌ {seg_name}: NO AUDIO TRACK", flush=True)
                    audio_ok = False
            
            results[track] = {"ok": audio_ok, "path": str(final)}
        else:
            print(f"  ❌ {track}-final: concat failed", flush=True)
            results[track] = {"ok": False, "reason": "concat failed"}
    
    return results


def step6_push_github():
    """Push results to GitHub."""
    print("\n" + "="*60)
    print("STEP 6: Push to GitHub")
    print("="*60, flush=True)
    
    repo = Path.home() / "trinity-v7-consistency"
    cmds = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", "[operator][cycle-906] EXP-V7-040: camera angle constraint + asset upload dual-track"],
        ["git", "pull", "--rebase", "origin", "main"],
        ["git", "push", "origin", "main"]
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, timeout=60)
        print(f"  {' '.join(cmd[:3])}: {'OK' if r.returncode == 0 else 'FAIL'}", flush=True)
        if r.returncode != 0 and "commit" not in cmd[1]:
            print(f"    {r.stderr[:200]}", flush=True)


def main():
    print("=" * 60)
    print("EXP-V7-040: Camera Angle Constraint + Asset Upload Test")
    print("Story: 外卖小哥的隐藏身份 — 李飞 (25yo delivery rider)")
    print("Method: Independent concat (B1) with ≤15° angle constraint")
    print("=" * 60, flush=True)
    
    keys = load_keys()
    print(f"  Gemini: {'✅' if keys['gemini_key'] else '❌'}")
    print(f"  ARK: {'✅' if keys['ark_key'] else '❌'}")
    print(f"  Seedance: {'✅' if keys['seedance_script'] else '❌'}", flush=True)
    
    # Step 1: Generate assets
    if not step1_generate_assets(keys):
        print("\n[ABORT] Asset generation failed", flush=True)
        return
    
    # Step 2: Upload assets
    asset_ids = step2_upload_assets(keys)
    if not asset_ids:
        print("\n[ABORT] Asset upload failed", flush=True)
        return
    
    # Step 3: Seg1 (anime + realistic concurrent)
    seg1_ok = step3_generate_seg1(keys, asset_ids)
    
    # Step 4: Seg2 (anime + realistic concurrent) — independent
    seg2_ok = step4_generate_seg2(keys, asset_ids)
    
    # Step 5: Concat + audio check
    results = step5_concat_and_check(keys)
    
    # Step 6: Push to GitHub
    step6_push_github()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for track, res in results.items():
        status = "✅ PASS" if res.get("ok") else f"❌ FAIL ({res.get('reason', 'audio issue')})"
        print(f"  {track}: {status}", flush=True)
    
    # Save generation log
    log = {
        "experiment": "EXP-V7-040",
        "hypothesis": "H-388: camera angle ≤15° delta improves anime continuity to ≥8/10",
        "method": "independent_concat_B1",
        "camera_constraint": "Seg1 ends at left 15°, Seg2 starts at left 15° (Δ=0°)",
        "asset_ids": asset_ids,
        "results": results,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    }
    log_path = EXP_DIR / "generation-log.json"
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n  Generation log saved to {log_path}", flush=True)


if __name__ == "__main__":
    main()
