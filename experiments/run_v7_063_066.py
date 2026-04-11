#!/usr/bin/env python3 -u
"""
EXP-V7-063~066 Runner: Text-to-video game style horizontal comparison V2
Fix: Each segment has COMPLETELY DIFFERENT location (V7-046 pattern)
"""
import json, subprocess, sys, os, time

TOOLS = os.path.expanduser("~/trinity-v7-consistency/tools")
EXPS = os.path.expanduser("~/trinity-v7-consistency/experiments")

STYLES = {
    "063": {
        "id": "rpg",
        "prefix": "RPG game cinematic cutscene, Unreal Engine 5 render, dramatic cinematic lighting, game CG quality, detailed environment",
    },
    "064": {
        "id": "cyber",
        "prefix": "Cyberpunk game style, Cyberpunk 2077 aesthetic, neon glow, rain-slicked surfaces, holographic ambient light, night city vibe",
    },
    "065": {
        "id": "gacha",
        "prefix": "Gacha mobile game style, Genshin Impact aesthetic, anime character design, soft glow, vivid color palette, detailed background art",
    },
    "066": {
        "id": "pixar",
        "prefix": "Pixar Disney 3D animation style, expressive character, warm color palette, cinematic depth of field, studio lighting quality",
    },
}

# Seg2: OUTDOOR rooftop - completely different from Seg1
SEG2_SCENE = (
    "Continuation of previous scene, now transitioning to: {style}. "
    "Exterior of an old apartment building rooftop at night, concrete railing, "
    "distant city neon lights and skyscraper silhouettes, night wind blowing hair, "
    "cool moonlight. The same 25-year-old Chinese male programmer, now wearing a "
    "black hoodie over his gray hoodie, leans against the rooftop railing looking at "
    "distant city lights, pulls out phone and looks at an old photo on screen, takes "
    "a deep breath, puts phone back in pocket, eyes become determined. "
    "Camera: wide shot establishing rooftop, then medium close-up of face in profile. "
    "Dialogue in Chinese Mandarin, must finish before second 12: "
    "'当初说好要做出来的……还没到放弃的时候。回去。' "
    "9:16 vertical format, cinematic composition, character not looking at camera. "
    "No subtitles, no slow motion."
)

# Seg3: INDOOR cafe - completely different from Seg1 and Seg2
SEG3_SCENE = (
    "Continuation of previous scene, now transitioning to: {style}. "
    "Interior of a bright modern coffee shop in daytime, warm sunlight streaming through "
    "floor-to-ceiling windows, wooden long table, blurred background of other people working, "
    "a latte and laptop on the table. The same 25-year-old Chinese male programmer, now "
    "wearing a clean white t-shirt looking refreshed, typing rapidly on laptop, suddenly "
    "stops and stares at screen, eyes widening with excitement, mouth curving into a smile, "
    "pumps fist and whispers excitedly. "
    "Camera: over-shoulder shot of screen, then medium close-up of face showing joy. "
    "Dialogue in Chinese Mandarin, must finish before second 12: "
    "'等一下……这个方向……通了！！！真的通了！！！哈哈哈！' "
    "9:16 vertical format, cinematic composition, character not looking at camera. "
    "No subtitles, no slow motion."
)

