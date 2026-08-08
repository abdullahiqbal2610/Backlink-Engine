#!/bin/bash
set -e

echo "=== 1. Running Discovery Engine ==="
python discovery/main.py

echo "=== 2. Running LLM Pipeline ==="
python llm_pipeline/worker.py

echo "=== Worker Job Complete ==="
