# EXP-V7-008 Generation Log

## Experiment Info
- **Date**: 2026-04-10
- **Cycle**: CYCLE-operator-854
- **Purpose**: SeeDance 2.0 Semi-Realistic style exploration (3 styles × 2 segments)
- **Storyboard**: 闪送小哥（小刘+林姐）

## Reference Images
All generated with Gemini 3 Pro Image (via king.tokenssr.com proxy).

| Style | Character | File |
|-------|----------|------|
| A: Cinematic CG | 小刘 | style-a-cinematic-cg/assets/xiaoliu.png |
| A: Cinematic CG | 林姐 | style-a-cinematic-cg/assets/linjie.png |
| A: Cinematic CG | 场景 | style-a-cinematic-cg/assets/scene.png |
| B: Hyper-Anime | 小刘 | style-b-hyper-anime/assets/xiaoliu.png |
| B: Hyper-Anime | 林姐 | style-b-hyper-anime/assets/linjie.png |
| B: Hyper-Anime | 场景 | style-b-hyper-anime/assets/scene.png |
| C: Semi-Realistic | 小刘 | style-c-semi-realistic/assets/xiaoliu.png |
| C: Semi-Realistic | 林姐 | style-c-semi-realistic/assets/linjie.png |
| C: Semi-Realistic | 场景 | style-c-semi-realistic/assets/scene.png |

## Video Generation

### Privacy Filter Issue
- Style A (CG) and C (Semi-realistic) reference images triggered `PrivacyInformation` error when used as multimodal refs
- **Workaround**: Style A and C used **text-only mode** (no image refs, detailed character descriptions in prompt)
- Style B (Anime) images passed the filter — used **multimodal reference mode** with all 3 images

### Task IDs

| Style | Segment | Task ID | Mode | Status |
|-------|---------|---------|------|--------|
| A: Cinematic CG | 1 | cgt-20260410050038-clqc2 | text-only | submitted |
| A: Cinematic CG | 2 | cgt-20260410050038-nsp6s | text-only | submitted |
| B: Hyper-Anime | 1 | cgt-20260410045953-cfzx4 | multimodal ref (3 imgs) | submitted |
| B: Hyper-Anime | 2 | cgt-20260410050035-h7xqp | multimodal ref (3 imgs) | submitted |
| C: Semi-Realistic | 1 | cgt-20260410050038-rcdj9 | text-only | submitted |
| C: Semi-Realistic | 2 | cgt-20260410050039-srl9f | text-only | submitted |

### Prompt Strategy
- All prompts include style prefix (e.g. "cinematic CG animation, movie-quality 3D rendering")
- Dialogue in Chinese with 说：format for voice sync
- Constraint suffix: "Normal speed, no slow-mo, no facing camera, no subtitles"
- Duration: 15s per segment, 9:16 vertical, 720p
- Audio generation enabled (default)

### Key Observation
SeeDance privacy filter blocks CG and semi-realistic character reference images (too close to real faces). This confirms the need for Asset Library integration to bypass the filter. For now, text-only generation is the fallback — but character consistency will be weaker without image anchoring.
