#!/usr/bin/env bash
# 手动触发 Feiladin/rankings 的 Update rankings workflow
# 用法：
#   export GITHUB_TOKEN=ghp_xxx   # 或写入 .env（已 gitignore）
#   ./scripts/dispatch-actions.sh
#   ./scripts/dispatch-actions.sh --status
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${REPO:-Feiladin/rankings}"
WORKFLOW="${WORKFLOW:-update.yml}"
REF="${REF:-main}"

# 读取 token：优先环境变量，其次 .env
if [[ -z "${GITHUB_TOKEN:-}" && -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$ROOT/.env"
  set +a
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "错误：未设置 GITHUB_TOKEN（export GITHUB_TOKEN=... 或写入 $ROOT/.env）" >&2
  exit 1
fi

api() {
  local method="$1" path="$2"
  shift 2
  curl -sS -X "$method" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@" \
    "https://api.github.com${path}"
}

if [[ "${1:-}" == "--status" ]]; then
  echo "== 最近 runs（${REPO}/${WORKFLOW}）=="
  api GET "/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?per_page=5" \
    | python3 -c '
import json,sys
d=json.load(sys.stdin)
runs=d.get("workflow_runs") or []
if not runs:
    print("(暂无 runs)")
for r in runs:
    created = r.get("created_at", "")
    status = r.get("status") or "-"
    conclusion = r.get("conclusion") or "-"
    url = r.get("html_url") or ""
    print("%s  %-10s  %-10s  %s" % (created, status, conclusion, url))
'
  exit 0
fi

echo "触发 workflow: ${REPO} / ${WORKFLOW} @ ${REF}"
code=$(curl -sS -o /tmp/dispatch_body.txt -w "%{http_code}" -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
  -d "{\"ref\":\"${REF}\"}")

echo "HTTP ${code}"
if [[ "$code" != "204" ]]; then
  echo "响应：" >&2
  cat /tmp/dispatch_body.txt >&2
  exit 1
fi

echo "已触发。约 10 秒后查看最近 runs："
sleep 10
api GET "/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?per_page=3" \
  | python3 -c '
import json,sys
d=json.load(sys.stdin)
runs=d.get("workflow_runs") or []
if not runs:
    print("(尚未出现 run，稍后再 --status)")
for r in runs:
    created = r.get("created_at", "")
    status = r.get("status") or "-"
    conclusion = r.get("conclusion") or "-"
    url = r.get("html_url") or ""
    print("%s  %-10s  %-10s  %s" % (created, status, conclusion, url))
'
