#!/usr/bin/env python3
"""EXP-V7-045 runner: 3-Segment extend chain for 赌神觉醒 (anime only)."""
import json, subprocess, sys, os, shutil
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"
TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
EXP = Path(__file__).resolve().parent
ASSETS = {
    "chenfeng": "asset://asset-20260411192533-xzx5w",
    "malaoban": "asset://asset-20260411192546-grpn7",
    "casino": "asset://asset-20260411192603-tz89r",
}

# TTS lines per segment (Chinese)
TTS_LINES = {
    "seg1": [
        {"speaker": "马老板", "text": "小陈啊，听说你数学很好？"},
        {"speaker": "旁白", "text": "欠的二十万，就靠今晚了。"},
        {"speaker": "马老板", "text": "今天玩点特别的，梭哈。"},
        {"speaker": "旁白", "text": "翻开第一张，黑桃三。这手牌烂透了。"},
        {"speaker": "陈风", "text": "马老板，梭哈之前，加个注怎么样？"},
    ],
    "seg2": [
        {"speaker": "马老板", "text": "小子，你一手烂牌还敢加注？"},
        {"speaker": "马老板", "text": "一对三？哈哈哈！"},
        {"speaker": "旁白", "text": "笑吧。数学告诉我，这副牌被做过手脚。但做手脚的人，忘了一件事。"},
        {"speaker": "陈风", "text": "马老板，你的千术，漏了一张牌。"},
    ],
    "seg3": [
        {"speaker": "马老板", "text": "小子你敢诬陷我！给我上！"},
        {"speaker": "陈风", "text": "马老板，您忘了，我是程序员。"},
        {"speaker": "旁白", "text": "今晚所有监控画面，已经实时传到了三个不同的服务器。"},
        {"speaker": "陈风", "text": "马老板，数学不好就别开赌场。"},
    ],
}

# Seedance prompts
SEG1_PROMPT = f"""Anime style. A dimly lit underground casino, green felt round table, warm yellow pendant lamp, wisps of smoke.
A young Chinese man (陈风, 28, sharp eyes, short black hair, dark jacket) sits on the left side of the table. An older Chinese man (马老板, 50s, round face, gold watch, dark suit) leans back in his chair on the right side, tapping his gold watch with a calculating smile. Two bodyguards stand in the background.

Camera: Medium shot, static. 陈风 sits down at the table. 马老板 pushes a deck of cards forward. 陈风 picks up a card, his hand trembles slightly. He takes a deep breath and speaks.

The scene ends with 陈风's face in a calm, still expression looking at 马老板.

No slow motion. Normal speed movement and speech. No text on screen. No subtitles. Anime illustration style, cinematic lighting.

Reference characters: 陈风 [{ASSETS['chenfeng']}], 马老板 [{ASSETS['malaoban']}]
Reference scene: [{ASSETS['casino']}]"""

SEG2_PROMPT = f"""Anime style continuation. Same underground casino, same green felt table.

陈风 (young Chinese man, 28, short black hair, dark jacket) leans forward slightly, expression shifting from tense to calm. 马老板 (older Chinese man, 50s, round face, gold watch) starts looking uneasy.

Camera: Medium shot favoring 陈风's side. 马老板 laughs at the cards. 陈风's expression doesn't change. Then 陈风 stands up and slaps a card from his sleeve onto the table. 马老板's face turns to shock.

The scene ends with 马老板's horrified expression frozen still.

No slow motion. Normal speed. No text on screen. No subtitles. Anime style.

Reference characters: 陈风 [{ASSETS['chenfeng']}], 马老板 [{ASSETS['malaoban']}]"""

SEG3_PROMPT = f"""Anime style continuation. Same underground casino, lights slightly brighter, tension escalated.

马老板 (older Chinese man, 50s, round face) slams the table and stands up. Two bodyguards move toward 陈风. 陈风 (young Chinese man, 28, short black hair, dark jacket) calmly pulls out a phone, screen glows on 马老板's face. 马老板 collapses back into his chair in defeat. 陈风 picks up chips, smiles, and walks toward the exit.

Camera: Wide high angle, then low angle on 陈风, then close-up on 马老板, then full wide shot pulling back.

No slow motion. Normal speed. No text on screen. No subtitles. Anime style.

Reference characters: 陈风 [{ASSETS['chenfeng']}], 马老板 [{ASSETS['malaoban']}]"""


def run_seedance(prompt, images=None, video=None, out=None):
    """Call seedance_gen.py."""
    cmd = ["python3", "-u", str(TOOLS / "seedance_gen.py"), "--prompt", prompt, "--out", out, "--duration", "15", "--ratio", "9:16"]
    if images:
        cmd += ["--images"] + images
    if video:
        cmd += ["--video", video]
    print(f"\n{'='*60}", flush=True)
    print(f"Generating: {out}", flush=True)
    print(f"{'='*60}", flush=True)
    r = subprocess.run(cmd, timeout=600)
    if r.returncode != 0:
        print(f"[FAIL] {out}", flush=True)
        return False
    return True


def main():
    out_dir = EXP / "videos"
    out_dir.mkdir(exist_ok=True)

    # Seg1: text-to-video with reference images
    seg1_out = str(out_dir / "seg1-anime.mp4")
    ok = run_seedance(SEG1_PROMPT, images=[ASSETS["chenfeng"], ASSETS["malaoban"], ASSETS["casino"]], out=seg1_out)
    if not ok:
        print("[ABORT] Seg1 failed", flush=True)
        sys.exit(1)

    # Seg2: extend from Seg1
    seg2_out = str(out_dir / "seg2-anime.mp4")
    ok = run_seedance(SEG2_PROMPT, video=seg1_out, images=[ASSETS["chenfeng"], ASSETS["malaoban"]], out=seg2_out)
    if not ok:
        print("[ABORT] Seg2 failed", flush=True)
        sys.exit(1)

    # Seg3: extend from Seg2
    seg3_out = str(out_dir / "seg3-anime.mp4")
    ok = run_seedance(SEG3_PROMPT, video=seg2_out, images=[ASSETS["chenfeng"], ASSETS["malaoban"]], out=seg3_out)
    if not ok:
        print("[ABORT] Seg3 failed", flush=True)
        sys.exit(1)

    print("\n✅ All 3 segments generated!", flush=True)
    print(f"  Seg1: {seg1_out}", flush=True)
    print(f"  Seg2: {seg2_out}", flush=True)
    print(f"  Seg3: {seg3_out}", flush=True)

    # Record generation log
    log = {
        "experiment": "EXP-V7-045",
        "story": "赌神觉醒",
        "style": "anime",
        "direction": "A (extend chain)",
        "segments": 3,
        "assets": ASSETS,
        "tts_lines": TTS_LINES,
        "prompts": {"seg1": SEG1_PROMPT, "seg2": SEG2_PROMPT, "seg3": SEG3_PROMPT},
    }
    with open(EXP / "generation-log.json", "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print("📋 Generation log saved", flush=True)


if __name__ == "__main__":
    main()
