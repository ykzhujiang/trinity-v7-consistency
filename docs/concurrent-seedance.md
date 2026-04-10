# Concurrent Seedance Generation

**Date**: 2026-04-10
**Status**: Implemented starting from EXP-V7-014

## Problem
Serial Seedance calls: Seg1 anime → wait 3-5min → Seg1 realistic → wait → Seg2 anime → wait → Seg2 realistic → wait = ~20min total.

## Solution
**Phase-based concurrency** using `ThreadPoolExecutor`:

```
Phase 1 (parallel): anime-Seg1 + realistic-Seg1
                         ↓ both complete
Phase 2 (parallel): anime-Seg2 + realistic-Seg2
```

### Constraints
- Seg2 depends on Seg1 (Video Extension needs Seg1 video) → phases are sequential
- Within each phase, different styles run in parallel → 2x speedup
- Total time: ~10min instead of ~20min

## Implementation
- `scripts/concurrent_seedance.py` — reusable utility module
- `scripts/exp_v7_014_runner.py` — first experiment using built-in concurrency

## Usage Pattern
```python
with ThreadPoolExecutor(max_workers=2) as pool:
    futures = {pool.submit(_run_seg1, style, ...): style for style in styles}
    for future in as_completed(futures):
        style, result, path = future.result()
```

## Moderation Handling
Per standing order: if any track hits moderation → immediately abandon that track, continue others.
