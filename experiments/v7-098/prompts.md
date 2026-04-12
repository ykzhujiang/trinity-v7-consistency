# V7-098 Prompts — Dramatic Action Verbs in Extend Chain

## Hypothesis H-177
Dramatic, high-energy action verbs in extend prompts increase visual storytelling score ≥0.70 while maintaining consistency ≥0.90.

## Story: 深夜代码 (Late Night Code)
- **Setting**: [INDOOR] Small startup studio, 3 monitors with code, city nightscape outside, takeout boxes and energy drinks on desk, cold white monitor glow
- **Character**: Young male programmer, short hair, black-rimmed glasses, black hoodie, ~25 years old

---

## Seg1 — 困境 (text-to-video, Genshin 3D style)

```
A young male programmer with short black hair, black-rimmed glasses, and a black hoodie sits hunched in front of three glowing monitors displaying red error messages in a small dimly lit startup studio. City nightscape visible through the window behind him. Empty takeout boxes and crushed energy drink cans scattered on the desk. Cold white monitor light illuminates his exhausted face. He slowly rubs his tired eyes with both hands, reaches for an energy drink can, takes a long sip, then suddenly slams the empty can down on the desk with frustration. He mutters through gritted teeth. Genshin Impact 3D cel-shaded animation style, cold blue-white monitor lighting with warm city lights in background, cinematic medium shot, tense coding atmosphere. No subtitles, no text overlay, no slow motion.
```
Chars: ~770

Dialogue: "三天了……三天三夜，Bug还是找不到。服务器明天就要上线，我到底在干什么……"

---

## Seg2 — 转折 ⚡ HIGH-ENERGY VERBS (extend from Seg1)

```
Continuation of previous scene. Same young male programmer with short black hair, black-rimmed glasses, black hoodie. All three monitors suddenly flash green — tests passing. His eyes go wide. He springs up explosively from the chair, the rolling chair crashes backward into the wall. He clenches both fists and thrusts them overhead, mouth open in a triumphant shout. He spins around and kicks a takeout box on the floor, sending it flying across the room. Papers scatter from the desk. His whole body trembles with adrenaline and disbelief. Genshin Impact 3D cel-shaded animation style, monitors now casting green light on the room, explosive celebratory energy, cinematic dynamic angles. No subtitles, no text overlay, no slow motion.
```
Chars: ~748

Dialogue: "过了！！！全绿了！三天的Bug终于过了！！哈哈哈——"

---

## Seg3 — 升华 ⚡ EMOTION CONTRAST (extend from Seg2)

```
Continuation of previous scene. Same young male programmer with short black hair, black-rimmed glasses, black hoodie. He slowly sinks back into the chair which is now slightly crooked. He takes a deep shaky breath, his racing heartbeat visibly calming. A subtle smile creeps across his face. He picks up his phone from the desk, his hand trembling slightly. He dials a number, brings the phone to his ear, opens his mouth to speak but his voice cracks. His eyes redden and glisten with tears he fights to hold back. He swallows hard, forces a smile, and speaks with a trembling voice. Genshin Impact 3D cel-shaded animation style, warm green monitor glow, intimate close-up to medium shot, quiet emotional aftermath. No subtitles, no text overlay, no slow motion.
```
Chars: ~750

Dialogue: "哥们……我们的东西……跑通了。三年了，从车库到现在，终于跑通了。"

---

## Audio Strategy
- TTS: Chinese Mandarin, male voice
- Seg1 台词在14秒前说完（留1秒静默缓冲）
- Seg2 台词在14秒前说完
- Seg3 台词在14秒前说完
- ffmpeg -an strip before extend input
