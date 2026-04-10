#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "pillow>=10.0.0", "requests>=2.28.0"]
# ///
"""
EXP-V7-024: 深夜Debug→产品意外爆火 — 暖色调情绪反差

Thin runner using modular tools. No pipeline code duplication.
Usage: python3 -u experiments/exp-v7-024/run.py [--skip-assets] [--skip-video] [--style anime|realistic|both]
"""

import json, os, subprocess, sys, time, argparse
from pathlib import Path

BASE = Path.home() / "trinity-v7-consistency"
EXP = BASE / "experiments" / "exp-v7-024"
TOOLS = BASE / "tools"

# ── Character & Scene ──
CHAR_MAIN = (
    "中国男性，28岁，175cm，短发微乱，戴黑框眼镜，穿皱巴巴的灰色连帽卫衣，深色运动裤。"
    "面容偏瘦，有黑眼圈，表情略显疲惫但有韧劲。"
)

SCENE_NIGHT = (
    "现代创业公司开放式办公室，深夜2点。只有一个工位台灯亮着，暖黄色灯光。"
    "桌上有双屏显示器（屏幕有代码），3个空纸杯，零食袋，充电线缠绕。"
    "周围工位漆黑。远处落地窗外是城市暖色夜景灯光。整体暖黄色调。"
    "Warm lighting, warm color temperature, no cold blue tones."
)

SCENE_DAWN = (
    "同一间现代创业公司开放式办公室，清晨。窗外天亮，清晨橙色阳光从落地窗涌入，"
    "整个办公室被暖橙色光笼罩。桌上物品与深夜一致（空纸杯、零食袋、双屏显示器）。"
    "Warm orange morning sunlight, warm color temperature, no cold blue tones."
)

# ── Seedance Prompts ──
SEG1_PROMPT_TEMPLATE = """Physical state: 主角坐在办公椅上，面对双屏显示器（屏幕代码滚动光映在脸上）。桌上3个空纸杯、零食袋、充电线缠绕。台灯暖黄光。周围工位漆黑，只有远处窗外城市暖色灯光。

[Part 1] Medium shot from behind-left 45 degrees. {style_char} male 28yo with messy short hair and black-frame glasses wearing wrinkled gray hoodie sits at desk facing dual monitors with red error code. His hands stop on keyboard, right hand lifts to rub temple, left hand presses laptop edge. Deep frown. He sighs and says "第37次了…同一个bug…同一个位置…"

[Part 2] Close-up of face right side. Warm desk lamp light on face, code reflected in glasses. He smirks bitterly, mouth corner twitches. Right hand pushes glasses up revealing dark circles under eyes. He says sarcastically "当初非说'三天上线'…现在第三天了，线还没理清…"

[Part 3] Medium-close from front slightly right. Background: dark office, distant warm city lights through window. He grabs last paper cup to drink, finds it empty, tosses it in trash. Deep breath, fingers return to keyboard. No dialogue. Keyboard typing sounds start, rhythm speeds up.

[Part 4] Side close-up, character on left of frame. Monitor screen changes from red error to green success. His typing suddenly stops. He stares at screen 3 seconds, expression shifts from blank to slightly widened eyes. Lips move but no words. ~1 second silence. Background: distant AC hum.

No subtitles, no slow motion, no character looking at camera. Normal speed movement and natural pacing. 9:16 vertical. Warm indoor lighting throughout, warm color temperature, absolutely no cold blue tones. Generic modern Asian city skyline through windows."""

SEG2_PROMPT_TEMPLATE = """Extend @video1 by 15 seconds. Continue the scene seamlessly in the SAME office but now it is early morning with warm orange sunlight flooding through floor-to-ceiling windows.

Physical state: 主角仍坐在同一把办公椅上but has fallen asleep on desk. Phone on desk starts vibrating.

[Part 1] Medium shot from window direction looking inward. Warm orange morning backlight gradually illuminates the character silhouette. Phone buzzes on desk repeatedly. Character jolts awake from sleeping on desk, lifts head with keyboard marks on cheek. Rubs eyes, groggily looks at phone. No dialogue. Phone vibration sounds intensify.

[Part 2] Close-up of phone screen held in character's hand. Screen shows social media notifications flooding in rapidly. Character scrolls up, expression shifts from groggy to confused to pupils dilating. He reads aloud "这个bug太好玩了…居然变成新功能了…什么？？"

[Part 3] Medium shot, warm morning light fully illuminating scene. Character stands up abruptly, chair rolls backward. Left hand holds phone up, right hand involuntarily makes fist. Mouth opens wide, eyes slightly reddened. Chair slides away. He says with trembling voice "十…十万用户？一夜之间？？"

[Part 4] Wide shot from office corner. Character stands alone in morning sunlight, empty workstations around him. Light beam falls on him. He slowly crouches down, covers face with both hands. Shoulders shaking — laughing. Then throws head back, arms open wide, laughs silently at ceiling. No dialogue. Bird sounds from outside window. ~1 second silence.

Maintain EXACT same character appearance clothing and office setting as segment 1. No subtitles, no slow motion, no character looking at camera. Normal speed. 9:16 vertical. Warm orange morning lighting, absolutely no cold blue tones. Same furniture placement, same desk items, same wall decorations."""

