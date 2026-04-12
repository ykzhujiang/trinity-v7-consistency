#!/usr/bin/env python3
"""V7-095: Audio Tail A/B Test — strip vs keep-audio(tail-2s)
Reuses V7-092 Test A scene (Genshin teahouse).
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLS = os.path.expanduser("~/trinity-v7-consistency/tools")
EXP = os.path.dirname(os.path.abspath(__file__))
SEG1 = os.path.join(EXP, "..", "v7-092", "seg1-shared.mp4")
SEG1_TAIL = os.path.join(EXP, "test-b", "seg1-tail.mp4")

PROMPTS = {
    "seg2": "Continuation of previous scene. The young man lifts the teacup and takes a sip, closes eyes savoring the taste. A bird lands on the windowsill outside. Same medium shot side angle, same warm golden lighting. 延续上一场景，年轻男子端起茶杯品茶，闭眼回味。窗外一只鸟停在窗台上。",
    "seg3": "Continuation of previous scene. The young man opens eyes and smiles gently, sets down the teacup. He picks up a calligraphy brush from the table and begins writing on paper. Same medium shot side angle, same warm lighting. 延续上一场景，年轻男子睁眼微笑，放下茶杯，拿起毛笔在纸上书写。"
}

def run_gen(label, video_in, out_dir, keep_audio=False):
    """Generate seg2 and seg3 sequentially (extend chain), return results."""
    os.makedirs(out_dir, exist_ok=True)
    results = {}
    
    # Seg2
    seg2_out = os.path.join(out_dir, "seg2.mp4")
    cmd = [
        "python3", "-u", os.path.join(TOOLS, "seedance_gen.py"),
        "--prompt", PROMPTS["seg2"],
        "--video", video_in,
        "--out", seg2_out,
        "--ratio", "9:16",
    ]
    if keep_audio:
        cmd.append("--keep-audio")
    
    print(f"[{label}] Generating seg2...", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    seg2_time = time.time() - t0
    
    if r.returncode != 0 or not os.path.exists(seg2_out):
        print(f"[{label}] seg2 FAILED: {r.stderr[-300:]}", flush=True)
        results["seg2"] = {"ok": False, "error": r.stderr[-300:], "elapsed": seg2_time}
        return results
    
    results["seg2"] = {"ok": True, "path": seg2_out, "elapsed": seg2_time}
    print(f"[{label}] seg2 done ({seg2_time:.0f}s)", flush=True)
    
    # Seg3
    seg3_out = os.path.join(out_dir, "seg3.mp4")
    cmd = [
        "python3", "-u", os.path.join(TOOLS, "seedance_gen.py"),
        "--prompt", PROMPTS["seg3"],
        "--video", seg2_out,
        "--out", seg3_out,
        "--ratio", "9:16",
    ]
    if keep_audio:
        cmd.append("--keep-audio")
    
    print(f"[{label}] Generating seg3...", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    seg3_time = time.time() - t0
    
    if r.returncode != 0 or not os.path.exists(seg3_out):
        print(f"[{label}] seg3 FAILED: {r.stderr[-300:]}", flush=True)
        results["seg3"] = {"ok": False, "error": r.stderr[-300:], "elapsed": seg3_time}
        return results
    
    results["seg3"] = {"ok": True, "path": seg3_out, "elapsed": seg3_time}
    print(f"[{label}] seg3 done ({seg3_time:.0f}s)", flush=True)
    return results

def concat_final(seg1, seg2, seg3, out, label):
    """Concatenate 3 segments with TTS overlay (or just concat for now)."""
    # Simple concat without TTS for audio comparison
    list_file = os.path.join(os.path.dirname(out), "concat_list.txt")
    with open(list_file, "w") as f:
        f.write(f"file '{seg1}'\nfile '{seg2}'\nfile '{seg3}'\n")
    
    cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", "-y", out]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and os.path.exists(out):
        mb = os.path.getsize(out) / 1024 / 1024
        print(f"[{label}] Final: {mb:.1f}MB", flush=True)
        return True
    print(f"[{label}] Concat failed: {r.stderr[-200:]}", flush=True)
    return False

def check_audio(video_path):
    """Check if video has audio and return info."""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return {"has_audio": False, "error": "ffprobe failed"}
    streams = json.loads(r.stdout).get("streams", [])
    audio = [s for s in streams if s["codec_type"] == "audio"]
    return {"has_audio": len(audio) > 0, "audio_streams": len(audio)}

def main():
    log = {"experiment": "V7-095", "hypothesis": "H-171 retest", "tests": {}}
    
    print("=== V7-095: Audio Tail A/B ===", flush=True)
    print("Test A: full strip (default)", flush=True)
    print("Test B: keep-audio (2s tail)", flush=True)
    
    # Run both tests concurrently
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(run_gen, "A-strip", SEG1, os.path.join(EXP, "test-a"), keep_audio=False)
        fut_b = pool.submit(run_gen, "B-tail", SEG1_TAIL, os.path.join(EXP, "test-b"), keep_audio=True)
        
        res_a = fut_a.result()
        res_b = fut_b.result()
    
    log["tests"]["A"] = {"strategy": "full_strip", "results": res_a}
    log["tests"]["B"] = {"strategy": "audio_tail_2s", "results": res_b}
    
    # Concat finals
    for test_id, res, seg1_path in [("A", res_a, SEG1), ("B", res_b, SEG1_TAIL)]:
        if res.get("seg2", {}).get("ok") and res.get("seg3", {}).get("ok"):
            final = os.path.join(EXP, f"test-{test_id.lower()}", "final.mp4")
            ok = concat_final(seg1_path, res["seg2"]["path"], res["seg3"]["path"], final, test_id)
            if ok:
                log["tests"][test_id]["final"] = final
                # Audio check each segment
                for seg_name in ["seg2", "seg3"]:
                    audio_info = check_audio(res[seg_name]["path"])
                    log["tests"][test_id][f"{seg_name}_audio"] = audio_info
                final_audio = check_audio(final)
                log["tests"][test_id]["final_audio"] = final_audio
    
    # Save log
    log_path = os.path.join(EXP, "generation-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\nLog saved: {log_path}", flush=True)
    
    # Summary
    for t in ["A", "B"]:
        td = log["tests"][t]
        s2 = "✓" if td["results"].get("seg2", {}).get("ok") else "✗"
        s3 = "✓" if td["results"].get("seg3", {}).get("ok") else "✗"
        print(f"Test {t}: seg2={s2} seg3={s3}", flush=True)

if __name__ == "__main__":
    main()
