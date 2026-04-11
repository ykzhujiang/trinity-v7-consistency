#!/usr/bin/env python3 -u
"""
EXP-V7-048~051 Batch Runner — 4 3D Style Comparison (Low Complexity)
H-131: 3D animation styles have better physical consistency than realistic

Uses modular tools: gemini_chargen → ark_asset_upload → seedance_gen → ffmpeg_concat
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
TOOLS = REPO / "tools"
EXP_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(TOOLS))
from config_loader import load_keys

# ============================================================
# Experiment definitions
# ============================================================

EXPERIMENTS = {
    "v7-048-pixar": {
        "id": "EXP-V7-048",
        "style_name": "Pixar/Disney",
        "style_prefix": "Pixar-quality 3D animation, soft ambient lighting, Disney character design, smooth subsurface scattering skin, large expressive eyes, stylized proportions",
        "character": {
            "name": "小李-pixar",
            "desc": "25岁中国男性程序员，圆脸，黑色短发蓬松，大眼睛，穿灰色卫衣+牛仔裤，背微驼",
            "en": "25-year-old Chinese male programmer, round face, fluffy short black hair, large expressive eyes, wearing grey hoodie and jeans, slightly hunched posture"
        },
        "scene": {
            "name": "办公室-pixar",
            "desc": "[INDOOR] 小型开放式办公室，夜晚，只有一个工位台灯亮着，27寸显示器发蓝光，桌上有咖啡杯和零食包装袋，窗外城市夜景模糊可见",
            "en": "Small open-plan office at night, only one desk lamp on, 27-inch monitor glowing blue, coffee cup and snack wrappers on desk, blurred city night view through window"
        },
        "segments": [
            {
                "action": "小李疲惫地敲键盘，揉眼睛，喝了口咖啡，皱眉看屏幕上的代码报错",
                "en": "Xiaoli tiredly types on keyboard, rubs his eyes, takes a sip of coffee, frowns at code error on screen"
            },
            {
                "action": "继续调试，突然屏幕变绿（编译通过），先愣住，然后慢慢露出笑容，小声说'终于过了'",
                "en": "Continues debugging, suddenly screen turns green (compilation passed), freezes for a moment, then slowly smiles, quietly says 'finally passed'"
            },
            {
                "action": "站起来伸懒腰，拿起手机看消息，开心地握拳，收拾东西准备回家",
                "en": "Stands up and stretches, picks up phone to read message, happily clenches fist, packs up things to leave"
            },
        ],
        "dialogue": [
            "",  # seg1: no dialogue
            "终于过了……",  # seg2
            "",  # seg3: no dialogue
        ],
    },
    "v7-049-gamecg": {
        "id": "EXP-V7-049",
        "style_name": "Game CG (Unreal)",
        "style_prefix": "AAA game cinematic, Unreal Engine 5 quality, ray-traced global illumination, photorealistic materials, cinematic depth of field, game cutscene style",
        "character": {
            "name": "小雨-gamecg",
            "desc": "28岁中国女性，长直黑发过肩，柳叶眉，穿米白色毛衣+浅蓝牛仔裤，戴银色手链",
            "en": "28-year-old Chinese woman, long straight black hair past shoulders, willow-leaf eyebrows, wearing cream white sweater and light blue jeans, silver bracelet"
        },
        "scene": {
            "name": "咖啡店-gamecg",
            "desc": "[INDOOR] 精品咖啡店靠窗卡座，暖黄色吊灯，木质桌面上放着拿铁和翻开的书，窗外雨天街景，玻璃上有雨滴",
            "en": "Boutique coffee shop window booth, warm yellow pendant lamp, wooden table with latte and open book, rainy street view outside, raindrops on glass"
        },
        "segments": [
            {
                "action": "小雨坐在卡座，双手捧咖啡杯取暖，看着窗外的雨，表情略带思念",
                "en": "Xiaoyu sits in booth, holds coffee cup with both hands for warmth, gazes at rain outside window, expression slightly wistful"
            },
            {
                "action": "放下咖啡，低头翻书页，偶尔抬头看门口方向，手指无意识地转手链",
                "en": "Puts down coffee, looks down turning book pages, occasionally glances toward entrance, fingers unconsciously fidgeting with bracelet"
            },
            {
                "action": "手机震动，拿起看消息，嘴角微微上扬，放下手机继续看书，表情变得安心",
                "en": "Phone vibrates on table, picks up and reads message, corners of mouth slightly curl up, puts phone down and continues reading, expression becomes peaceful"
            },
        ],
        "dialogue": ["", "", ""],  # no spoken dialogue
    },
    "v7-050-celshaded": {
        "id": "EXP-V7-050",
        "style_name": "Cel-shaded (Genshin/Zelda)",
        "style_prefix": "Cel-shaded 3D animation, Genshin Impact art style, clean outlines, flat shading with vibrant colors, anime-influenced 3D, stylized environment",
        "character": {
            "name": "阿明-celshaded",
            "desc": "22岁中国男性，翘起的黑色短发（微卡通化），圆润脸型，大眼睛，穿橙色T恤+格子睡裤，套白色围裙",
            "en": "22-year-old Chinese male, spiky short black hair (slightly cartoonish), round face, large eyes, wearing orange T-shirt and plaid pajama pants, white apron"
        },
        "scene": {
            "name": "厨房-celshaded",
            "desc": "[INDOOR] 明亮的小厨房，阳光从窗户照进来，白色橱柜，浅木色台面，台面有鸡蛋牛奶面包，墙上可爱冰箱贴，整体色调暖亮",
            "en": "Bright small kitchen, sunlight streaming through window, white cabinets, light wood countertop with eggs milk and bread, cute fridge magnets on wall, warm bright color tone"
        },
        "segments": [
            {
                "action": "阿明从冰箱拿出鸡蛋和牛奶放台面上，打开燃气灶，从橱柜拿出平底锅",
                "en": "Aming takes eggs and milk from fridge places on counter, turns on gas stove, takes frying pan from cabinet"
            },
            {
                "action": "打鸡蛋入锅，蛋壳掉一小块进去，手忙脚乱用筷子捞蛋壳，嘟囔'每次都这样'",
                "en": "Cracks egg into pan, a small piece of shell falls in, frantically uses chopsticks to fish out shell, mumbles 'every time'"
            },
            {
                "action": "煎蛋完成装盘，倒杯牛奶，端到桌上坐下，看着自己作品满意地点头，开吃",
                "en": "Finishes fried egg onto plate, pours glass of milk, carries to table sits down, looks at his creation nods satisfiedly, starts eating"
            },
        ],
        "dialogue": ["", "每次都这样", ""],
    },
    "v7-051-jpn3d": {
        "id": "EXP-V7-051",
        "style_name": "Japanese 3D (Shinkai)",
        "style_prefix": "Japanese 3D anime, Makoto Shinkai lighting quality, CG-anime hybrid, detailed atmospheric effects, soft bokeh background, anime character proportions with 3D rendering",
        "character": {
            "name": "小天-jpn3d",
            "desc": "17岁中国男高中生，黑色碎发被风吹动，略瘦，穿白色校服衬衫（袖子卷到手肘）+深蓝校裤，斜挎帆布书包",
            "en": "17-year-old Chinese male high school student, black layered hair blown by wind, slim build, wearing white school uniform shirt (sleeves rolled to elbows) and dark blue school pants, canvas messenger bag"
        },
        "scene": {
            "name": "天台-jpn3d",
            "desc": "[OUTDOOR] 学校教学楼天台，四周铁栏杆，灰色水泥地面，远处城市天际线，天空橙红色落日+云层渐变，傍晚逆光",
            "en": "School building rooftop, iron railings around perimeter, grey concrete floor, city skyline in distance, orange-red sunset with gradient clouds, evening backlight"
        },
        "segments": [
            {
                "action": "小天推开天台门走出来，阳光照脸微眯眼，走到栏杆前，把书包放地上",
                "en": "Xiaotian pushes open rooftop door walks out, sunlight hits face squints slightly, walks to railing, puts bag on ground"
            },
            {
                "action": "双手搭在栏杆上，看远处落日，风吹动头发和衬衫，深吸一口气闭上眼",
                "en": "Rests both hands on railing, gazes at distant sunset, wind blows hair and shirt, takes deep breath and closes eyes"
            },
            {
                "action": "睁开眼，掏出耳机戴上，拿起书包，转身走向楼梯门，回头看一眼落日微笑，推门离开",
                "en": "Opens eyes, takes out earphones puts them on, picks up bag, turns to walk toward stairway door, glances back at sunset smiles, pushes door and leaves"
            },
        ],
        "dialogue": ["", "", ""],
    },
}

# ============================================================
# Pipeline Steps
# ============================================================

def step1_generate_assets(exp_key: str, exp: dict, keys: dict):
    """Generate character + scene reference images via gemini_chargen."""
    import subprocess
    exp_dir = EXP_DIR / exp_key
    assets_dir = exp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    specs = [
        {
            "name": exp["character"]["name"],
            "type": "character",
            "desc": f"{exp['character']['desc']}，{exp['style_name']}风格，{exp['style_prefix'][:80]}",
            "style": "anime"  # gemini_chargen uses "anime" for non-realistic
        },
        {
            "name": exp["scene"]["name"],
            "type": "scene",
            "desc": f"{exp['scene']['desc']}，{exp['style_name']}风格",
            "style": "anime"
        },
    ]
    specs_path = exp_dir / "asset_specs.json"
    with open(specs_path, "w") as f:
        json.dump(specs, f, ensure_ascii=False, indent=2)

    cmd = [
        "python3", "-u", str(TOOLS / "gemini_chargen.py"),
        "--specs", str(specs_path),
        "--out-dir", str(assets_dir),
    ]
    print(f"\n{'='*60}", flush=True)
    print(f"[{exp_key}] Step 1: Generating assets...", flush=True)
    r = subprocess.run(cmd, capture_output=False, text=True, timeout=300)
    if r.returncode != 0:
        print(f"[{exp_key}] ⚠️ Asset generation returned {r.returncode}", flush=True)
        return False

    # Check outputs exist
    generated = list(assets_dir.glob("*.webp")) + list(assets_dir.glob("*.jpg")) + list(assets_dir.glob("*.png"))
    print(f"[{exp_key}] Generated {len(generated)} asset images", flush=True)
    return len(generated) >= 2


def step2_upload_assets(exp_key: str, exp: dict, keys: dict):
    """Upload assets to Volcano Engine and get asset:// URIs."""
    import subprocess
    exp_dir = EXP_DIR / exp_key
    assets_dir = exp_dir / "assets"

    images = sorted(assets_dir.glob("*.webp")) + sorted(assets_dir.glob("*.jpg")) + sorted(assets_dir.glob("*.png"))
    if not images:
        print(f"[{exp_key}] No images to upload!", flush=True)
        return {}

    img_args = []
    name_args = []
    for img in images:
        img_args.extend(["--images", str(img)])
        name_args.extend(["--names", img.stem])

    cmd = [
        "python3", "-u", str(TOOLS / "ark_asset_upload.py"),
        *img_args, *name_args,
        "--group-name", exp_key,
    ]
    print(f"\n[{exp_key}] Step 2: Uploading {len(images)} assets to Volcano...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    print(r.stdout, flush=True)
    if r.stderr:
        print(r.stderr, flush=True)

    # Parse asset IDs from output
    asset_ids = {}
    for line in r.stdout.split("\n"):
        if "asset://" in line:
            # Try to parse "name: asset://xxx" format
            parts = line.split("asset://")
            if len(parts) == 2:
                asset_id = "asset://" + parts[1].strip().split()[0].strip('"').strip("'")
                # Try to get name from before the colon
                name_part = parts[0].strip().rstrip(":").rstrip().split()[-1] if parts[0].strip() else "unknown"
                asset_ids[name_part] = asset_id
                print(f"  → {name_part}: {asset_id}", flush=True)

    # Save
    ids_path = exp_dir / "asset_ids.json"
    with open(ids_path, "w") as f:
        json.dump(asset_ids, f, ensure_ascii=False, indent=2)

    return asset_ids


def build_seedance_prompt(exp: dict, seg_idx: int, asset_ids: dict) -> str:
    """Build Seedance prompt for a segment. ≤800 chars."""
    seg = exp["segments"][seg_idx]
    style = exp["style_prefix"]
    char_en = exp["character"]["en"]
    scene_en = exp["scene"]["en"]
    action_en = seg["en"]
    dialogue = exp["dialogue"][seg_idx] if seg_idx < len(exp["dialogue"]) else ""

    # For seg1: include full scene + character + action
    # For seg2/3: action continuation (extend mode)
    if seg_idx == 0:
        prompt = (
            f"{style}. "
            f"{scene_en}. "
            f"A {char_en} — {action_en}. "
            f"Camera: medium shot, slight side angle, fixed position. "
            f"Normal speed movement, natural pacing."
        )
    else:
        prompt = (
            f"Continuing the scene — {action_en}. "
            f"Same character, same location, consistent lighting and style. "
            f"Normal speed movement, natural pacing."
        )

    if dialogue:
        prompt += f' Character speaks in Mandarin Chinese: "{dialogue}"'

    # Append safety suffix
    prompt += " No subtitles, no text overlay, no slow motion, character does not face camera directly."

    # Truncate to 800 chars
    if len(prompt) > 800:
        prompt = prompt[:797] + "..."

    return prompt


def step3_generate_video(exp_key: str, exp: dict, keys: dict, asset_ids: dict):
    """Generate 3 segments via Seedance 2.0 extend chain."""
    import subprocess
    exp_dir = EXP_DIR / exp_key
    output_dir = exp_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Find character and scene asset URIs
    char_asset = None
    scene_asset = None
    for name, uri in asset_ids.items():
        if "char" in name.lower() or exp["character"]["name"].split("-")[0] in name:
            char_asset = uri
        elif "scene" in name.lower() or exp["scene"]["name"].split("-")[0] in name:
            scene_asset = uri

    # Seg1: image-to-video
    seg1_prompt = build_seedance_prompt(exp, 0, asset_ids)
    print(f"\n[{exp_key}] Step 3: Segment 1 (image-to-video)", flush=True)
    print(f"  Prompt ({len(seg1_prompt)} chars): {seg1_prompt[:100]}...", flush=True)

    # Find asset images for reference
    assets_dir = exp_dir / "assets"
    ref_images = sorted(str(p) for p in assets_dir.glob("*") if p.suffix in (".webp", ".jpg", ".png"))

    seg1_path = str(output_dir / "seg1.mp4")
    seg1_batch = {
        "prompt": seg1_prompt,
        "images": ref_images[:2],  # char + scene
        "out": seg1_path,
    }
    # Save batch spec for logging
    with open(exp_dir / "seg1_batch.json", "w") as f:
        json.dump(seg1_batch, f, ensure_ascii=False, indent=2)

    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--prompt", seg1_prompt,
        "--images", *ref_images[:2],
        "--out", seg1_path,
        "--ratio", "9:16",
    ]
    r = subprocess.run(cmd, capture_output=False, text=True, timeout=1200)
    if not Path(seg1_path).exists():
        print(f"[{exp_key}] ❌ Seg1 failed!", flush=True)
        return False

    # Seg2: video extension
    seg2_prompt = build_seedance_prompt(exp, 1, asset_ids)
    print(f"\n[{exp_key}] Segment 2 (extend from seg1)", flush=True)
    seg2_path = str(output_dir / "seg2.mp4")
    with open(exp_dir / "seg2_batch.json", "w") as f:
        json.dump({"prompt": seg2_prompt, "video": seg1_path, "out": seg2_path}, f, ensure_ascii=False, indent=2)

    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--prompt", seg2_prompt,
        "--video", seg1_path,
        "--out", seg2_path,
        "--ratio", "9:16",
    ]
    r = subprocess.run(cmd, capture_output=False, text=True, timeout=1200)
    if not Path(seg2_path).exists():
        print(f"[{exp_key}] ❌ Seg2 failed!", flush=True)
        return False

    # Seg3: video extension from seg2
    seg3_prompt = build_seedance_prompt(exp, 2, asset_ids)
    print(f"\n[{exp_key}] Segment 3 (extend from seg2)", flush=True)
    seg3_path = str(output_dir / "seg3.mp4")
    with open(exp_dir / "seg3_batch.json", "w") as f:
        json.dump({"prompt": seg3_prompt, "video": seg2_path, "out": seg3_path}, f, ensure_ascii=False, indent=2)

    cmd = [
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--prompt", seg3_prompt,
        "--video", seg2_path,
        "--out", seg3_path,
        "--ratio", "9:16",
    ]
    r = subprocess.run(cmd, capture_output=False, text=True, timeout=1200)
    if not Path(seg3_path).exists():
        print(f"[{exp_key}] ❌ Seg3 failed!", flush=True)
        return False

    return True


