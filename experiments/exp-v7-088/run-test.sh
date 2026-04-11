#!/bin/bash
set -euo pipefail
# V7-088 Test Runner — runs one test (A or B)
# Usage: bash run-test.sh A|B

TEST="$1"
TOOLS=~/trinity-v7-consistency/tools
BASE=~/trinity-v7-consistency/experiments/exp-v7-088/test${TEST}
mkdir -p "$BASE"
cd "$BASE"

if [ "$TEST" = "A" ]; then
  STYLE="Genshin Impact game cinematic, 3D anime style, cel-shaded rendering, vibrant colors, detailed environment."

  PROMPT1="${STYLE} Ancient Chinese tea room, wooden low table with celadon tea set, bamboo forest visible through window, warm lantern light, about 15sqm. A white-haired young man (long hair in ponytail, wearing blue-white xianxia robe) sits at the tea table, slowly lifting a teacup to drink. Across from him sits a black-haired girl (twin tails, wearing red short robe), smiling at him. Soft warm lighting. Fixed medium shot, 15 degrees left of center."
  AUDIO1='这茶不错，师姐从哪找的？|秘密。'
  VOICE1_A="zh-CN-YunxiNeural"
  VOICE1_B="zh-CN-XiaoxiaoNeural"

  PROMPT2="${STYLE} Continuation of previous scene. Ancient Chinese tea room. The black-haired girl (twin tails, red short robe) reaches for the teapot and pours tea for the white-haired young man (ponytail, blue-white xianxia robe), who holds his cup with both hands. They exchange a smile. Fixed medium shot, same angle."
  AUDIO2='喝完这杯就该出发了。|嗯，这次任务不简单。'

  PROMPT3="${STYLE} Continuation of previous scene. Ancient Chinese tea room. The white-haired young man (ponytail, blue-white xianxia robe) puts down his teacup and stands up, adjusting the sword at his waist. The black-haired girl (twin tails, red short robe) also stands, picking up a folding fan from the table. They walk side by side toward the door. Fixed medium shot slowly pulling back to wide shot."
  AUDIO3='走吧，师姐。|嗯，一起。'

elif [ "$TEST" = "B" ]; then
  STYLE="Genshin Impact game cinematic, 3D anime style, cel-shaded rendering, vibrant colors, dynamic action scene."

  PROMPT1="${STYLE} Cliff-edge stone training ground, sea of clouds and distant mountains in background, cracked stone floor, strong wind blowing, sunlight piercing through clouds. A white-haired young man (long hair in ponytail, blue-white xianxia robe) swings his sword at the center of the training ground, sword light tracing an arc. A stone block is split in half, fragments scattering. Wind blows his robes. Wide shot showing full training ground."
  AUDIO1='破！'
  VOICE1_A="zh-CN-YunxiNeural"
  VOICE1_B=""

  PROMPT2="${STYLE} Continuation of previous scene. Cliff-edge stone training ground, clouds and mountains background. A black-haired girl (twin tails, red short robe) leaps in from the right side, opens her folding fan to block the white-haired young man's (ponytail, blue-white xianxia robe) next strike. They engage in close combat, the girl spins and kicks, the young man backflips to dodge. Medium shot tracking, rotating around the two fighters."
  AUDIO2='就这？|师姐别大意！'

  PROMPT3="${STYLE} Continuation of previous scene. Cliff-edge training ground, cloud sea background. Both fighters leap into the air simultaneously, exchange positions mid-air and land. The white-haired young man (ponytail, blue-white robe) kneels on one knee panting, the black-haired girl (twin tails, red robe) stands before him closing her fan with a smile. Distant cloud sea churning. Low angle rising to level shot."
  AUDIO3='这次算你赢。|下次可不会手下留情。'
fi

echo "=== V7-088 Test $TEST — Starting ==="
echo "Base dir: $BASE"

# --- Seg1: text-to-video ---
echo ">>> Seg1: generating..."
python3 -u $TOOLS/seedance_gen.py --prompt "$PROMPT1" --out seg1.mp4
echo ">>> Seg1 done"

# --- TTS for Seg1 ---
echo ">>> TTS Seg1..."
IFS='|' read -ra LINES1 <<< "$AUDIO1"
TTS_FILES1=()
for i in "${!LINES1[@]}"; do
  VOICE="zh-CN-YunxiNeural"
  if [ $((i % 2)) -eq 1 ]; then VOICE="zh-CN-XiaoxiaoNeural"; fi
  python3 -u $TOOLS/tts_gen.py --text "${LINES1[$i]}" --out "seg1_tts_${i}.mp3" --voice "$VOICE"
  TTS_FILES1+=("seg1_tts_${i}.mp3")
