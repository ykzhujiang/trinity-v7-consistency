# BUG: Seg2 No Audio in Concatenated Videos

## Affected
- EXP-V7-006 (D group), EXP-V7-009, EXP-V7-010, EXP-V7-011

## Root Cause
`ffmpeg -f concat -c copy` silently drops audio from the second segment.
The concat demuxer with stream copy mode fails to properly concatenate AAC audio streams
even when codec parameters (sample_rate=44100, channels=2, aac-lc) are identical.

Video stream concatenates fine, but audio duration = Seg1 only (~15s instead of ~30s).

## Fix (2026-04-10, Cycle 865)
Replaced `-c copy` with re-encode:
```
ffmpeg -f concat -safe 0 -i concat.txt \
  -c:v libx264 -preset fast -crf 18 \
  -c:a aac -b:a 128k \
  -movflags +faststart -y output.mp4
```

Added post-concat audio duration check: if audio_dur < video_dur * 0.9, fail loudly.

## Files Fixed
- `scripts/v7_pipeline.py` (main pipeline)
- `scripts/exp_v7_006_runner.py`

## Videos Re-concatenated
- exp-v7-010/anime, exp-v7-010/realistic
- exp-v7-011/anime, exp-v7-011/realistic

## Prevention
Pipeline now automatically verifies audio/video duration match after every concat.
