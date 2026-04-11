#!/bin/bash
set -e
cd ~/trinity-v7-consistency
EXP=experiments/exp-v7-075/output

echo "=== V7-075 Runner: Waiting for seg2 ==="
while [ ! -f "$EXP/seg2.mp4" ]; do sleep 30; echo "  Waiting for seg2..."; done
echo "✓ seg2 ready"

# Strip audio from seg2
ffmpeg -y -i "$EXP/seg2.mp4" -an "$EXP/seg2-noaudio.mp4" 2>/dev/null
echo "✓ seg2 audio stripped"

# Seg3
echo "[V7-075] Generating seg3 (extend from seg2)..."
python3 -u tools/seedance_gen.py \
  --prompt 'Continuation of previous scene. The swordsman reads the letter intensely, his expression shifting from confusion to shock, pupils dilating. His hands tremble slightly holding the paper. He suddenly looks up toward the window, jaw tight, determined eyes reflecting the golden sunlight. "原来如此……一切都说得通了。" He folds the letter and tucks it into his robe.' \
  --video "$EXP/seg2-noaudio.mp4" \
  --out "$EXP/seg3.mp4" --duration 15 --ratio 9:16
echo "✓ seg3 done"

# Concat
echo "[V7-075] Concatenating..."
python3 -u tools/ffmpeg_concat.py \
  "$EXP/seg1.mp4" "$EXP/seg2.mp4" "$EXP/seg3.mp4" \
  -o "$EXP/final.mp4" 2>&1
echo "✓ V7-075 COMPLETE: $EXP/final.mp4"
ls -lh "$EXP/final.mp4"
