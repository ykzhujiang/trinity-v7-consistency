#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "pillow>=10.0.0"]
# ///
"""
Gemini Character/Scene Image Generator — Concurrent batch generation.

Usage:
    python3 -u tools/gemini_chargen.py --specs specs.json --out-dir assets/
    python3 -u tools/gemini_chargen.py --name "陈磊" --desc "中国男性，28岁，短发微乱，黑框眼镜，灰色卫衣" --style anime --out assets/char-chenlei.webp
    python3 -u tools/gemini_chargen.py --help

Specs JSON format (for batch mode):
[
  {"name": "陈磊", "type": "character", "desc": "中国男性，28岁...", "style": "anime"},
  {"name": "office-night", "type": "scene", "desc": "深夜办公室...", "style": "anime"}
]
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

# Add parent for config_loader
sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_keys


def generate_one(gemini_key: str, base_url: str, prompt: str, output_path: str) -> dict:
    """Generate a single image. Returns {"path": ..., "ok": bool, "error": ...}."""
    from google import genai
    from google.genai import types

    kwargs = {"api_key": gemini_key}
    if base_url:
        # SDK adds /v1beta to path; strip it from base_url to avoid doubling
        clean_url = base_url.rstrip("/")
        for suffix in ["/v1beta", "/v1beta1", "/v1"]:
            if clean_url.endswith(suffix):
                clean_url = clean_url[:-len(suffix)]
                break
        kwargs["http_options"] = types.HttpOptions(base_url=clean_url)

    client = genai.Client(**kwargs)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        for part in response.candidates[0].content.parts:
            img_data = None
            # Method 1: inline_data (native Gemini)
            if part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("image/"):
                img_data = part.inline_data.data
            # Method 2: data URI in text (proxy returns markdown with base64)
            elif part.text and "data:image/" in part.text:
                import re, base64
                m = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=\s]+)', part.text)
                if m:
                    img_data = base64.b64decode(m.group(1))
            if img_data:
                from PIL import Image
                img = Image.open(BytesIO(img_data))
                if img.width > 600:
                    ratio = 600 / img.width
                    img = img.resize((600, int(img.height * ratio)), Image.LANCZOS)
                img.save(output_path, "WEBP", quality=75)
                size_kb = os.path.getsize(output_path) // 1024
                print(f"  ✓ {output_path} ({size_kb}KB)", flush=True)
                return {"path": output_path, "ok": True}
        return {"path": output_path, "ok": False, "error": "No image in response"}
    except Exception as e:
        return {"path": output_path, "ok": False, "error": str(e)}


def build_prompt(spec: dict) -> str:
    """Build Gemini prompt from a spec dict."""
    style = spec.get("style", "anime")
    typ = spec.get("type", "character")

    if style == "realistic":
        style_desc = "Professional DSLR photograph, photorealistic portrait"
        style_detail = "Professional DSLR photograph, 35mm lens, natural lighting, real human face and body. Photorealistic skin texture, real hair, real fabric. NOT anime, NOT 3D, NOT cartoon, NOT Pixar, NOT CG, NOT animated, NOT illustration."
    else:
        style_desc = "Anime-style"
        style_detail = "Semi-realistic anime illustration, soft studio lighting, clean background. High detail, vibrant colors, cinematic anime quality."

    desc = spec["desc"]

    if typ == "scene":
        # Detect indoor/outdoor from desc or explicit spec field
        location_tag = spec.get("location", "").upper()
        desc_upper = desc.upper()
        is_indoor = "[INDOOR]" in desc_upper or "INDOOR" in location_tag or any(kw in desc for kw in ["室内", "屋内", "房间", "办公", "餐厅", "厨房", "卧室", "客厅", "面馆", "酒吧", "大厅", "大堂"])
        is_outdoor = "[OUTDOOR]" in desc_upper or "OUTDOOR" in location_tag or any(kw in desc for kw in ["室外", "户外", "街", "路", "广场", "公园", "天台", "屋顶"])
        # Strip [INDOOR]/[OUTDOOR] tags from desc for cleaner prompt
        import re as _re
        clean_desc = _re.sub(r'\[INDOOR\]|\[OUTDOOR\]', '', desc, flags=_re.IGNORECASE).strip()
        
        if style == "realistic":
            if is_indoor:
                scene_style = "Interior DSLR photograph of a real indoor location. Natural indoor lighting, photorealistic textures, real-world environment. NOT 3D, NOT CG, NOT animated, NOT Pixar, NOT cartoon."
            elif is_outdoor:
                scene_style = "Exterior DSLR photograph of a real outdoor location. Natural outdoor lighting, photorealistic textures, real-world environment. NOT 3D, NOT CG, NOT animated, NOT Pixar, NOT cartoon."
            else:
                scene_style = "DSLR photograph of real location. Natural lighting, photorealistic textures, real-world environment. NOT 3D, NOT CG, NOT animated, NOT Pixar, NOT cartoon."
        else:
            if is_indoor:
                scene_style = "Anime-style interior establishing shot. Semi-realistic anime illustration, warm indoor lighting, cinematic quality."
            elif is_outdoor:
                scene_style = "Anime-style exterior establishing shot. Semi-realistic anime illustration, natural outdoor lighting, cinematic quality."
            else:
                scene_style = "Anime-style wide establishing shot. Semi-realistic anime illustration, warm lighting, cinematic quality."
        return f"{scene_style} 9:16 vertical format. {clean_desc}. No people in the scene."
    else:
        return (
            f"{style_desc} character portrait for production. "
            f"9:16 vertical format. The character is: {desc}. "
            f"{style_detail} "
            f"Character is looking slightly to the left (not at camera). Upper body visible."
        )


def main():
    parser = argparse.ArgumentParser(description="Gemini image generator (concurrent)")
    parser.add_argument("--specs", help="JSON file with batch specs")
    parser.add_argument("--name", help="Single asset name")
    parser.add_argument("--desc", help="Single asset description")
    parser.add_argument("--type", choices=["character", "scene"], default="character")
    parser.add_argument("--style", choices=["anime", "realistic"], default="anime")
    parser.add_argument("--out", help="Output path (single mode) or output dir (batch)")
    parser.add_argument("--out-dir", help="Output directory (batch mode)")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent requests")
    args = parser.parse_args()

    keys = load_keys()
    if not keys["gemini_key"]:
        print("ERROR: GEMINI_API_KEY not found", file=sys.stderr)
        sys.exit(1)

    # Build task list
    tasks = []
    out_dir = args.out_dir or (os.path.dirname(args.out) if args.out else "assets")
    os.makedirs(out_dir, exist_ok=True)

    if args.specs:
        with open(args.specs) as f:
            specs = json.load(f)
        for s in specs:
            prefix = "scene" if s.get("type") == "scene" else "char"
            name = s.get("name") or s.get("id", "unknown")
            out_file = s.get("out", f"{prefix}-{name}.webp")
            out_path = os.path.join(out_dir, out_file)
            prompt = s.get("prompt") or build_prompt(s)
            tasks.append((prompt, out_path, name))
    elif args.name and args.desc:
        out_path = args.out or os.path.join(out_dir, f"char-{args.name}.webp")
        spec = {"name": args.name, "desc": args.desc, "type": args.type, "style": args.style}
        tasks.append((build_prompt(spec), out_path, args.name))
    else:
        parser.print_help()
        sys.exit(1)

    print(f"Generating {len(tasks)} image(s) with concurrency={args.concurrency}...", flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {
            pool.submit(generate_one, keys["gemini_key"], keys.get("gemini_base_url"), prompt, path): name
            for prompt, path, name in tasks
        }
        for fut in as_completed(futures):
            name = futures[fut]
            r = fut.result()
            r["name"] = name
            results.append(r)
            if not r["ok"]:
                print(f"  ✗ {name}: {r.get('error')}", flush=True)

    # Summary
    ok = sum(1 for r in results if r["ok"])
    print(f"\nDone: {ok}/{len(results)} succeeded", flush=True)
    
    # Output manifest
    manifest = {r["name"]: r["path"] for r in results if r["ok"]}
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Manifest: {manifest_path}", flush=True)

    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
