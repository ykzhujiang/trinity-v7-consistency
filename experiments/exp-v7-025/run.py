#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "pillow>=10.0.0", "requests>=2.28.0"]
# ///
"""
EXP-V7-025: 同场景双人双Segment一致性测试
Thin runner — uses modular tools, no pipeline code duplication.
Usage: python3 -u experiments/exp-v7-025/run.py [--skip-assets] [--skip-video] [--style anime|realistic|both]
"""

import json, os, subprocess, sys, time, argparse
from pathlib import Path

BASE = Path.home() / "trinity-v7-consistency"
EXP = BASE / "experiments" / "exp-v7-025"
TOOLS = BASE / "tools"

# ── Characters ──
CHAR_A = (
    "中国男性，30岁，175cm，黑色短发，偏瘦面容，小胡茬，穿灰色卫衣和黑色运动裤。"
    "神情有点疲惫但眼神坚定。"
)

CHAR_B = (
    "中国女性，28岁，165cm，黑色马尾辫，清秀面容，穿白色T恤外面套深蓝色牛仔外套，牛仔裤。"
    "表情干练利落，嘴角常带一点笑意。"
)

SCENE = (
    "现代创业公司办公室深夜。暖黄色台灯光照亮两个紧挨的工位，各有一台双屏显示器。"
    "桌上有纸杯咖啡（一个空的一个半满）、外卖盒残余、缠绕的充电线、几张便签纸。"
    "周围工位漆黑。远处落地窗外是城市暖色夜景灯光。整体暖黄色调。"
    "Warm yellow desk lamp lighting, warm color temperature. No cold blue tones."
)

# ── Seedance Prompts ──
SEG1_PROMPT = """Physical state: 李昊(A) sits in office chair at LEFT workstation, hands resting near keyboard, leaning back. 苏晴(B) sits at RIGHT workstation facing her own monitor. Two coffee cups on desk (A's is empty). Warm yellow desk lamp light. Dark office around them, warm city lights through distant window.

[Part 1] Medium two-shot from front. {style_a} male 30yo with short black hair, thin face, slight stubble, wearing gray hoodie and black sweatpants sits on LEFT. {style_b} female 28yo with black ponytail, clean features, wearing white t-shirt under dark blue denim jacket sits on RIGHT. A stares at monitor showing red error code, lets out long sigh, pushes himself backward with both hands on desk edge. Chair rolls slightly. B glances sideways at him. A says "完了…这个支付接口又崩了…第四次了…"

[Part 2] Medium close-up on B from slightly right. B picks up her coffee cup with right hand, takes sip, then reaches left hand to grab a second full coffee cup from desk. She turns chair toward A, extends the cup to him. She says "别急，先喝口咖啡，我看看。"

[Part 3] Over-the-shoulder from behind A, facing B. B rolls her chair to A's desk, leans forward to look at A's screen. Her left hand points at a line of code on screen. Eyes narrow studying. A holds coffee with both hands watching her. No dialogue. Keyboard click sounds as B scrolls.

[Part 4] Medium two-shot from front. B taps Enter key once. Screen flashes from red to green success. A's jaw drops, eyes widen. B leans back in chair, crosses arms with satisfied smirk. A stares at screen then at B. A says "…就…就这样？一行就修好了？" Then 1 second silence.

No subtitles, no slow motion, no character looking at camera. Normal speed movement and natural pacing. 9:16 vertical. Warm indoor lighting throughout, absolutely no cold blue tones. A always on LEFT of frame, B always on RIGHT."""

SEG2_PROMPT = """Extend @video1 by 15 seconds. Continue seamlessly in the SAME office with SAME warm yellow desk lamp lighting.

Physical state: 同一间办公室。李昊(A, LEFT, gray hoodie, short black hair, stubble) sits holding coffee cup. 苏晴(B, RIGHT, ponytail, white T + denim jacket) sits at A's desk with arms crossed leaning on chair back. Monitor shows green success.

[Part 1] Medium shot from front. A puts coffee cup down with right hand, stands up, stretches both arms high above head with fingers interlocked. Twists torso left then right. He says "你怎么每次都能一下找到问题…我debug四个小时白折腾了…"

[Part 2] Close-up on B, warm light on face. B tilts head slightly, smiles showing teeth, right index finger points at A's screen. She says "因为这个bug上次你也写过一模一样的。" Eyebrows rise teasingly.

[Part 3] Medium two-shot from slightly left. A freezes mid-stretch, slowly lowers arms. Face turns slightly red, mouth forms exaggerated O shape. Covers face with both palms. He says "不是吧…一模一样的？我以为我修过了…"

[Part 4] Medium-wide two-shot, warm backlight from desk lamp. B reaches right hand and pats A's left shoulder twice. Both burst into laughter. A drops hands from face shaking head. B's head tilts back laughing. No dialogue. Office ambient hum plus laughter. 1 second silence at end.

Maintain EXACT same character appearances, clothing, and office setting as segment 1. A always on LEFT, B always on RIGHT. No subtitles, no slow motion, no character looking at camera. Normal speed. 9:16 vertical. Same warm yellow lighting."""


def write_asset_specs(style: str, out_dir: str):
    style_prefix = "Anime-style " if style == "anime" else ""
    specs = [
        {"name": f"李昊-{style}", "type": "character",
         "desc": f"{style_prefix}{CHAR_A}", "style": style},
        {"name": f"苏晴-{style}", "type": "character",
         "desc": f"{style_prefix}{CHAR_B}", "style": style},
        {"name": f"office-night-{style}", "type": "scene",
         "desc": f"{style_prefix}{SCENE}", "style": style},
    ]
    path = os.path.join(out_dir, f"specs-{style}.json")
    with open(path, "w") as f:
        json.dump(specs, f, indent=2, ensure_ascii=False)
    return path


