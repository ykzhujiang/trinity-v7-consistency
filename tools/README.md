# V7 Pipeline Modular Tools

Reusable CLI tools for the V7 dual-segment video pipeline. Each tool does one thing, supports `--help`, and can be tested independently.

**All scripts must be run with `python3 -u`** (unbuffered output).

## Tools

| Tool | Purpose | Concurrency |
|------|---------|-------------|
| `gemini_chargen.py` | Generate character/scene images via Gemini | ✅ batch concurrent |
| `seedance_gen.py` | Generate videos via Seedance 2.0 | ✅ batch concurrent |
| `ffmpeg_concat.py` | Concatenate segments + audio integrity check | — |
| `frame_extract.py` | Extract frames (last frame, at timestamp) | — |
| `config_loader.py` | Shared API key/config loader (library, not CLI) | — |

## Quick Start

```bash
# Generate character images (concurrent)
python3 -u tools/gemini_chargen.py --specs assets-spec.json --out-dir assets/

# Generate Seg1 video
python3 -u tools/seedance_gen.py --prompt "..." --images assets/char-main.webp assets/scene.webp --out output/seg1-anime.mp4

# Concurrent Seg1 (anime + realistic)
python3 -u tools/seedance_gen.py --batch seg1-batch.json --out-dir output/

# Extract last frame for Seg2 anchor
python3 -u tools/frame_extract.py --input output/seg1-anime.mp4 --last --out output/seg1-last.png

# Generate Seg2 (video extension)
python3 -u tools/seedance_gen.py --prompt "..." --video output/seg1-anime.mp4 --out output/seg2-anime.mp4

# Concatenate + audio check
python3 -u tools/ffmpeg_concat.py --inputs output/seg1-anime.mp4 output/seg2-anime.mp4 --out output/final-anime.mp4 --check-audio --check-per-segment
```

## Experiment Runner Pattern

New experiments should NOT copy pipeline code. Instead, write a thin runner that:
1. Defines the storyboard content (prompts, descriptions)
2. Writes asset specs JSON
3. Calls tools via subprocess or import

```python
# experiments/exp-v7-024/run.py (thin runner example)
import subprocess, json

# 1. Write asset specs
specs = [{"name": "陈磊", "type": "character", "desc": "...", "style": "anime"}, ...]
with open("assets-spec.json", "w") as f: json.dump(specs, f)

# 2. Generate assets (concurrent)
subprocess.run(["python3", "-u", "tools/gemini_chargen.py", "--specs", "assets-spec.json", "--out-dir", "assets/"])

# 3. Generate videos (concurrent where possible)
# ... call seedance_gen.py, ffmpeg_concat.py, etc.
```
