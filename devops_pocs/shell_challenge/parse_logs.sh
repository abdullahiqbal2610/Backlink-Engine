#!/bin/bash

# 1. Using a pipe to count log lines containing a specific word
LOG_FILE="dummy_logs.txt"
SEARCH_WORD="timeout"

echo "=== Log Parsing POC ==="
COUNT=$(grep -ri "$SEARCH_WORD" $LOG_FILE | wc -l)
echo "Found $COUNT lines containing '$SEARCH_WORD' in $LOG_FILE."

# 2. Setting and printing an environment variable
export POC_ENV_VAR="DevOps_Challenge_Completed"
echo "The environment variable POC_ENV_VAR is set to: $POC_ENV_VAR"
