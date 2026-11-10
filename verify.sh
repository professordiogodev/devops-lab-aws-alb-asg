#!/usr/bin/env bash
# Reads the real load balancer and group, then uses them. Run with: ./verify.sh
cd "$(dirname "$0")" || exit 1
aws sts get-caller-identity >/dev/null 2>&1 || { echo "No working AWS credentials." >&2; exit 1; }
exec python3 .lab/awscheck.py
