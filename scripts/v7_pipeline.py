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
V7 N-Segment Pipeline — Consistency Research

Generates N-segment videos testing cross-segment consistency.
Seg1 is generated independently; Seg2..N extend from the previous segment.
Three modes:
  1. video-extension: SegN = Extend @video(N-1) by 15s
  2. first-frame-anchor: SegN uses last frame of Seg(N-1) as first frame
  3. hybrid: Combine video extension + character refs + first frame

V7-032 template: Seg2+ prompts include character reference images and copy
Seg1 character/scene descriptions verbatim for consistency.

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


def generate_all_assets(gemini_key: str, characters: dict, location_desc: str, output_dir: str, base_url=None, style: str = "anime"):
    """Generate character portraits and scene images."""
    os.makedirs(output_dir, exist_ok=True)
    assets = {}

    if style == "realistic":
        style_desc = "3D animated character portrait, Pixar/Disney quality"
        style_detail = "High-quality 3D animated character, like a Pixar or modern CG film. Stylized but detailed, with realistic proportions and expressive features. Warm cinematic lighting. NOT a photograph, clearly a 3D animated character."
    else:
        style_desc = "Anime-style"
        style_detail = "Semi-realistic anime illustration style, soft studio lighting, clean background. High detail, vibrant colors, cinematic anime quality."

    # Character portraits
    for name, desc in characters.items():
        path = os.path.join(output_dir, f"char-{name}.webp")
        prompt = (
            f"{style_desc} character portrait for production. "
            f"9:16 vertical format. The character is: {desc}. "
            f"{style_detail} "
            f"Character is looking slightly to the left (not at camera). "
            f"Upper body visible."
        )
        print(f"Generating character asset: {name}")
        if generate_asset(gemini_key, prompt, path, base_url=base_url):
            assets[name] = path

    # Scene
    scene_path = os.path.join(output_dir, "scene-office.webp")
    if style == "realistic":
        scene_style = "3D animated environment, Pixar/Disney quality CG scene. Warm cinematic lighting, detailed textures, clearly animated (not a photograph)."
    else:
        scene_style = "Anime-style wide establishing shot for animation. Semi-realistic anime illustration style, warm lighting, cinematic quality."
    prompt = (
        f"{scene_style} Modern office interior. "
        f"9:16 vertical format. {location_desc}. "
        f"No people in the scene. "
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
        "Natural speed movement and dialogue. 9:16 vertical format. "
        "Maintain identical generic modern Asian city skyline across all frames, no landmark buildings. "
        "Consistent warm indoor lighting, no change in outdoor sky color."
    )

    # Enforce prompt length constraint
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[:MAX_PROMPT_LENGTH - 3] + "..."

    return prompt, ref_map


MAX_PROMPT_LENGTH = 800


def build_seedance_prompt_seg_extend(segment, characters, asset_paths, seg1_desc=None):
    """Build Seedance prompt for Segment 2+ using Video Extension.

    V7-032 template: includes character reference images and copies Seg1 character
    description verbatim into continuation prompts.

    Returns (prompt, image_paths) where image_paths are the character ref images to pass via --image.
    """
    # Build character image refs
    img_refs = []
    img_paths = []
    ref_idx = 1
    for name in characters:
        if name in asset_paths:
            img_refs.append(f"@image{ref_idx} as character {name}")
            img_paths.append(asset_paths[name])
            ref_idx += 1

    ref_text = ", ".join(img_refs) + ". " if img_refs else ""

    # V7-032: copy Seg1 character description verbatim
    char_desc = ""
    if seg1_desc and seg1_desc.get("character_desc"):
        char_desc = f"Same {seg1_desc['character_desc']}. "
    scene_desc = ""
    if seg1_desc and seg1_desc.get("scene_desc"):
        scene_desc = f"Continuing in the same {seg1_desc['scene_desc']}. "

    timeline = []
    for num, text in segment["parts"]:
        clean = re.sub(r'\[.+?\]："(.+?)"', r'says "\1"', text)
        timeline.append(f"[Part {num}] {clean}")

    prompt = (
        f"Extend @video1 by 15 seconds. {ref_text}"
        f"{char_desc}{scene_desc}"
        f"Physical state: {segment['physical_state']} "
        f"Camera: {segment['camera']} "
        + " ".join(timeline)
        + " No subtitles, no slow motion. Natural speed. 9:16 vertical. "
        "Same characters, clothing, office setting, furniture, window view. "
        "Identical generic modern Asian city skyline. Consistent warm indoor lighting."
    )

    # Enforce prompt length constraint
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[:MAX_PROMPT_LENGTH - 3] + "..."

    return prompt, img_paths


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

