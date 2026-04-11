#!/bin/bash
set -e
cd ~/trinity-v7-consistency

echo "=== Waiting for V7-074/075/076 to finish before starting V7-077/078 ==="

# Wait for all three to have final.mp4
for exp in exp-v7-074 exp-v7-075 exp-v7-076; do
  while [ ! -f "experiments/$exp/output/final.mp4" ]; do
    sleep 60
    echo "  $(date +%H:%M) Waiting for $exp/final.mp4..."
  done
  echo "✓ $exp complete"
done

echo "=== All prerequisites done. Starting V7-077/078 ==="
bash experiments/shinkai-vs-genshin-runner.sh
