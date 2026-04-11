#!/usr/bin/env python3 -u
"""Phase 3: Generate only Seg3 (extend from Seg2) + concat for all 4 experiments."""
import json, os, sys, time, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
TOOLS = REPO / "tools"
BATCH_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

SUFFIX = " No subtitles, no text overlay, no slow motion, character does not face camera directly. Normal speed movement, natural pacing."

SEG3_PROMPTS = {
    "v7-050-celshaded": "Continuing the scene — Finishes fried egg onto plate, pours glass of milk, carries to table sits down, looks at his creation nods satisfiedly, starts eating. Same character, same location, consistent lighting and style." + SUFFIX,
    "v7-048-pixar": "Continuing the scene — Stands up and stretches, picks up phone to read message, happily clenches fist, packs up things to leave. Same character, same location, consistent lighting and style." + SUFFIX,
    "v7-051-jpn3d": "Continuing the scene — Opens eyes, takes out earphones puts them on, picks up bag, turns to walk toward stairway door, glances back at sunset smiles, pushes door and leaves. Same character, same location, consistent lighting and style." + SUFFIX,
    "v7-049-gamecg": "Continuing the scene — Phone vibrates on table, picks up and reads message, corners of mouth slightly curl up, puts phone down and continues reading, expression becomes peaceful. Same character, same location, consistent lighting and style." + SUFFIX,
}

def gen_seg3(exp_key, keys):
    out_dir = BATCH_DIR / exp_key / "output"
    seg2 = str(out_dir / "seg2.mp4")
    seg3 = str(out_dir / "seg3.mp4")
    if Path(seg3).exists():
        print(f"[{exp_key}] Seg3 already exists, skipping", flush=True)
        return seg3
    prompt = SEG3_PROMPTS[exp_key][:800]
    cmd = ["python3", "-u", str(TOOLS / "seedance_gen.py"), "--prompt", prompt, "--video", seg2, "--ratio", "9:16", "--out", seg3]
    t0 = time.time()
    subprocess.run(cmd, capture_output=False, text=True, timeout=1200)
    elapsed = time.time() - t0
    if Path(seg3).exists():
        size = Path(seg3).stat().st_size / 1024 / 1024
        print(f"[{exp_key}] ✅ Seg3: {size:.1f}MB, {elapsed:.0f}s", flush=True)
        return seg3
    print(f"[{exp_key}] ❌ Seg3 failed after {elapsed:.0f}s", flush=True)
    return None

def concat_exp(exp_key):
    out_dir = BATCH_DIR / exp_key / "output"
    segs = [str(out_dir / f"seg{i}.mp4") for i in range(1, 4)]
    if not all(Path(s).exists() for s in segs):
        return None
    final = str(out_dir / "final.mp4")
    subprocess.run(["python3", "-u", str(TOOLS / "ffmpeg_concat.py"), "--inputs"] + segs + ["--out", final, "--check-audio"], capture_output=False, text=True, timeout=120)
    if Path(final).exists():
        size = Path(final).stat().st_size / 1024 / 1024
        print(f"[{exp_key}] ✅ Final: {size:.1f}MB", flush=True)
        return final
    return None

def main():
    keys = load_keys()
    os.environ.setdefault("ARK_API_KEY", keys.get("ark_key") or "")
    cfg = json.loads((Path.home() / ".openclaw" / "openclaw.json").read_text())
    try:
        sv = cfg["skills"]["entries"]["seedance-video"]["env"]
        os.environ.setdefault("VOLCANO_ACCESS_KEY", sv.get("VOLCANO_ACCESS_KEY", ""))
        os.environ.setdefault("VOLCANO_ACCESS_SECRET", sv.get("VOLCANO_ACCESS_SECRET", ""))
    except (KeyError, TypeError):
        pass

    exp_keys = list(SEG3_PROMPTS.keys())
    
    print("=== Seg3: Extend (4 parallel) ===", flush=True)
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(gen_seg3, k, keys): k for k in exp_keys}
        for f in as_completed(futs):
            k = futs[f]
            try:
                results[k] = f.result()
            except Exception as e:
                print(f"[{k}] ❌ {e}", flush=True)
                results[k] = None

    print("\n=== Concat ===", flush=True)
    for k in exp_keys:
        if results.get(k):
            concat_exp(k)
        else:
            print(f"[{k}] Skipped", flush=True)

    print("\nDONE", flush=True)

if __name__ == "__main__":
    main()
