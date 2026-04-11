#!/usr/bin/env python3
"""Quick retry wrapper for EXP-V7-031: handles Gemini 429 rate limits."""
import subprocess, sys, os, time

PROJ = os.path.expanduser("~/trinity-v7-consistency")
EXP = f"{PROJ}/experiments/exp-v7-031"
TOOLS = f"{PROJ}/tools"

os.chdir(PROJ)

def gen_images(prefix):
    specs = f"{EXP}/asset-specs-{prefix}.json"
    out = f"{EXP}/assets"
    for attempt in range(5):
        print(f"\n=== Attempt {attempt+1} for {prefix} images ===", flush=True)
        r = subprocess.run(
            ["python3", "-u", f"{TOOLS}/gemini_chargen.py", "--specs", specs, "--out-dir", out],
            capture_output=True, text=True, timeout=300,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        print(r.stdout, flush=True)
        if r.stderr:
            print(r.stderr, file=sys.stderr, flush=True)
        # Check if all images generated
        import glob
        found = glob.glob(f"{out}/*{prefix}*.webp")
        if len(found) >= 3:  # at least 3 images (chars + scene)
            print(f"✓ {prefix}: {len(found)} images generated", flush=True)
            return found
        print(f"  Only {len(found)} images, waiting 30s before retry...", flush=True)
        time.sleep(30)
    print(f"✗ {prefix}: Failed after 5 attempts", flush=True)
    return []

# Generate both sets with delays between
anime_imgs = gen_images("anime")
time.sleep(15)
real_imgs = gen_images("real")

if not anime_imgs or not real_imgs:
    print("⚠️ Still missing images after retries. Exiting.", flush=True)
    sys.exit(1)

print(f"\n✓ All images ready. Now running main pipeline...", flush=True)

# Now run the main runner (which will find existing images and skip regeneration)
# Actually, let's just do the Seedance part directly
r = subprocess.run(
    ["python3", "-u", f"{PROJ}/scripts/exp_v7_031_runner.py"],
    timeout=3600, env={**os.environ, "PYTHONUNBUFFERED": "1"}
)
sys.exit(r.returncode)
