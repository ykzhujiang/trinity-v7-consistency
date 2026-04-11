#!/bin/bash
set -e
cd ~/trinity-v7-consistency
EXP=experiments/exp-v7-076/output

echo "=== V7-076 Runner: Waiting for seg1 ==="

# Wait for seg1
while [ ! -f "$EXP/seg1.mp4" ]; do sleep 30; echo "  Waiting for seg1..."; done
echo "✓ seg1 ready"

# Strip audio from seg1
ffmpeg -y -i "$EXP/seg1.mp4" -an "$EXP/seg1-noaudio.mp4" 2>/dev/null
echo "✓ seg1 audio stripped"

# Seg2
echo "[V7-076] Generating seg2 (extend from seg1)..."
python3 -u tools/seedance_gen.py \
  --prompt 'Continuation of previous scene. The woman lifts the lid of the ornate box with both hands. A soft golden glow emanates from inside, illuminating her face. Her eyes widen in amazement. The man watches her from across the table with an expectant smile, leaning forward slightly. "打开看看，值不值得我跑遍三座城。" She gasps softly.' \
  --video "$EXP/seg1-noaudio.mp4" \
  --out "$EXP/seg2.mp4" --duration 15 --ratio 9:16
echo "✓ seg2 done"

# Strip audio from seg2
ffmpeg -y -i "$EXP/seg2.mp4" -an "$EXP/seg2-noaudio.mp4" 2>/dev/null
echo "✓ seg2 audio stripped"

# Seg3
echo "[V7-076] Generating seg3 (extend from seg2)..."
python3 -u tools/seedance_gen.py \
  --prompt 'Continuation of previous scene. The woman looks up from the box toward the man, a bright smile spreading across her face. They lock eyes. Both burst into laughter simultaneously. The man reaches for his wine cup, the woman mirrors him. They raise their cups and clink them together over the table. "干杯！" Both take a drink, smiling.' \
  --video "$EXP/seg2-noaudio.mp4" \
  --out "$EXP/seg3.mp4" --duration 15 --ratio 9:16
echo "✓ seg3 done"

# Concat
echo "[V7-076] Concatenating..."
python3 -u tools/ffmpeg_concat.py \
  "$EXP/seg1.mp4" "$EXP/seg2.mp4" "$EXP/seg3.mp4" \
  -o "$EXP/final.mp4" 2>&1
echo "✓ V7-076 COMPLETE: $EXP/final.mp4"
ls -lh "$EXP/final.mp4"