def run_cmd(cmd, timeout=1800):
    print(f"\n{'='*60}")
    print(f"CMD: {' '.join(cmd)}")
    print(f"{'='*60}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    print(r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout)
    if r.stderr:
        print(f"STDERR: {r.stderr[-1000:]}")
    if r.returncode != 0:
        print(f"⚠️ Return code: {r.returncode}")
    return r

def run_batch(batch_file, out_dir, concurrency=4):
    return run_cmd([
        "python3", "-u", f"{TOOLS}/seedance_gen.py",
        "--batch", batch_file,
        "--out-dir", out_dir,
        "--concurrency", str(concurrency),
    ])

def main():
    # ======== PHASE 1: All Seg1 concurrently ========
    print("\n🎬 PHASE 1: Generating all Seg1 (4 styles concurrently)")
    
    # Combine all seg1 batches into one
    all_seg1 = []
    for exp_num, style in STYLES.items():
        batch_path = f"{EXPS}/exp-v7-{exp_num}/seg1_batch.json"
        with open(batch_path) as f:
            all_seg1.extend(json.load(f))
    
    combined_seg1 = f"{EXPS}/combined_seg1_063-066.json"
    with open(combined_seg1, "w") as f:
        json.dump(all_seg1, f, indent=2)
    
    r = run_batch(combined_seg1, f"{EXPS}", concurrency=4)
    
    # Verify seg1 outputs
    for exp_num, style in STYLES.items():
        seg1_path = f"{EXPS}/exp-v7-{exp_num}/output/seg1.mp4"
        if not os.path.exists(seg1_path):
            print(f"❌ {exp_num} seg1 missing: {seg1_path}")
        else:
            sz = os.path.getsize(seg1_path)
            print(f"✅ {exp_num} seg1: {sz/1024:.0f}KB")
    
    # ======== PHASE 2: All Seg2 concurrently (extend from Seg1) ========
    print("\n🎬 PHASE 2: Generating all Seg2 (extend from Seg1)")
    
    all_seg2 = []
    for exp_num, style in STYLES.items():
        seg1_path = f"{EXPS}/exp-v7-{exp_num}/output/seg1.mp4"
        if not os.path.exists(seg1_path):
            print(f"⏭️ Skipping {exp_num} seg2 (no seg1)")
            continue
        seg2_prompt = SEG2_SCENE.format(style=style["prefix"])
        all_seg2.append({
            "id": f"{style['id']}-seg2",
            "prompt": seg2_prompt,
            "video": seg1_path,
            "out": f"{EXPS}/exp-v7-{exp_num}/output/seg2.mp4",
        })
    
    combined_seg2 = f"{EXPS}/combined_seg2_063-066.json"
    with open(combined_seg2, "w") as f:
        json.dump(all_seg2, f, indent=2)
    
    r = run_batch(combined_seg2, f"{EXPS}", concurrency=4)
    
    for exp_num, style in STYLES.items():
        seg2_path = f"{EXPS}/exp-v7-{exp_num}/output/seg2.mp4"
        if os.path.exists(seg2_path):
            print(f"✅ {exp_num} seg2: {os.path.getsize(seg2_path)/1024:.0f}KB")
    
    # ======== PHASE 3: All Seg3 concurrently (extend from Seg2) ========
    print("\n🎬 PHASE 3: Generating all Seg3 (extend from Seg2)")
    
    all_seg3 = []
    for exp_num, style in STYLES.items():
        seg2_path = f"{EXPS}/exp-v7-{exp_num}/output/seg2.mp4"
        if not os.path.exists(seg2_path):
            print(f"⏭️ Skipping {exp_num} seg3 (no seg2)")
            continue
        seg3_prompt = SEG3_SCENE.format(style=style["prefix"])
        all_seg3.append({
            "id": f"{style['id']}-seg3",
            "prompt": seg3_prompt,
            "video": seg2_path,
            "out": f"{EXPS}/exp-v7-{exp_num}/output/seg3.mp4",
        })
    
    combined_seg3 = f"{EXPS}/combined_seg3_063-066.json"
    with open(combined_seg3, "w") as f:
        json.dump(all_seg3, f, indent=2)
    
    r = run_batch(combined_seg3, f"{EXPS}", concurrency=4)
    
    for exp_num, style in STYLES.items():
        seg3_path = f"{EXPS}/exp-v7-{exp_num}/output/seg3.mp4"
        if os.path.exists(seg3_path):
            print(f"✅ {exp_num} seg3: {os.path.getsize(seg3_path)/1024:.0f}KB")
    
    # ======== PHASE 4: Concat + Audio Check ========
    print("\n🎬 PHASE 4: Concatenating + Audio Check")
    
    results = {}
    for exp_num, style in STYLES.items():
        exp_dir = f"{EXPS}/exp-v7-{exp_num}/output"
        segs = [f"{exp_dir}/seg{i}.mp4" for i in [1,2,3]]
        if not all(os.path.exists(s) for s in segs):
            print(f"⏭️ Skipping {exp_num} concat (missing segments)")
            results[exp_num] = {"status": "incomplete"}
            continue
        
        final = f"{exp_dir}/final.mp4"
        r = run_cmd([
            "python3", "-u", f"{TOOLS}/ffmpeg_concat.py",
            "--inputs", *segs,
            "--out", final,
            "--check-audio", "--check-per-segment",
        ])
        
        if os.path.exists(final):
            sz = os.path.getsize(final)
            print(f"✅ {exp_num} final: {sz/1024/1024:.1f}MB")
            results[exp_num] = {"status": "complete", "size_mb": round(sz/1024/1024, 1), "path": final}
        else:
            results[exp_num] = {"status": "concat_failed"}
    
    # ======== PHASE 5: Git push ========
    print("\n🎬 PHASE 5: Git push")
    os.chdir(os.path.expanduser("~/trinity-v7-consistency"))
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run(["git", "commit", "-m", "[operator][cycle-917] EXP-V7-063~066: game style V2 with scene transitions"], capture_output=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
    r = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr[-500:])
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for exp_num, res in results.items():
        style_name = STYLES[exp_num]["id"]
        print(f"  V7-{exp_num} ({style_name}): {res['status']}")
    
    # Save generation log
    log = {
        "cycle": 917,
        "experiment_ids": ["V7-063", "V7-064", "V7-065", "V7-066"],
        "method": "text-to-video + extend chain (V7-046 pattern)",
        "fix_applied": "Each segment uses completely different location/scene/dialogue",
        "seg1_scene": "Indoor rental room at night",
        "seg2_scene": "Outdoor rooftop at night",
        "seg3_scene": "Indoor cafe in daytime",
        "results": results,
    }
    with open(f"{EXPS}/generation-log-063-066.json", "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    
    print("\nDone!")

if __name__ == "__main__":
    main()
