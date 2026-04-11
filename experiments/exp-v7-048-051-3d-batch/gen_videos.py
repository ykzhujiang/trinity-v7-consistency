#!/usr/bin/env python3 -u
"""
Phase 2: Video generation for EXP-V7-048~051 (assets already uploaded).
Seg1 for all 4 in parallel → Seg2 for all 4 in parallel → Seg3 for all 4 in parallel.
"""
import json, os, sys, time, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
TOOLS = REPO / "tools"
BATCH_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

# Load asset IDs
ASSETS = json.loads((BATCH_DIR / "all_asset_ids.json").read_text())

# Experiment prompts
EXPS = {
    "v7-050-celshaded": {
        "style": "Cel-shaded 3D animation, Genshin Impact art style, clean outlines, flat shading with vibrant colors, anime-influenced 3D, stylized environment",
        "char_en": "22-year-old Chinese male, spiky short black hair slightly cartoonish, round face, large eyes, wearing orange T-shirt and plaid pajama pants with white apron",
        "scene_en": "Bright small kitchen, sunlight streaming through window, white cabinets, light wood countertop with eggs milk and bread, cute fridge magnets on wall, warm bright color tone",
        "segs": [
            "Aming takes eggs and milk from fridge places on counter, turns on gas stove, takes frying pan from cabinet",
            "Cracks egg into pan, a small piece of shell falls in, frantically uses chopsticks to fish out shell, mumbles in Mandarin Chinese: \"每次都这样\"",
            "Finishes fried egg onto plate, pours glass of milk, carries to table sits down, looks at his creation nods satisfiedly, starts eating",
        ],
    },
    "v7-048-pixar": {
        "style": "Pixar-quality 3D animation, soft ambient lighting, Disney character design, smooth subsurface scattering skin, large expressive eyes, stylized proportions",
        "char_en": "25-year-old Chinese male programmer, round face, fluffy short black hair, large expressive eyes, wearing grey hoodie and jeans, slightly hunched posture",
        "scene_en": "Small open-plan office at night, only one desk lamp on, 27-inch monitor glowing blue, coffee cup and snack wrappers on desk, blurred city night view through window",
        "segs": [
            "Xiaoli tiredly types on keyboard, rubs his eyes, takes a sip of coffee, frowns at code error on screen",
            "Continues debugging, suddenly screen turns green compilation passed, freezes for a moment, then slowly smiles, quietly speaks in Mandarin Chinese: \"终于过了\"",
            "Stands up and stretches, picks up phone to read message, happily clenches fist, packs up things to leave",
        ],
    },
    "v7-051-jpn3d": {
        "style": "Japanese 3D anime, Makoto Shinkai lighting quality, CG-anime hybrid, detailed atmospheric effects, soft bokeh background, anime character proportions with 3D rendering",
        "char_en": "17-year-old Chinese male high school student, black layered hair blown by wind, slim build, wearing white school uniform shirt sleeves rolled to elbows and dark blue school pants, canvas messenger bag",
        "scene_en": "School building rooftop, iron railings around perimeter, grey concrete floor, city skyline in distance, orange-red sunset with gradient clouds, evening backlight",
        "segs": [
            "Xiaotian pushes open rooftop door walks out, sunlight hits face squints slightly, walks to railing, puts bag on ground",
            "Rests both hands on railing, gazes at distant sunset, wind blows hair and shirt, takes deep breath and closes eyes",
            "Opens eyes, takes out earphones puts them on, picks up bag, turns to walk toward stairway door, glances back at sunset smiles, pushes door and leaves",
        ],
    },
    "v7-049-gamecg": {
        "style": "AAA game cinematic, Unreal Engine 5 quality, ray-traced global illumination, photorealistic materials, cinematic depth of field, game cutscene style",
        "char_en": "28-year-old Chinese woman, long straight black hair past shoulders, willow-leaf eyebrows, wearing cream white sweater and light blue jeans, silver bracelet",
        "scene_en": "Boutique coffee shop window booth, warm yellow pendant lamp, wooden table with latte and open book, rainy street view outside, raindrops on glass",
        "segs": [
            "Xiaoyu sits in booth, holds coffee cup with both hands for warmth, gazes at rain outside window, expression slightly wistful",
            "Puts down coffee, looks down turning book pages, occasionally glances toward entrance, fingers unconsciously fidgeting with bracelet",
            "Phone vibrates on table, picks up and reads message, corners of mouth slightly curl up, puts phone down and continues reading, expression becomes peaceful",
        ],
    },
}

SUFFIX = " No subtitles, no text overlay, no slow motion, character does not face camera directly. Normal speed movement, natural pacing."


def build_prompt(exp_key, seg_idx):
    e = EXPS[exp_key]
    if seg_idx == 0:
        p = f"{e['style']}. {e['scene_en']}. A {e['char_en']} — {e['segs'][seg_idx]}. Camera: medium shot, slight side angle, fixed position."
    else:
        p = f"Continuing the scene — {e['segs'][seg_idx]}. Same character, same location, consistent lighting and style."
    p += SUFFIX
    return p[:800]


