# V7-089: Prompt Length & Continuation Prefix 2×2 A/B Test (H-163 + H-164)

## Design
- **Group A**: Short prompt (~500 chars) + no continuation prefix  
- **Group B**: Short prompt (~500 chars) + with continuation prefix
- **Group C**: Long prompt (~800 chars) + no continuation prefix
- **Group D**: Long prompt (~800 chars) + with continuation prefix

## Common
- Style: Genshin Impact 3D animation
- Scene: Ancient Chinese inn, warm candlelight
- Character: Young man, black ponytail, dark blue robe, sword
- Plot: Enter inn → sit down, order tea → sip tea
- 3 Segment extend chain, 9:16, Chinese TTS dialogue
- Audio strip before extend (bug fix)

## Hypotheses
- **H-163**: Short prompt ≥ long prompt in visual quality
- **H-164**: Continuation prefix improves character consistency by ≥1.0 point

## Evaluation (1-10 per group)
1. Visual quality
2. Character consistency
3. Scene consistency
4. Motion naturalness
5. Overall coherence

## Runners
- keen-canyon: Group A + B (sequential)
- tidal-cove: Group C + D (sequential)
