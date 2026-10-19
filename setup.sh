#!/usr/bin/env bash
# First-time setup: Python deps for Tasks 1+3, Node deps + TS build for Task 2.
set -euo pipefail
cd "$(dirname "$0")"
echo "== Python deps (Tasks 1 & 3) =="
pip install -r task1-knowledge-brain/requirements.txt -r task3-meeting-to-scope/requirements.txt
echo "== Node deps + TypeScript build (Task 2) =="
(cd task2-inbox-agent && npm install && npm run build)
[ -f task2-inbox-agent/data/emails.json ] || { echo "ERROR: task2 dataset missing — restore data/emails.json from the repo"; exit 1; }
echo "Setup complete. Run ./run.sh"