def write_asset_specs(style: str, out_dir: str):
    """Write asset generation specs."""
    specs = [
        {"name": f"陈磊-{style}", "type": "character", "desc": CHAR_MAIN, "style": style},
        {"name": f"office-night-{style}", "type": "scene", "desc": SCENE_NIGHT, "style": style},
        {"name": f"office-dawn-{style}", "type": "scene", "desc": SCENE_DAWN, "style": style},
    ]
    path = os.path.join(out_dir, f"specs-{style}.json")
    with open(path, "w") as f:
        json.dump(specs, f, indent=2, ensure_ascii=False)
    return path

def run_tool(args, timeout=1800):
    """Run a tool, return subprocess result."""
    print(f"\n▶ {' '.join(args[:4])}...", flush=True)
    return subprocess.run(args, timeout=timeout)

def main():
    parser = argparse.ArgumentParser(description="EXP-V7-024 runner (modular tools)")
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-video", action="store_true")
    parser.add_argument("--style", choices=["anime", "realistic", "both"], default="both")
    args = parser.parse_args()

    styles = ["anime", "realistic"] if args.style == "both" else [args.style]
    assets_dir = str(EXP / "output" / "assets")
    os.makedirs(assets_dir, exist_ok=True)

    log = {"experiment": "EXP-V7-024", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "styles": styles, "steps": []}

    # ── Step 1: Assets (concurrent across styles) ──
    if not args.skip_assets:
        for style in styles:
            spec_path = write_asset_specs(style, assets_dir)
            r = run_tool([
                "python3", "-u", str(TOOLS / "gemini_chargen.py"),
                "--specs", spec_path,
                "--out-dir", assets_dir,
                "--concurrency", "3"
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
        char_ref = os.path.join(assets_dir, f"char-陈磊-{style}.webp")
        scene_ref = os.path.join(assets_dir, f"scene-office-night-{style}.webp")
        style_char = "Chinese" if style == "realistic" else "Anime-style Chinese"
        prompt = SEG1_PROMPT_TEMPLATE.format(style_char=style_char)
        images = [p for p in [char_ref, scene_ref] if os.path.exists(p)]
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
        "--concurrency", "2"
    ], timeout=1800)
    log["steps"].append({"step": "seg1-dual", "ok": r.returncode == 0})

    if r.returncode != 0:
        print("⛔ Seg1 failed. Check if moderation blocked.", flush=True)
        # Check for moderation blocks
        batch_log = EXP / "output" / "seedance-batch-log.json"
        if batch_log.exists():
            with open(batch_log) as f:
                results = json.load(f)
            for res in results:
                if res.get("error") == "MODERATION_BLOCK":
                    print(f"⛔ {res['id']} blocked by moderation — ABANDONING experiment per standing order.", flush=True)
                    log["abandoned"] = True
                    log["reason"] = "MODERATION_BLOCK"
                    with open(str(EXP / "output" / "generation-log.json"), "w") as f:
                        json.dump(log, f, indent=2, ensure_ascii=False)
                    sys.exit(1)

    # ── Step 3: Seg2 (sequential per style, needs Seg1 video) ──
    for style in styles:
        seg1_path = str(EXP / "output" / f"{style}-seg1.mp4")
        seg2_path = str(EXP / "output" / f"{style}-seg2.mp4")
        if not os.path.exists(seg1_path):
            print(f"⏭ Skipping {style} Seg2 (no Seg1)", flush=True)
            continue

        style_char = "Chinese" if style == "realistic" else "Anime-style Chinese"
        prompt = SEG2_PROMPT_TEMPLATE.format(style_char=style_char)
        r = run_tool([
            "python3", "-u", str(TOOLS / "seedance_gen.py"),
            "--prompt", prompt,
            "--video", seg1_path,
            "--out", seg2_path,
        ], timeout=1800)
        log["steps"].append({"step": f"seg2-{style}", "ok": r.returncode == 0})

        if r.returncode != 0:
            continue

        # ── Step 4: Concatenate ──
        final = str(EXP / "output" / f"final-{style}.mp4")
        r = run_tool([
            "python3", "-u", str(TOOLS / "ffmpeg_concat.py"),
            "--inputs", seg1_path, seg2_path,
            "--out", final,
            "--check-audio", "--check-per-segment"
        ])
        log["steps"].append({"step": f"concat-{style}", "ok": r.returncode == 0})

    # ── Save log ──
    with open(str(EXP / "output" / "generation-log.json"), "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Generation log: {EXP / 'output' / 'generation-log.json'}", flush=True)
    print("Done!", flush=True)


if __name__ == "__main__":
    main()
