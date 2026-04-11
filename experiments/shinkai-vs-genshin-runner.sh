#!/bin/bash
set -e
cd ~/trinity-v7-consistency

run_experiment() {
  local EXP_ID=$1
  local EXP_DIR="experiments/exp-${EXP_ID}/output"
  local PROMPTS="experiments/exp-${EXP_ID}/prompts.json"
  
  SEG1_PROMPT=$(python3 -c "import json; d=json.load(open('$PROMPTS')); print(d['seg1']['prompt'])")
  SEG2_PROMPT=$(python3 -c "import json; d=json.load(open('$PROMPTS')); print(d['seg2']['prompt'])")
  SEG3_PROMPT=$(python3 -c "import json; d=json.load(open('$PROMPTS')); print(d['seg3']['prompt'])")
  
  echo "[$EXP_ID] Seg1: text-to-video..."
  python3 -u tools/seedance_gen.py --prompt "$SEG1_PROMPT" --out "$EXP_DIR/seg1.mp4" --duration 15 --ratio 9:16
  echo "[$EXP_ID] ✓ seg1 done"
  
  ffmpeg -y -i "$EXP_DIR/seg1.mp4" -an "$EXP_DIR/seg1-noaudio.mp4" 2>/dev/null
  
  echo "[$EXP_ID] Seg2: extend from seg1..."
  python3 -u tools/seedance_gen.py --prompt "$SEG2_PROMPT" --video "$EXP_DIR/seg1-noaudio.mp4" --out "$EXP_DIR/seg2.mp4" --duration 15 --ratio 9:16
  echo "[$EXP_ID] ✓ seg2 done"
  
  ffmpeg -y -i "$EXP_DIR/seg2.mp4" -an "$EXP_DIR/seg2-noaudio.mp4" 2>/dev/null
  
  echo "[$EXP_ID] Seg3: extend from seg2..."
  python3 -u tools/seedance_gen.py --prompt "$SEG3_PROMPT" --video "$EXP_DIR/seg2-noaudio.mp4" --out "$EXP_DIR/seg3.mp4" --duration 15 --ratio 9:16
  echo "[$EXP_ID] ✓ seg3 done"
  
  echo "[$EXP_ID] Concatenating..."
  python3 -u tools/ffmpeg_concat.py "$EXP_DIR/seg1.mp4" "$EXP_DIR/seg2.mp4" "$EXP_DIR/seg3.mp4" -o "$EXP_DIR/final.mp4"
  echo "[$EXP_ID] ✓ COMPLETE: $EXP_DIR/final.mp4"
  ls -lh "$EXP_DIR/final.mp4"
}

echo "============================================"
echo "V7-077/078: Shinkai vs Genshin Comparison"
echo "============================================"

# Run both experiments sequentially (Seedance seg1 can't parallelize safely with 074/075/076 still running)
# Actually, run V7-077 first, then V7-078
run_experiment "v7-077"
echo ""
run_experiment "v7-078"

echo ""
echo "=== BOTH V7-077 AND V7-078 COMPLETE ==="
