# V7-099 Prompts — Multi-Character Dialogue (H-178)

## Hypothesis H-178
Two-character interaction with dialogue improves storytelling score ≥0.70 while maintaining character consistency across 3 segments.

## Story: 师徒对决 (Master vs Disciple)
- **Setting**: [INDOOR] Spacious ancient Chinese martial arts hall, wooden floor, weapon racks on both sides, warm sunset light through windows, ~100sqm with wooden pillars
- **Character A (Master)**: Middle-aged male, gray-white long hair in high ponytail, dark gray martial robe, tall imposing build, wooden sword
- **Character B (Disciple)**: Young male, short black hair, white training uniform, lean build, wooden sword

---

## Seg1 — 挑战 (text-to-video, Genshin 3D style)

```
A spacious ancient Chinese martial arts hall with polished wooden floor, weapon racks along both walls, warm golden sunset light streaming through tall windows, wooden pillars supporting the ceiling. A young lean male with short black hair wearing a white training uniform stands at center gripping a wooden sword, takes a deep breath, eyes fixed forward. Across from him, a tall imposing middle-aged male with gray-white long hair tied in a high ponytail wearing a dark gray martial robe slowly turns around holding a wooden sword, a slight smile on his lips. The young man raises his sword and points it at the master, eyes burning with determination. The master flicks his sword blade with one finger, producing a resonant hum, his expression shifting from amusement to seriousness. Genshin Impact 3D cel-shaded animation style, warm sunset lighting, cinematic wide to medium shot, martial arts tension. No subtitles, no text overlay, no slow motion.
```
Chars: ~796

Dialogue:
- 师父: "你确定准备好了？"
- 徒弟: "等这一天，等了三年。"

---

## Seg2 — 交锋 (extend from Seg1)

```
Continuation of previous scene. Same ancient martial arts hall, sunset light. Young male short black hair white training uniform charges forward swinging wooden sword horizontally. Tall middle-aged male gray-white ponytail dark gray robe sidesteps effortlessly, counters with a quick thrust toward the young man's shoulder. The young man barely blocks with his sword, staggers back two steps from the impact. He steadies himself, shifts strategy, begins circling cautiously looking for openings, expression changing from anxious to calm and focused. He suddenly accelerates, attacking from a low angle with an upward slash. The master's eyes flash with surprise. Genshin Impact 3D cel-shaded animation style, warm sunset lighting, dynamic combat cinematography. No subtitles, no text overlay, no slow motion.
```
Chars: ~770

Dialogue:
- 师父: "太急了。"

---

## Seg3 — 突破 (extend from Seg2)

```
Continuation of previous scene. Same martial arts hall. Tall middle-aged male gray-white ponytail dark gray robe blocks seriously for the first time, wooden swords clash with a sharp crack. Both men face each other at close range. Young male short black hair white uniform uses the rebound to spin and deliver a sweeping strike. The master blocks but is forced back one step. The master suddenly laughs heartily, sheathes his sword and clasps his fists in salute, face full of pride and warmth. The young man drops to one knee breathing heavily, bowing respectfully. The master walks forward and places a hand on his shoulder. Golden sunset bathes both figures. Genshin Impact 3D cel-shaded animation style, warm emotional sunset lighting, cinematic medium to close shot. No subtitles, no text overlay, no slow motion.
```
Chars: ~779

Dialogue:
- 徒弟: "这招，是您教的。"
- 师父: "好，三年没白费。"

---

## Audio Strategy
- TTS: Chinese Mandarin, male voices (YunxiNeural for both — differentiate via context)
- All dialogue must finish before 14s mark (1s silence buffer)
- ffmpeg -an strip before extend input
- Seg1 has 2 lines of dialogue, Seg2 has 1, Seg3 has 2
