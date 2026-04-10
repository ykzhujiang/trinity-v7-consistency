# EXP-V7-026 Generation Log

## Experiment
- **ID**: EXP-V7-026
- **Hypothesis**: H-358 (同场景时间流逝双Segment一致性)
- **Cycle**: CYCLE-operator-885
- **Date**: 2026-04-11T03:03+08:00

## Assets (Gemini, concurrent)
| Asset | Style | Size | Time |
|-------|-------|------|------|
| chenmo-portrait | anime | 33KB | ~15s |
| wanglei-portrait | anime | 23KB | ~15s |
| office-daytime | anime | 57KB | ~15s |
| office-nighttime | anime | 26KB | ~15s |
| chenmo-portrait | realistic | 31KB | ~15s |
| wanglei-portrait | realistic | 20KB | ~15s |
| office-daytime | realistic | 37KB | ~20s (retry) |
| office-nighttime | realistic | 23KB | ~15s |

## Video Generation (Seedance 2.0, concurrent)

### Seg1 (anime + realistic concurrent)
| Track | Duration | Size | Gen Time |
|-------|----------|------|----------|
| anime-seg1 | 15.04s | 6.3MB | 531s |
| realistic-seg1 | 15.04s | 6.8MB | 228s |

### Seg2 (anime + realistic concurrent, video extension from Seg1)
| Track | Duration | Size | Gen Time |
|-------|----------|------|----------|
| anime-seg2 | 15.04s | 5.5MB | 801s |
| realistic-seg2 | 15.04s | 5.1MB | 556s |

### Prompt Strategy
- Seg1: Full scene + character description + action sequence + constraints (no slow-mo, no camera look, no subtitles)
- Seg2: Video extension mode — input Seg1 video + nighttime scene reference image + new action prompt
- Key constraint suffix: "Normal speed movements, natural pacing. No slow motion. Characters do not look at camera. No subtitles, no text overlay."

## Audio Check
- anime-seg1: ✅ audio 15.07s
- anime-seg2: ✅ audio 15.07s
- realistic-seg1: ✅ audio 15.07s
- realistic-seg2: ✅ audio 15.07s
- anime-final: ✅ 30.2s/30.1s (100%)
- realistic-final: ✅ 30.2s/30.1s (100%)

## Final Videos
- Anime: `experiments/exp-v7-026/output/anime/v7-026-anime-final.mp4`
- Realistic: `experiments/exp-v7-026/output/realistic/v7-026-realistic-final.mp4`

## No content moderation blocks encountered.