def step4_concat(exp_key: str):
    """Concatenate 3 segments + audio check."""
    import subprocess
    exp_dir = EXP_DIR / exp_key
    output_dir = exp_dir / "output"
    segs = [str(output_dir / f"seg{i}.mp4") for i in range(1, 4)]
    final = str(output_dir / "final.mp4")

    cmd = [
        "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
        "--inputs", *segs,
        "--out", final,
        "--check-audio",
    ]
    print(f"\n[{exp_key}] Step 4: Concatenating...", flush=True)
    r = subprocess.run(cmd, capture_output=False, text=True, timeout=120)
    return Path(final).exists()


def run_single_experiment(exp_key: str, exp: dict, keys: dict) -> dict:
    """Run full pipeline for one experiment."""
    result = {"id": exp["id"], "key": exp_key, "style": exp["style_name"]}
    t0 = time.time()

    try:
        # Step 1: Generate assets
        ok = step1_generate_assets(exp_key, exp, keys)
        if not ok:
            result["status"] = "FAILED_ASSETS"
            return result

        # Step 2: Upload assets
        asset_ids = step2_upload_assets(exp_key, exp, keys)
        if not asset_ids:
            result["status"] = "FAILED_UPLOAD"
            return result

        # Step 3: Generate video (3 segments sequential — extend chain)
        ok = step3_generate_video(exp_key, exp, keys, asset_ids)
        if not ok:
            result["status"] = "FAILED_VIDEO"
            return result

        # Step 4: Concat
        ok = step4_concat(exp_key)
        if not ok:
            result["status"] = "FAILED_CONCAT"
            return result

        result["status"] = "SUCCESS"
        result["duration_s"] = round(time.time() - t0, 1)
        result["final_video"] = str(EXP_DIR / exp_key / "output" / "final.mp4")

    except Exception as e:
        result["status"] = f"ERROR: {e}"
        result["duration_s"] = round(time.time() - t0, 1)

    return result