def run_tool(args, timeout=1800):
    print(f"\n▶ {' '.join(args[:5])}...", flush=True)
    return subprocess.run(args, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description="EXP-V7-025 runner")
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-video", action="store_true")
    parser.add_argument("--style", choices=["anime", "realistic", "both"], default="both")
    args = parser.parse_args()

    styles = ["anime", "realistic"] if args.style == "both" else [args.style]
    assets_dir = str(EXP / "output" / "assets")
    os.makedirs(assets_dir, exist_ok=True)

    log = {
        "experiment": "EXP-V7-025",
        "hypothesis": "H-357: same-scene dual-character → highest cross-segment consistency",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "styles": styles,
        "steps": [],
    }

    # ── Step 1: Assets ──
    if not args.skip_assets:
        for style in styles:
            spec_path = write_asset_specs(style, assets_dir)
            r = run_tool([
                "python3", "-u", str(TOOLS / "gemini_chargen.py"),
                "--specs", spec_path,
                "--out-dir", assets_dir,
                "--concurrency", "3",
            ])
            log["steps"].append({"step": f"assets-{style}", "ok": r.returncode == 0})

    if args.skip_video:
        print("\n⏭ Skipping video generation", flush=True)
        with open(str(EXP / "output" / "generation-log.json"), "w") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        return

    # ── Step 2: Seg1 (anime + realistic concurrent) ──
    seg1_batch = []
    for style in styles:
        char_a = os.path.join(assets_dir, f"char-李昊-{style}.webp")
        char_b = os.path.join(assets_dir, f"char-苏晴-{style}.webp")
        scene_ref = os.path.join(assets_dir, f"scene-office-night-{style}.webp")
        style_a = "Chinese" if style == "realistic" else "Anime-style Chinese"
        style_b = "Chinese" if style == "realistic" else "Anime-style Chinese"
        prompt = SEG1_PROMPT.format(style_a=style_a, style_b=style_b)
        images = [p for p in [char_a, char_b, scene_ref] if os.path.exists(p)]
        seg1_batch.append({
            "id": f"{style}-seg1",
            "prompt": prompt,
            "images": images,
            "out": f"{style}-seg1.mp4",
        })

    batch_path = str(EXP / "output" / "seg1-batch.json")
    with open(batch_path, "w") as f:
        json.dump(seg1_batch, f, indent=2, ensure_ascii=False)

    r = run_tool([
        "python3", "-u", str(TOOLS / "seedance_gen.py"),
        "--batch", batch_path,
        "--out-dir", str(EXP / "output"),
        "--concurrency", "2",
    ], timeout=1800)
    log["steps"].append({"step": "seg1-dual", "ok": r.returncode == 0})

    if r.returncode != 0:
        print("⛔ Seg1 failed.", flush=True)
        batch_log = EXP / "output" / "seedance-batch-log.json"
        if batch_log.exists():
            with open(batch_log) as f:
                results = json.load(f)
            for res in results:
                if res.get("error") == "MODERATION_BLOCK":
                    print(f"⛔ {res['id']} blocked by moderation — ABANDONING per standing order.", flush=True)
                    log["abandoned"] = True
                    log["reason"] = "MODERATION_BLOCK"
                    with open(str(EXP / "output" / "generation-log.json"), "w") as f:
                        json.dump(log, f, indent=2, ensure_ascii=False)
                    sys.exit(1)

    # ── Step 3: Seg2 (needs Seg1 video — sequential per style, but styles concurrent) ──
    seg2_batch = []
    for style in styles:
        seg1_path = str(EXP / "output" / f"{style}-seg1.mp4")
        if not os.path.exists(seg1_path):
            print(f"⏭ Skipping {style} Seg2 (no Seg1)", flush=True)
            continue
        seg2_batch.append({
            "id": f"{style}-seg2",
            "prompt": SEG2_PROMPT,
            "video": seg1_path,
            "out": f"{style}-seg2.mp4",
        })

    if seg2_batch:
        seg2_batch_path = str(EXP / "output" / "seg2-batch.json")
        with open(seg2_batch_path, "w") as f:
            json.dump(seg2_batch, f, indent=2, ensure_ascii=False)
        r = run_tool([
            "python3", "-u", str(TOOLS / "seedance_gen.py"),
            "--batch", seg2_batch_path,
            "--out-dir", str(EXP / "output"),
            "--concurrency", "2",
        ], timeout=1800)
        log["steps"].append({"step": "seg2-dual", "ok": r.returncode == 0})

    # ── Step 4: Concat per style ──
    for style in styles:
        seg1 = str(EXP / "output" / f"{style}-seg1.mp4")
        seg2 = str(EXP / "output" / f"{style}-seg2.mp4")
        final = str(EXP / "output" / f"final-{style}.mp4")
        if not (os.path.exists(seg1) and os.path.exists(seg2)):
            continue
        r = run_tool([
            "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
            "--inputs", seg1, seg2,
            "--out", final,
            "--check-audio", "--check-per-segment",
        ])
        log["steps"].append({"step": f"concat-{style}", "ok": r.returncode == 0})

    # ── Save log ──
    with open(str(EXP / "output" / "generation-log.json"), "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Log: {EXP / 'output' / 'generation-log.json'}", flush=True)
    print("Done!", flush=True)


if __name__ == "__main__":
    main()