def gen_seg(exp_key, seg_idx, keys):
    """Generate one segment. Returns output path or None."""
    exp_dir = BATCH_DIR / exp_key
    out_dir = exp_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = str(out_dir / f"seg{seg_idx+1}.mp4")

    prompt = build_prompt(exp_key, seg_idx)
    print(f"[{exp_key}] Seg{seg_idx+1}: prompt={len(prompt)}c", flush=True)

    # Save prompt for logging
    (exp_dir / f"seg{seg_idx+1}_prompt.txt").write_text(prompt)

    cmd = ["python3", "-u", str(TOOLS / "seedance_gen.py"), "--prompt", prompt, "--ratio", "9:16", "--out", out_path]

    if seg_idx == 0:
        # Image-to-video: use both char + scene reference images
        assets_dir = exp_dir / "assets"
        imgs = sorted(str(p) for p in assets_dir.glob("*.webp"))
        cmd.extend(["--images"] + imgs)
    else:
        # Extend from previous segment
        prev = str(out_dir / f"seg{seg_idx}.mp4")
        if not Path(prev).exists():
            print(f"[{exp_key}] ❌ Seg{seg_idx+1} skipped — prev segment missing", flush=True)
            return None
        cmd.extend(["--video", prev])

    t0 = time.time()
    r = subprocess.run(cmd, capture_output=False, text=True, timeout=1200)
    elapsed = time.time() - t0

    if Path(out_path).exists():
        size = Path(out_path).stat().st_size / 1024 / 1024
        print(f"[{exp_key}] ✅ Seg{seg_idx+1}: {size:.1f}MB, {elapsed:.0f}s", flush=True)
        return out_path
    else:
        print(f"[{exp_key}] ❌ Seg{seg_idx+1} failed after {elapsed:.0f}s", flush=True)
        return None


def concat_exp(exp_key):
    """Concat 3 segments."""
    out_dir = BATCH_DIR / exp_key / "output"
    segs = [str(out_dir / f"seg{i}.mp4") for i in range(1, 4)]
    if not all(Path(s).exists() for s in segs):
        print(f"[{exp_key}] ❌ Concat skipped — missing segments", flush=True)
        return None
    final = str(out_dir / "final.mp4")
    cmd = ["python3", "-u", str(TOOLS / "ffmpeg_concat.py"), "--inputs"] + segs + ["--out", final, "--check-audio"]
    subprocess.run(cmd, capture_output=False, text=True, timeout=120)
    if Path(final).exists():
        size = Path(final).stat().st_size / 1024 / 1024
        print(f"[{exp_key}] ✅ Final: {size:.1f}MB", flush=True)
        return final
    return None


def main():
    keys = load_keys()
    os.environ.setdefault("ARK_API_KEY", keys.get("ark_key") or "")
    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        try:
            sv = cfg["skills"]["entries"]["seedance-video"]["env"]
            os.environ.setdefault("VOLCANO_ACCESS_KEY", sv.get("VOLCANO_ACCESS_KEY", ""))
            os.environ.setdefault("VOLCANO_ACCESS_SECRET", sv.get("VOLCANO_ACCESS_SECRET", ""))
        except (KeyError, TypeError):
            pass

    exp_keys = list(EXPS.keys())  # priority order
    t0 = time.time()

    # Seg1: all 4 in parallel
    print("\n=== Seg1: Image-to-Video (4 parallel) ===", flush=True)
    seg1_results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(gen_seg, k, 0, keys): k for k in exp_keys}
        for f in as_completed(futs):
            k = futs[f]
            try:
                seg1_results[k] = f.result()
            except Exception as e:
                print(f"[{k}] ❌ Seg1 exception: {e}", flush=True)
                seg1_results[k] = None

    # Seg2: extend from Seg1, parallel for those that succeeded
    active = [k for k in exp_keys if seg1_results.get(k)]
    print(f"\n=== Seg2: Extend (parallel for {len(active)} active) ===", flush=True)
    seg2_results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(gen_seg, k, 1, keys): k for k in active}
        for f in as_completed(futs):
            k = futs[f]
            try:
                seg2_results[k] = f.result()
            except Exception as e:
                print(f"[{k}] ❌ Seg2 exception: {e}", flush=True)
                seg2_results[k] = None

    # Seg3: extend from Seg2
    active2 = [k for k in active if seg2_results.get(k)]
    print(f"\n=== Seg3: Extend (parallel for {len(active2)} active) ===", flush=True)
    seg3_results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(gen_seg, k, 2, keys): k for k in active2}
        for f in as_completed(futs):
            k = futs[f]
            try:
                seg3_results[k] = f.result()
            except Exception as e:
                print(f"[{k}] ❌ Seg3 exception: {e}", flush=True)
                seg3_results[k] = None

    # Concat
    print(f"\n=== Concat ===", flush=True)
    finals = {}
    for k in exp_keys:
        if seg3_results.get(k):
            finals[k] = concat_exp(k)
        else:
            print(f"[{k}] Skipped concat (incomplete segments)", flush=True)

    total = time.time() - t0
    print(f"\n{'='*60}", flush=True)
    print(f"DONE in {total:.0f}s ({total/60:.1f}min)", flush=True)
    for k in exp_keys:
        status = "✅ " + finals[k] if finals.get(k) else "❌ FAILED"
        print(f"  {k}: {status}", flush=True)

    # Save results
    results = []
    for k in exp_keys:
        results.append({
            "key": k,
            "seg1": bool(seg1_results.get(k)),
            "seg2": bool(seg2_results.get(k)),
            "seg3": bool(seg3_results.get(k)),
            "final": finals.get(k),
            "status": "SUCCESS" if finals.get(k) else "FAILED",
        })
    (BATCH_DIR / "video_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
