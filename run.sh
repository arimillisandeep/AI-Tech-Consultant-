#!/usr/bin/env bash
# One-command run: Knowledge Brain first (Tasks 2 & 3 depend on its API).
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
export KNOWLEDGE_BRAIN_URL="${KNOWLEDGE_BRAIN_URL:-http://127.0.0.1:8000}"
cleanup() { kill $(jobs -p) 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd task1-knowledge-brain && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
echo "Waiting for Knowledge Brain…"
for i in $(seq 1 30); do curl -fs http://127.0.0.1:8000/health >/dev/null 2>&1 && break || sleep 1; done

[ -d task2-inbox-agent/dist ] || (cd task2-inbox-agent && npm run build)
(cd task2-inbox-agent && INBOX_PORT=3001 node dist/server.js) &
(cd task3-meeting-to-scope && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001) &

cat <<EOF

  🧠 Knowledge Brain   http://localhost:8000   (API docs /docs)
  📥 Inbox Agent       http://localhost:3001
  📐 Meeting to Scope  http://localhost:8001

  Ctrl-C stops all three.
EOF
wait