def main():
    keys = load_keys()
    # Set env vars for tools
    os.environ.setdefault("ARK_API_KEY", keys.get("ark_key") or "")
    os.environ.setdefault("GEMINI_API_KEY", keys.get("gemini_key") or "")
    if keys.get("gemini_base_url"):
        os.environ.setdefault("GEMINI_BASE_URL", keys["gemini_base_url"])
    # Volcano keys from openclaw.json
    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        try:
            sv = cfg["skills"]["entries"]["seedance-video"]["env"]
            os.environ.setdefault("VOLCANO_ACCESS_KEY", sv.get("VOLCANO_ACCESS_KEY", ""))
            os.environ.setdefault("VOLCANO_ACCESS_SECRET", sv.get("VOLCANO_ACCESS_SECRET", ""))
        except (KeyError, TypeError):
            pass

    print("=" * 60, flush=True)
    print("EXP-V7-048~051: 3D Style Horizontal Comparison", flush=True)
    print(f"4 styles × 3 segments × low complexity", flush=True)
    print("=" * 60, flush=True)

    # Priority order per Controller spec:
    # 1. V7-050 (Cel-shaded) — 朱江 known preference
    # 2. V7-048 (Pixar) — most universal
    # 3. V7-051 (Japanese 3D) — Shinkai lighting
    # 4. V7-049 (Game CG) — closest to realistic
    priority_order = ["v7-050-celshaded", "v7-048-pixar", "v7-051-jpn3d", "v7-049-gamecg"]

    # Step 1+2 can be parallelized across experiments (asset gen + upload)
    print("\n=== Phase 1: Generate + Upload Assets (parallel) ===", flush=True)
    asset_results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for key in priority_order:
            exp = EXPERIMENTS[key]
            exp_dir = EXP_DIR / key
            exp_dir.mkdir(parents=True, exist_ok=True)
            futures[pool.submit(step1_generate_assets, key, exp, keys)] = key

        for fut in as_completed(futures):
            key = futures[fut]
            try:
                ok = fut.result()
                asset_results[key] = ok
                print(f"  Asset gen {'✅' if ok else '❌'}: {key}", flush=True)
            except Exception as e:
                asset_results[key] = False
                print(f"  Asset gen ❌: {key} — {e}", flush=True)

    # Upload assets (parallel)
    upload_results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for key in priority_order:
            if asset_results.get(key):
                futures[pool.submit(step2_upload_assets, key, EXPERIMENTS[key], keys)] = key

        for fut in as_completed(futures):
            key = futures[fut]
            try:
                ids = fut.result()
                upload_results[key] = ids
                print(f"  Upload {'✅' if ids else '❌'}: {key} ({len(ids)} assets)", flush=True)
            except Exception as e:
                upload_results[key] = {}
                print(f"  Upload ❌: {key} — {e}", flush=True)

    # Step 3+4: Video generation — Seg1 can be parallel across experiments,
    # but Seg2 depends on Seg1, Seg3 depends on Seg2 (extend chain).
    # Strategy: Run Seg1 for all 4 in parallel, then Seg2 for all 4, then Seg3.
    print("\n=== Phase 2: Video Generation (seg-level parallel) ===", flush=True)

    active_exps = [k for k in priority_order if upload_results.get(k)]
    results = []

    for key in active_exps:
        print(f"\n{'='*60}", flush=True)
        print(f"Running full extend chain for {key}...", flush=True)
        result = {"id": EXPERIMENTS[key]["id"], "key": key, "style": EXPERIMENTS[key]["style_name"]}
        t0 = time.time()

        ok = step3_generate_video(key, EXPERIMENTS[key], keys, upload_results[key])
        if ok:
            ok = step4_concat(key)

        result["status"] = "SUCCESS" if ok else "FAILED"
        result["duration_s"] = round(time.time() - t0, 1)
        if ok:
            result["final_video"] = str(EXP_DIR / key / "output" / "final.mp4")
        results.append(result)
        print(f"  → {key}: {result['status']} ({result['duration_s']}s)", flush=True)

    # Save summary
    summary_path = EXP_DIR / "batch_results.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}", flush=True)
    print("SUMMARY:", flush=True)
    for r in results:
        print(f"  {r['key']}: {r['status']} ({r.get('duration_s', '?')}s)", flush=True)
    print(f"\nResults saved to {summary_path}", flush=True)


if __name__ == "__main__":
    main()