def check_segment_audio(video_path: str, segment_label: str) -> bool:
    """Check that a segment video has audio using ffprobe. Returns True if audio is present."""
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=duration", "-of", "csv=p=0", video_path
    ], capture_output=True, text=True)
    audio_dur = float(result.stdout.strip()) if result.stdout.strip() else 0
    video_result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v",
        "-show_entries", "stream=duration", "-of", "csv=p=0", video_path
    ], capture_output=True, text=True)
    video_dur = float(video_result.stdout.strip()) if video_result.stdout.strip() else 0
    if audio_dur < video_dur * 0.9:
        print(f"  ⛔ AUDIO CHECK FAILED ({segment_label}): audio={audio_dur:.1f}s video={video_dur:.1f}s")
        return False
    else:
        print(f"  ✓ Audio OK ({segment_label}): audio={audio_dur:.1f}s video={video_dur:.1f}s")
        return True


def concat_segments(segment_videos: list, output_dir: str) -> str:
    """Concatenate N segment videos into a final video with proper re-encoding."""
    n = len(segment_videos)
    total_dur = n * 15
    concat_path = os.path.join(output_dir, f"final-{total_dur}s.mp4")
    concat_list = os.path.join(output_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for v in segment_videos:
            f.write(f"file '{os.path.abspath(v)}'\n")
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-y", concat_path
    ], capture_output=True)
    print(f"  ✓ Concatenated {n} segments → {concat_path}")
    return concat_path


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_consistency(segment_videos: list, output_dir: str):
    """Generate a consistency evaluation report for N segments."""
    report = {
        "experiment": os.path.basename(output_dir),
        "segments": segment_videos,
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
    parser = argparse.ArgumentParser(description="V7 N-Segment Pipeline — Consistency Research")
    parser.add_argument("--storyboard", required=True, help="Path to storyboard.md")
    parser.add_argument("--mode", choices=["video-extension", "first-frame-anchor", "hybrid"],
                        default="video-extension")
    parser.add_argument("--output-dir", default="output/")
    parser.add_argument("--style", choices=["anime", "realistic"], default="anime",
                        help="Visual style: anime or realistic")
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
        asset_paths = generate_all_assets(keys["gemini_key"], characters, location_desc, assets_dir, base_url=keys.get("gemini_base_url"), style=args.style)
        print(f"Generated {len(asset_paths)} assets")
    else:
        # Load existing assets
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                name = f.replace(".webp", "").replace("char-", "")
                asset_paths[name] = os.path.join(assets_dir, f)

    if args.skip_video:
        print("\n--- Skipping video generation ---")
        log = {
            "mode": args.mode,
            "storyboard": args.storyboard,
            "assets": asset_paths,
            "segments_count": len(segments),
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

    pipeline_start = time.time()
    segment_videos = []
    segment_prompts = []
    segment_timings = []

    # Build Seg1 description for V7-032 template reuse in Seg2+
    seg1_char_desc = "; ".join(
        f"{name}: {desc}" for name, desc in characters.items()
    )
    seg1_scene_desc = location_desc
    seg1_desc = {"character_desc": seg1_char_desc, "scene_desc": seg1_scene_desc}

    # --- Generate Segment 1 (independent) ---
    print(f"\n--- Step 2: Generate Segment 1 / {len(segments)} ---")
    seg1 = segments[0]
    seg1_start = time.time()
    seg1_prompt, ref_map = build_seedance_prompt_seg1(characters, location_desc, seg1, asset_paths)
    seg1_video = os.path.join(args.output_dir, "segment-01.mp4")
    seg1_images = [asset_paths[name] for name in characters if name in asset_paths]
    if "scene-office" in asset_paths:
        seg1_images.append(asset_paths["scene-office"])

    seg1_ok = call_seedance(
        keys["seedance_script"], keys["ark_key"],
        seg1_prompt, seg1_images, seg1_video
    )
    seg1_elapsed = time.time() - seg1_start

    if not seg1_ok:
        print("Segment 1 generation failed. Aborting.")
        sys.exit(1)

    segment_videos.append(seg1_video)
    segment_prompts.append(seg1_prompt)
    segment_timings.append(seg1_elapsed)

    # --- Generate Segments 2..N (serial, each extends previous) ---
    for i in range(1, len(segments)):
        seg = segments[i]
        seg_num = i + 1
        print(f"\n--- Step 2: Generate Segment {seg_num} / {len(segments)} ---")
        seg_start = time.time()
        prev_video = segment_videos[-1]
        seg_video = os.path.join(args.output_dir, f"segment-{seg_num:02d}.mp4")

        if args.mode == "video-extension":
            seg_prompt, seg_images = build_seedance_prompt_seg_extend(
                seg, characters, asset_paths, seg1_desc=seg1_desc
            )
            seg_ok = call_seedance(
                keys["seedance_script"], keys["ark_key"],
                seg_prompt, seg_images, seg_video,
                input_video=prev_video
            )
        elif args.mode == "first-frame-anchor":
            last_frame = os.path.join(args.output_dir, f"seg{i}-last-frame.png")
            subprocess.run([
                "ffmpeg", "-sseof", "-0.1", "-i", prev_video,
                "-frames:v", "1", "-y", last_frame
            ], capture_output=True)

            base_prompt, base_images = build_seedance_prompt_seg_extend(
                seg, characters, asset_paths, seg1_desc=seg1_desc
            )
            # Replace video extension ref with first-frame anchor
            seg_prompt = (
                f"@image1 as the first frame of this scene. "
                f"Continue the scene seamlessly from this exact moment. "
                + base_prompt.replace("Extend @video1 by 15 seconds. ", "")
            )
            seg_images = [last_frame] + base_images
            seg_ok = call_seedance(
                keys["seedance_script"], keys["ark_key"],
                seg_prompt, seg_images, seg_video
            )
        elif args.mode == "hybrid":
            last_frame = os.path.join(args.output_dir, f"seg{i}-last-frame.png")
            subprocess.run([
                "ffmpeg", "-sseof", "-0.1", "-i", prev_video,
                "-frames:v", "1", "-y", last_frame
            ], capture_output=True)

            base_prompt, base_images = build_seedance_prompt_seg_extend(
                seg, characters, asset_paths, seg1_desc=seg1_desc
            )
            seg_prompt = base_prompt.replace(
                "Extend @video1 by 15 seconds. ",
                "Extend @video1 by 15 seconds. Maintain character appearance exactly consistent with reference images. "
            )
            seg_images = base_images
            seg_ok = call_seedance(
                keys["seedance_script"], keys["ark_key"],
                seg_prompt, seg_images, seg_video,
                input_video=prev_video
            )

        seg_elapsed = time.time() - seg_start
        segment_prompts.append(seg_prompt)
        segment_timings.append(seg_elapsed)

        if not seg_ok:
            print(f"Segment {seg_num} generation failed. Stopping at segment {seg_num - 1}.")
            break

        segment_videos.append(seg_video)

    # --- Audio check per segment ---
    print(f"\n--- Step 3: Audio Check ({len(segment_videos)} segments) ---")
    for idx, v in enumerate(segment_videos):
        check_segment_audio(v, f"Segment {idx + 1}")

    # --- Concatenate all segments ---
    if len(segment_videos) >= 2:
        print(f"\n--- Step 4: Concatenate {len(segment_videos)} Segments ---")
        concat_path = concat_segments(segment_videos, args.output_dir)

        # Final audio check on concatenated video
        check_segment_audio(concat_path, "Final concatenated")
    elif len(segment_videos) == 1:
        print("\n--- Only 1 segment generated, skipping concat ---")
        concat_path = segment_videos[0]

    # --- Evaluate ---
    print("\n--- Step 5: Evaluation ---")
    evaluate_consistency(segment_videos, args.output_dir)

    # --- Save generation log ---
    pipeline_elapsed = time.time() - pipeline_start
    log = {
        "mode": args.mode,
        "style": args.style,
        "storyboard": args.storyboard,
        "segments_count": len(segments),
        "segments_generated": len(segment_videos),
        "assets": asset_paths,
        "segments": [
            {
                "number": idx + 1,
                "prompt": segment_prompts[idx] if idx < len(segment_prompts) else None,
                "prompt_length": len(segment_prompts[idx]) if idx < len(segment_prompts) else None,
                "video": segment_videos[idx] if idx < len(segment_videos) else None,
                "generation_time_s": round(segment_timings[idx], 1) if idx < len(segment_timings) else None,
            }
            for idx in range(len(segment_prompts))
        ],
        "total_time_s": round(pipeline_elapsed, 1),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    log_path = os.path.join(args.output_dir, "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\nGeneration log: {log_path}")
    print(f"Total time: {pipeline_elapsed:.0f}s")
    print("Done!")


if __name__ == "__main__":
    main()
