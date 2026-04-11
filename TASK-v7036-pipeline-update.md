# V7-036 Pipeline Update Task

## Goal
Update `~/trinity-v7-consistency/scripts/v7_pipeline.py` to support N segments (not just 2) and apply V7-032 success template fixes.

## Required Changes

### 1. Support N Segments
Currently the pipeline hardcodes Seg1 + Seg2. Change to loop over all parsed segments:
- Seg1: independent generation (current behavior)
- Seg2..N: video extension from previous segment

### 2. V7-032 Template Fixes (CRITICAL)
For Seg2+ prompts:
- **Must include character reference images** (not just video_ref) — pass them via `--image` args
- **Must copy Seg1 character description verbatim** into Seg2+ prompts
- Use template: `Same [Seg1 character desc]. Continuing in the same [Seg1 scene desc]. [new actions]`

### 3. Prompt Length Constraint
- Each segment prompt should be ≤ 800 characters

### 4. Concat N Segments
Update the ffmpeg concat to handle N segments (not just 2). Re-encode with proper audio.

### 5. Audio Check per Segment
After concat, verify each segment has audio using ffprobe.

### 6. Generation Log
Save complete generation log including all segment prompts, parameters, and timing.

## Constraints
- Don't break existing 2-segment functionality
- Keep the CLI interface: `--storyboard`, `--mode`, `--style`, `--output-dir`
- Use `python3 -u` for unbuffered output
- Concurrent generation where possible: anime Seg1 + realistic Seg1 can be parallel
- But Seg2 depends on Seg1 (video extension), so those are serial within a track

## Test
After changes, verify with: `python3 -u scripts/v7_pipeline.py --help`
