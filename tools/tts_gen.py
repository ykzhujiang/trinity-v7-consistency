#!/usr/bin/env python3 -u
"""Simple TTS wrapper using edge-tts."""
import argparse, asyncio, sys

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    args = parser.parse_args()
    
    import edge_tts
    comm = edge_tts.Communicate(args.text, args.voice)
    await comm.save(args.out)
    print(f"TTS: {args.out} ({len(args.text)} chars)", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
