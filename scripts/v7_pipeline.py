#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "requests>=2.28.0",
#     "pillow>=10.0.0",
#     "httpx[socks]>=0.24.0",
# ]
# ///
"""
V7 Dual Segment Pipeline — Consistency Research

Generates dual-segment videos testing cross-segment consistency.
Three modes:
  1. video-extension: Segment2 = Extend @video1 by 15s
  2. first-frame-anchor: Segment2 uses last frame of Seg1 as first frame
  3. hybrid: Combine video extension + character refs + first frame

Usage:
    uv run scripts/v7_pipeline.py \
        --storyboard experiments/exp-v7-001/storyboard.md \
        --mode video-extension \
        --output-dir experiments/exp-v7-001/output/
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from io import BytesIO

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_keys():
    """Load API keys from env or openclaw.json."""
    config = {}
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    gemini_base_url = os.environ.get("GEMINI_BASE_URL")
    if not gemini_key:
        try:
            gi = config["skills"]["entries"]["gemini-image"]
            gemini_key = gi.get("env", {}).get("GEMINI_API_KEY") or gi.get("apiKey")
            gemini_base_url = gi.get("env", {}).get("GEMINI_BASE_URL")
        except (KeyError, TypeError):
            pass

    ark_key = os.environ.get("ARK_API_KEY")
    if not ark_key:
        try:
            ark_key = config["skills"]["entries"]["seedance-video"]["env"]["ARK_API_KEY"]
        except (KeyError, TypeError):
            pass
        if not ark_key:
            try:
                ark_key = config["models"]["providers"]["ark"]["apiKey"]
            except (KeyError, TypeError):
                pass

    seedance_script = Path.home() / ".openclaw" / "workspace" / "skills" / "seedance-video" / "scripts" / "seedance.py"

    return {
        "gemini_key": gemini_key,
        "gemini_base_url": gemini_base_url,
        "ark_key": ark_key,
        "seedance_script": str(seedance_script) if seedance_script.exists() else None,
    }


# ---------------------------------------------------------------------------
# Storyboard parsing
# ---------------------------------------------------------------------------

def parse_storyboard(path: str):
    """Parse the V7 storyboard format."""
    with open(path) as f:
        content = f.read()

    # Extract character descriptions
    characters = {}
    cast_section = re.search(r"### Cast\s*\n(.*?)### Location", content, re.DOTALL)
    if cast_section:
        char_blocks = re.findall(
            r"\*\*角色[A-Z]\s*—\s*(\S+)\*\*\s*\n((?:- .*\n)+)",
            cast_section.group(1)
        )
        for name, desc in char_blocks:
            characters[name] = desc.strip()

    # Extract location description
    location_desc = ""
    loc_section = re.search(r"### Location\s*\n\*\*(.+?)\*\*\s*\n((?:- .*\n)+)", content)
    if loc_section:
        location_desc = loc_section.group(2).strip()

    # Extract segments
    segments = []
    seg_pattern = re.compile(r"^## Segment (\d+) \| (.+)$", re.MULTILINE)
    seg_starts = list(seg_pattern.finditer(content))

    for i, match in enumerate(seg_starts):
        start = match.start()
        end = seg_starts[i + 1].start() if i + 1 < len(seg_starts) else len(content)
        seg_text = content[start:end].strip()

        # Extract parts
        parts = re.findall(r"\[Part (\d+)\] (.+?)(?=\[Part|\Z)", seg_text, re.DOTALL)

        # Extract physical state
        phys_match = re.search(r"\*\*Physical State\*\*:\s*(.+)", seg_text)
        physical_state = phys_match.group(1).strip() if phys_match else ""

        # Extract camera
        cam_match = re.search(r"\*\*Camera\*\*:\s*(.+)", seg_text)
        camera = cam_match.group(1).strip() if cam_match else ""

        segments.append({
            "number": int(match.group(1)),
            "title": match.group(2),
            "physical_state": physical_state,
            "camera": camera,
            "parts": [(int(n), text.strip()) for n, text in parts],
            "raw": seg_text,
        })

    return characters, location_desc, segments


# ---------------------------------------------------------------------------
# Asset generation (Gemini)
# ---------------------------------------------------------------------------

def generate_asset(gemini_key: str, prompt: str, output_path: str, aspect="9:16", base_url=None):
    """Generate an image using Gemini and save it."""
    from google import genai
    from google.genai import types

    kwargs = {"api_key": gemini_key}
    if base_url:
        kwargs["http_options"] = types.HttpOptions(base_url=base_url)

    client = genai.Client(**kwargs)

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            img_data = part.inline_data.data
            # Compress to WebP
            from PIL import Image
            img = Image.open(BytesIO(img_data))
            # Resize to max 600px width
            if img.width > 600:
                ratio = 600 / img.width
                img = img.resize((600, int(img.height * ratio)), Image.LANCZOS)
            img.save(output_path, "WEBP", quality=75)
            print(f"  → Saved: {output_path} ({os.path.getsize(output_path) // 1024}KB)")
            return True

    print(f"  ✗ No image generated for {output_path}")
    return False


def generate_all_assets(gemini_key: str, characters: dict, location_desc: str, output_dir: str, base_url=None):
    """Generate character portraits and scene images."""
    os.makedirs(output_dir, exist_ok=True)
    assets = {}

    # Character portraits
    for name, desc in characters.items():
        path = os.path.join(output_dir, f"char-{name}.webp")
        prompt = (
            f"Anime-style character portrait for animation production. "
            f"9:16 vertical format. The character is: {desc}. "
            f"Semi-realistic anime illustration style, soft studio lighting, clean background. "
            f"Character is looking slightly to the left (not at camera). "
            f"Upper body visible. High detail, vibrant colors, cinematic anime quality."
        )
        print(f"Generating character asset: {name}")
        if generate_asset(gemini_key, prompt, path, base_url=base_url):
            assets[name] = path

    # Scene
    scene_path = os.path.join(output_dir, "scene-office.webp")
    prompt = (
        f"Anime-style wide establishing shot of a modern office interior for animation. "
        f"9:16 vertical format. {location_desc}. "
        f"No people in the scene. Semi-realistic anime illustration style, warm lighting, cinematic quality. "
        f"The office has a glass door on the left, a desk with laptop and coffee cup in the center, "
        f"and large floor-to-ceiling windows with city skyline view on the right."
    )
    print("Generating scene asset: office")
    if generate_asset(gemini_key, prompt, scene_path, base_url=base_url):
        assets["scene-office"] = scene_path

    return assets


# ---------------------------------------------------------------------------
# Seedance video generation
# ---------------------------------------------------------------------------

def build_seedance_prompt_seg1(characters, location_desc, segment, asset_paths):
    """Build Seedance prompt for Segment 1."""
    # Build image reference section
    img_refs = []
    ref_idx = 1
    ref_map = {}
    for name in characters:
        if name in asset_paths:
            img_refs.append(f"@image{ref_idx} as character {name}")
            ref_map[name] = f"@image{ref_idx}"
            ref_idx += 1
    if "scene-office" in asset_paths:
        img_refs.append(f"@image{ref_idx} as the office scene background")
        ref_map["scene"] = f"@image{ref_idx}"
        ref_idx += 1

    ref_text = ", ".join(img_refs) + ". "

    # Build timeline from parts
    timeline = []
    for num, text in segment["parts"]:
        # Remove dialogue tags for Seedance (it can't speak)
        clean = re.sub(r'\[.+?\]："(.+?)"', r'says "\1"', text)
        timeline.append(f"[Part {num}] {clean}")

    prompt = (
        f"{ref_text}\n"
        f"Physical state: {segment['physical_state']}\n"
        f"Camera: {segment['camera']}\n\n"
        + "\n".join(timeline)
        + "\n\nNo subtitles, no slow motion, no characters looking at camera. "
        "Natural speed movement and dialogue. 9:16 vertical format."
    )
    return prompt, ref_map


def build_seedance_prompt_seg2_extend(segment):
    """Build Seedance prompt for Segment 2 using Video Extension."""
    timeline = []
    for num, text in segment["parts"]:
        clean = re.sub(r'\[.+?\]："(.+?)"', r'says "\1"', text)
        timeline.append(f"[Part {num}] {clean}")

    prompt = (
        f"Extend @video1 by 15 seconds. "
        f"Continue the scene seamlessly. "
        f"Physical state at start: {segment['physical_state']}\n"
        f"Camera: {segment['camera']}\n\n"
        + "\n".join(timeline)
        + "\n\nMaintain exact same character appearances, clothing, and office setting. "
        "No subtitles, no slow motion, no characters looking at camera. "
        "Natural speed movement. 9:16 vertical format."
    )
    return prompt


def upload_to_tmpfiles(local_path: str) -> str:
    """Upload a local file to tmpfiles.org and return the direct download URL."""
    import requests
    print(f"  Uploading {local_path} to tmpfiles.org...")
    with open(local_path, "rb") as f:
        resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    # Convert page URL to direct download URL
    page_url = data["data"]["url"]  # e.g. http://tmpfiles.org/12345/file.mp4
    direct_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    print(f"  → Uploaded: {direct_url}")
    return direct_url


def call_seedance(seedance_script: str, ark_key: str, prompt: str, 
                  asset_paths: list, output_path: str, 
                  input_video: str = None, duration: int = 15):
    """Call seedance.py to generate video."""
    cmd = [
        "python3", seedance_script, "run",
        "--prompt", prompt,
        "--ratio", "9:16",
        "--duration", str(duration),
        "--out", output_path,
    ]

    if input_video:
        # Upload local video to get a public URL
        if os.path.isfile(input_video) and not input_video.startswith("http"):
            input_video = upload_to_tmpfiles(input_video)
        cmd.extend(["--video", input_video])

    for i, path in enumerate(asset_paths):
        cmd.extend(["--image", path])

    env = os.environ.copy()
    env["ARK_API_KEY"] = ark_key

    print(f"  Calling Seedance... (this may take 3-5 minutes)")
    print(f"  Prompt: {prompt[:200]}...")
    
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1200)
    
    if result.returncode == 0:
        print(f"  ✓ Video generated: {output_path}")
        return True
    else:
        print(f"  ✗ Seedance failed: {result.stderr[:500]}")
        return False


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_consistency(seg1_path: str, seg2_path: str, output_dir: str):
    """Generate a consistency evaluation report."""
    report = {
        "experiment": "EXP-V7-001",
        "mode": "video-extension",
        "segment1": seg1_path,
        "segment2": seg2_path,
        "evaluation": {
            "character_consistency": {"score": None, "notes": "Pending manual review"},
            "scene_consistency": {"score": None, "notes": "Pending manual review"},
            "camera_continuity": {"score": None, "notes": "Pending manual review"},
            "plot_continuity": {"score": None, "notes": "Pending manual review"},
        },
        "overall_score": None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    
    report_path = os.path.join(output_dir, "consistency-report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"  Evaluation template saved: {report_path}")
    return report_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="V7 Dual Segment Pipeline")
    parser.add_argument("--storyboard", required=True, help="Path to storyboard.md")
    parser.add_argument("--mode", choices=["video-extension", "first-frame-anchor", "hybrid"],
                        default="video-extension")
    parser.add_argument("--output-dir", default="output/")
    parser.add_argument("--skip-assets", action="store_true", help="Skip asset generation")
    parser.add_argument("--skip-video", action="store_true", help="Skip video generation")
    args = parser.parse_args()

    keys = load_keys()
    if not keys["gemini_key"]:
        print("ERROR: GEMINI_API_KEY not found")
        sys.exit(1)
    if not keys["ark_key"] and not args.skip_video:
        print("ERROR: ARK_API_KEY not found")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    assets_dir = os.path.join(args.output_dir, "assets")

    # Parse storyboard
    print("=" * 60)
    print(f"V7 Pipeline — Mode: {args.mode}")
    print("=" * 60)
    characters, location_desc, segments = parse_storyboard(args.storyboard)
    print(f"Parsed: {len(characters)} characters, {len(segments)} segments")

    # Generate assets
    asset_paths = {}
    if not args.skip_assets:
        print("\n--- Step 1: Generate Assets ---")
        asset_paths = generate_all_assets(keys["gemini_key"], characters, location_desc, assets_dir, base_url=keys.get("gemini_base_url"))
        print(f"Generated {len(asset_paths)} assets")
    else:
        # Load existing assets
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                name = f.replace(".webp", "").replace("char-", "")
                asset_paths[name] = os.path.join(assets_dir, f)

    if args.skip_video:
        print("\n--- Skipping video generation ---")
        # Save generation log
        log = {
            "experiment": "EXP-V7-001",
            "mode": args.mode,
            "storyboard": args.storyboard,
            "assets": asset_paths,
            "video_skipped": True,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        log_path = os.path.join(args.output_dir, "generation-log.json")
        with open(log_path, "w") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        print(f"Log saved: {log_path}")
        return

    if not keys["seedance_script"]:
        print("ERROR: seedance.py not found")
        sys.exit(1)

    # Generate Segment 1
    print("\n--- Step 2: Generate Segment 1 ---")
    seg1 = segments[0]
    seg1_prompt, ref_map = build_seedance_prompt_seg1(characters, location_desc, seg1, asset_paths)
    seg1_video = os.path.join(args.output_dir, "segment-01.mp4")
    seg1_images = [asset_paths[name] for name in characters if name in asset_paths]
    if "scene-office" in asset_paths:
        seg1_images.append(asset_paths["scene-office"])
    
    seg1_ok = call_seedance(
        keys["seedance_script"], keys["ark_key"],
        seg1_prompt, seg1_images, seg1_video
    )

    if not seg1_ok:
        print("Segment 1 generation failed. Aborting.")
        sys.exit(1)

    # Generate Segment 2
    print("\n--- Step 3: Generate Segment 2 ---")
    seg2 = segments[1]

    if args.mode == "video-extension":
        seg2_prompt = build_seedance_prompt_seg2_extend(seg2)
        seg2_video = os.path.join(args.output_dir, "segment-02.mp4")
        seg2_ok = call_seedance(
            keys["seedance_script"], keys["ark_key"],
            seg2_prompt, [], seg2_video,
            input_video=seg1_video
        )
    elif args.mode == "first-frame-anchor":
        # Extract last frame from seg1
        last_frame = os.path.join(args.output_dir, "seg1-last-frame.png")
        subprocess.run([
            "ffmpeg", "-sseof", "-0.1", "-i", seg1_video,
            "-frames:v", "1", "-y", last_frame
        ], capture_output=True)
        
        seg2_prompt = (
            f"@image1 as the first frame of this scene. "
            f"Continue the scene seamlessly from this exact moment. "
            + build_seedance_prompt_seg2_extend(seg2).replace("Extend @video1 by 15 seconds. ", "")
        )
        seg2_images = [last_frame]
        # Add character refs
        for name in characters:
            if name in asset_paths:
                seg2_images.append(asset_paths[name])
        
        seg2_video = os.path.join(args.output_dir, "segment-02.mp4")
        seg2_ok = call_seedance(
            keys["seedance_script"], keys["ark_key"],
            seg2_prompt, seg2_images, seg2_video
        )
    elif args.mode == "hybrid":
        # Extract last frame + use video extension + character refs
        last_frame = os.path.join(args.output_dir, "seg1-last-frame.png")
        subprocess.run([
            "ffmpeg", "-sseof", "-0.1", "-i", seg1_video,
            "-frames:v", "1", "-y", last_frame
        ], capture_output=True)
        
        seg2_prompt = (
            f"Extend @video1 by 15 seconds. "
            f"Maintain character appearance exactly consistent with reference images. "
            + build_seedance_prompt_seg2_extend(seg2).replace("Extend @video1 by 15 seconds. ", "")
        )
        seg2_images = []
        for name in characters:
            if name in asset_paths:
                seg2_images.append(asset_paths[name])
        
        seg2_video = os.path.join(args.output_dir, "segment-02.mp4")
        seg2_ok = call_seedance(
            keys["seedance_script"], keys["ark_key"],
            seg2_prompt, seg2_images, seg2_video,
            input_video=seg1_video
        )

    if not seg2_ok:
        print("Segment 2 generation failed.")
    
    # Concatenate
    if seg1_ok and seg2_ok:
        print("\n--- Step 4: Concatenate ---")
        concat_path = os.path.join(args.output_dir, "final-30s.mp4")
        concat_list = os.path.join(args.output_dir, "concat.txt")
        with open(concat_list, "w") as f:
            f.write(f"file '{os.path.abspath(seg1_video)}'\n")
            f.write(f"file '{os.path.abspath(seg2_video)}'\n")
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-c", "copy", "-y", concat_path
        ], capture_output=True)
        print(f"  ✓ Final video: {concat_path}")

    # Evaluate
    print("\n--- Step 5: Evaluation ---")
    evaluate_consistency(seg1_video, seg2_video, args.output_dir)

    # Save generation log
    log = {
        "experiment": "EXP-V7-001",
        "mode": args.mode,
        "storyboard": args.storyboard,
        "assets": asset_paths,
        "segment1_prompt": seg1_prompt if seg1_ok else None,
        "segment2_prompt": seg2_prompt if 'seg2_prompt' in dir() else None,
        "segment1_video": seg1_video if seg1_ok else None,
        "segment2_video": seg2_video if seg2_ok else None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = os.path.join(args.output_dir, "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\nGeneration log: {log_path}")
    print("Done!")


if __name__ == "__main__":
    main()
