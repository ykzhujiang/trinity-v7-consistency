#!/bin/bash
set -euo pipefail
export PYTHONUNBUFFERED=1
cd ~/trinity-v7-consistency

EXPA=experiments/exp-v7-085a/output
EXPB=experiments/exp-v7-085b/output

echo "=== H-158 Prompt Length A/B Test ==="
echo "  V7-085a: Short prompt (~400 chars)"  
echo "  V7-085b: Long prompt (~750 chars)"

# --- TTS (edge-tts, zh-CN) ---
echo "=== Generating TTS ==="
edge-tts --voice zh-CN-YunxiNeural --text "这个……送给你的。打开看看。" --write-media $EXPA/seg1.wav &
edge-tts --voice zh-CN-YunxiNeural --text "这个……送给你的。打开看看。" --write-media $EXPB/seg1.wav &
wait
edge-tts --voice zh-CN-YunxiNeural --text "好，来一壶你们最好的酒。" --write-media $EXPA/seg2.wav &
edge-tts --voice zh-CN-YunxiNeural --text "好，来一壶你们最好的酒。" --write-media $EXPB/seg2.wav &
wait
edge-tts --voice zh-CN-YunxiNeural --text "不错……值得跑这一趟。" --write-media $EXPA/seg3.wav &
edge-tts --voice zh-CN-YunxiNeural --text "不错……值得跑这一趟。" --write-media $EXPB/seg3.wav &
wait
echo "✓ TTS done"

# --- Seg1: text-to-video (concurrent A + B) ---
echo "=== Seg1: text-to-video ==="
python3 -u tools/seedance_gen.py \
  --prompt 'Genshin Impact style 3D anime. 古风客栈大堂，烛光暖黄。一个黑发年轻剑客推门走进来，背着长剑，环顾四周后走向角落的桌子坐下。画面跟随剑客移动。' \
  --out $EXPA/seg1.mp4 --duration 15 --ratio 9:16 &
PID_A=$!

python3 -u tools/seedance_gen.py \
  --prompt 'Genshin Impact style 3D anime, cel-shaded rendering with soft volumetric lighting. 一间古风客栈大堂，木质横梁和立柱构成主体结构，角落堆放着深褐色酒坛，二楼栏杆有雕花装饰。暖黄烛光从墙壁烛台投射，地面木板有使用痕迹。一个身穿深蓝色长袍、黑色长发束成高马尾的年轻剑客，背着一把带有青色流苏的长剑，推开木门走进客栈。他身高约175cm，体型偏瘦但肩宽，面容清秀带有一丝疲惫。他环顾四周，目光扫过其他桌客，然后迈步走向靠窗的角落桌子，拉开椅子坐下。摄像机从门口中景跟随至桌旁中近景。' \
  --out $EXPB/seg1.mp4 --duration 15 --ratio 9:16 &
PID_B=$!

wait $PID_A && echo "✓ 085a seg1 done" || echo "✗ 085a seg1 FAILED"
wait $PID_B && echo "✓ 085b seg1 done" || echo "✗ 085b seg1 FAILED"

# --- Seg2: extend (concurrent A + B) ---
echo "=== Seg2: extend ==="
# Strip audio
ffmpeg -y -i $EXPA/seg1.mp4 -an $EXPA/seg1-noaudio.mp4 2>/dev/null
ffmpeg -y -i $EXPB/seg1.mp4 -an $EXPB/seg1-noaudio.mp4 2>/dev/null

python3 -u tools/seedance_gen.py \
  --prompt 'Continuation of previous scene. 剑客坐在桌旁，抬手示意。店小二端着酒壶走过来，把酒倒入碗中。剑客点头致谢。' \
  --video $EXPA/seg1-noaudio.mp4 \
  --out $EXPA/seg2.mp4 --duration 15 --ratio 9:16 &
PID_A=$!

python3 -u tools/seedance_gen.py \
  --prompt 'Continuation of previous scene. 同一古风客栈内景，烛光氛围不变。深蓝色长袍黑发马尾剑客坐在靠窗角落桌旁，长剑靠在桌边。他抬起右手，向柜台方向微微招手示意。一个穿着灰褐色短褂、系白围裙的圆脸店小二，双手端着一只陶制酒壶和一只粗瓷酒碗，小跑着来到桌前。店小二弯腰将酒碗放在桌上，倾斜酒壶缓缓倒酒，琥珀色液体落入碗中。剑客微微点头致谢。中景固定机位。' \
  --video $EXPB/seg1-noaudio.mp4 \
  --out $EXPB/seg2.mp4 --duration 15 --ratio 9:16 &
PID_B=$!

wait $PID_A && echo "✓ 085a seg2 done" || echo "✗ 085a seg2 FAILED"
wait $PID_B && echo "✓ 085b seg2 done" || echo "✗ 085b seg2 FAILED"

# --- Seg3: extend (concurrent A + B) ---
echo "=== Seg3: extend ==="
ffmpeg -y -i $EXPA/seg2.mp4 -an $EXPA/seg2-noaudio.mp4 2>/dev/null
ffmpeg -y -i $EXPB/seg2.mp4 -an $EXPB/seg2-noaudio.mp4 2>/dev/null

python3 -u tools/seedance_gen.py \
  --prompt 'Continuation of previous scene. 剑客端起酒碗喝了一口，放下碗，露出满足的微笑。目光望向窗外，烛光在脸上跳动。' \
  --video $EXPA/seg2-noaudio.mp4 \
  --out $EXPA/seg3.mp4 --duration 15 --ratio 9:16 &
PID_A=$!

python3 -u tools/seedance_gen.py \
  --prompt 'Continuation of previous scene. 古风客栈角落桌旁，深蓝色长袍黑发马尾剑客面前摆着一碗酒。他双手端起粗瓷酒碗，仰头饮了一口，然后缓缓放下酒碗回到桌面。他的嘴角微微上扬，露出一个满足而放松的微笑，眼神柔和。他的目光转向右侧窗户，望向窗外。烛光在他脸庞左侧跳动，明暗交替。近景特写，微微推近到面部。' \
  --video $EXPB/seg2-noaudio.mp4 \
  --out $EXPB/seg3.mp4 --duration 15 --ratio 9:16 &
PID_B=$!

wait $PID_A && echo "✓ 085a seg3 done" || echo "✗ 085a seg3 FAILED"
wait $PID_B && echo "✓ 085b seg3 done" || echo "✗ 085b seg3 FAILED"

# --- Concat ---
echo "=== Concatenating ==="
python3 -u tools/ffmpeg_concat.py --inputs $EXPA/seg1.mp4 $EXPA/seg2.mp4 $EXPA/seg3.mp4 --out $EXPA/final.mp4 --check-audio --check-per-segment
python3 -u tools/ffmpeg_concat.py --inputs $EXPB/seg1.mp4 $EXPB/seg2.mp4 $EXPB/seg3.mp4 --out $EXPB/final.mp4 --check-audio --check-per-segment

echo "=== H-158 COMPLETE ==="
ls -lh $EXPA/final.mp4 $EXPB/final.mp4
