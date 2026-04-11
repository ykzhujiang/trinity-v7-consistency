#!/usr/bin/env python3
"""V7-033 Asset Generator — uses gen_image.py (raw HTTP) for reliability."""
import json, os, sys, subprocess, concurrent.futures
from pathlib import Path

# Load key from config
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
# Read key from openclaw.json  
import json as j
config_path = Path.home() / ".openclaw" / "openclaw.json"
config = j.load(open(config_path))
gi = config["skills"]["entries"]["gemini-image"]
API_KEY = gi.get("env", {}).get("GEMINI_API_KEY") or gi.get("apiKey")
BASE_URL = gi.get("env", {}).get("GEMINI_BASE_URL", "https://king.tokenssr.com/v1beta")

GEN_SCRIPT = Path.home() / ".openclaw-trinity-v3" / "workspace-operator" / "tools" / "gen_image.py"

EXP = Path(__file__).parent
ASSETS = EXP / "assets"

def gen(spec_file, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    specs = json.load(open(spec_file))
    results = []
    for s in specs:
        name = s["name"]
        out = out_dir / f"{name}.jpg"
        prompt = s["desc"]
        env = {**os.environ, "GEMINI_API_KEY": API_KEY, "PYTHONUNBUFFERED": "1"}
        r = subprocess.run(
            ["python3", "-u", str(GEN_SCRIPT), prompt, str(out)],
            capture_output=True, text=True, timeout=120, env=env
        )
        print(r.stdout, flush=True)
        if r.returncode != 0:
            print(f"FAIL {name}: {r.stderr[-300:]}", flush=True)
            results.append(False)
        else:
            results.append(True)
    return all(results)

if __name__ == "__main__":
    ok1 = gen(EXP / "asset-specs-anime.json", ASSETS / "anime")
    ok2 = gen(EXP / "asset-specs-real.json", ASSETS / "real")
    if ok1 and ok2:
        print("✅ All assets generated")
        # List files
        for d in [ASSETS / "anime", ASSETS / "real"]:
            for f in sorted(d.glob("*")):
                print(f"  {f.name}: {f.stat().st_size // 1024}KB")
    else:
        print("⛔ Some assets failed")
        sys.exit(1)
