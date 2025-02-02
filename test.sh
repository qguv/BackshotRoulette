#!/bin/sh
set -e

for f in example_logs/*.*; do
    python3 parse_log.py "$f"
done

for f in example_logs/errors/**/*.*; do
    echo
    if python3 parse_log.py "$f"; then
        echo test failed: expected error!
    fi
done

echo
echo =================
echo all tests passed!
echo =================