done
# Concat TTS files for seg1
if [ ${#TTS_FILES1[@]} -gt 1 ]; then
  printf "file '%s'\n" "${TTS_FILES1[@]}" > seg1_tts_list.txt
  ffmpeg -y -f concat -safe 0 -i seg1_tts_list.txt -c copy seg1_audio.mp3
else
  cp "${TTS_FILES1[0]}" seg1_audio.mp3
fi

# --- Audio strip for extend ---
echo ">>> Stripping audio from seg1..."
ffmpeg -y -i seg1.mp4 -an -c:v copy seg1-noaudio.mp4

# --- Seg2: extend ---
echo ">>> Seg2: generating (extend from seg1)..."
python3 -u $TOOLS/seedance_gen.py --prompt "$PROMPT2" --video seg1-noaudio.mp4 --out seg2.mp4
echo ">>> Seg2 done"

# --- TTS for Seg2 ---
echo ">>> TTS Seg2..."
IFS='|' read -ra LINES2 <<< "$AUDIO2"
TTS_FILES2=()
for i in "${!LINES2[@]}"; do
  VOICE="zh-CN-XiaoxiaoNeural"
  if [ $((i % 2)) -eq 1 ]; then VOICE="zh-CN-YunxiNeural"; fi
  python3 -u $TOOLS/tts_gen.py --text "${LINES2[$i]}" --out "seg2_tts_${i}.mp3" --voice "$VOICE"
  TTS_FILES2+=("seg2_tts_${i}.mp3")
done
if [ ${#TTS_FILES2[@]} -gt 1 ]; then
  printf "file '%s'\n" "${TTS_FILES2[@]}" > seg2_tts_list.txt
  ffmpeg -y -f concat -safe 0 -i seg2_tts_list.txt -c copy seg2_audio.mp3
else
  cp "${TTS_FILES2[0]}" seg2_audio.mp3
fi

# --- Audio strip seg2 for extend ---
echo ">>> Stripping audio from seg2..."
ffmpeg -y -i seg2.mp4 -an -c:v copy seg2-noaudio.mp4

# --- Seg3: extend ---
echo ">>> Seg3: generating (extend from seg2)..."
python3 -u $TOOLS/seedance_gen.py --prompt "$PROMPT3" --video seg2-noaudio.mp4 --out seg3.mp4
echo ">>> Seg3 done"

# --- TTS for Seg3 ---
echo ">>> TTS Seg3..."
IFS='|' read -ra LINES3 <<< "$AUDIO3"
TTS_FILES3=()
for i in "${!LINES3[@]}"; do
  VOICE="zh-CN-YunxiNeural"
  if [ $((i % 2)) -eq 1 ]; then VOICE="zh-CN-XiaoxiaoNeural"; fi
  python3 -u $TOOLS/tts_gen.py --text "${LINES3[$i]}" --out "seg3_tts_${i}.mp3" --voice "$VOICE"
  TTS_FILES3+=("seg3_tts_${i}.mp3")
done
if [ ${#TTS_FILES3[@]} -gt 1 ]; then
  printf "file '%s'\n" "${TTS_FILES3[@]}" > seg3_tts_list.txt
  ffmpeg -y -f concat -safe 0 -i seg3_tts_list.txt -c copy seg3_audio.mp3
else
  cp "${TTS_FILES3[0]}" seg3_audio.mp3
fi

# --- Merge video + TTS audio per segment ---
echo ">>> Merging video+audio per segment..."
for S in 1 2 3; do
  VID="seg${S}.mp4"
  AUD="seg${S}_audio.mp3"
  OUT="seg${S}-final.mp4"
  # Get video duration, pad/trim audio to match
  DUR=$(ffprobe -v error -select_streams v -show_entries stream=duration -of csv=p=0 "$VID" 2>/dev/null | head -1)
  ffmpeg -y -i "$VID" -i "$AUD" -c:v copy -c:a aac -shortest -t "$DUR" "$OUT"
  echo ">>> seg${S}-final.mp4 created"
done

# --- Final concat ---
echo ">>> Concatenating 3 segments..."
python3 -u $TOOLS/ffmpeg_concat.py --inputs seg1-final.mp4 seg2-final.mp4 seg3-final.mp4 --out "V7-088${TEST}-final.mp4" --check-audio

echo "=== V7-088 Test $TEST — COMPLETE ==="
echo "Final: $BASE/V7-088${TEST}-final.mp4"
ls -lh "V7-088${TEST}-final.mp4"
