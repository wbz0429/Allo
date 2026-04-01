#!/usr/bin/env bash
#
# start.sh - Start all DeerFlow development services
#
# Must be run from the repo root directory.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

resolve_nginx_bin() {
    if command -v nginx >/dev/null 2>&1; then
        command -v nginx
        return 0
    fi

    for candidate in \
        "/opt/homebrew/bin/nginx" \
        "/opt/homebrew/opt/nginx/bin/nginx" \
        "/usr/local/bin/nginx" \
        "/opt/local/bin/nginx"
    do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    if command -v brew >/dev/null 2>&1; then
        local brew_prefix
        brew_prefix="$(brew --prefix nginx 2>/dev/null || true)"
        if [ -n "$brew_prefix" ] && [ -x "$brew_prefix/bin/nginx" ]; then
            printf '%s\n' "$brew_prefix/bin/nginx"
            return 0
        fi
    fi

    return 1
}

NGINX_BIN="$(resolve_nginx_bin || true)"

load_project_env() {
    eval "$(python3 - <<'PY'
from pathlib import Path
import shlex

env = {}
for path in [Path('.env'), Path('backend/.env')]:
    if not path.exists():
        continue
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        env[key] = value

for key, value in env.items():
    print(f'export {key}={shlex.quote(value)}')
PY
)"
}

# ── Argument parsing ─────────────────────────────────────────────────────────

DEV_MODE=true
for arg in "$@"; do
    case "$arg" in
        --dev)  DEV_MODE=true ;;
        --prod) DEV_MODE=false ;;
        *) echo "Unknown argument: $arg"; echo "Usage: $0 [--dev|--prod]"; exit 1 ;;
    esac
done

if $DEV_MODE; then
    FRONTEND_CMD="pnpm run dev"
    GATEWAY_ENV_PREFIX="ENV=development"
else
    FRONTEND_CMD="pnpm run preview"
    GATEWAY_ENV_PREFIX=""
fi

# ── Stop existing services ────────────────────────────────────────────────────

echo "Stopping existing services if any..."
pkill -f "langgraph dev" 2>/dev/null || true
pkill -f "uvicorn app.gateway.app:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
if [ -n "$NGINX_BIN" ]; then
    "$NGINX_BIN" -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
fi
sleep 1
pkill -9 nginx 2>/dev/null || true
killall -9 nginx 2>/dev/null || true
./scripts/cleanup-containers.sh deer-flow-sandbox 2>/dev/null || true
sleep 1

# ── Banner ────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo "  Starting DeerFlow Development Server"
echo "=========================================="
echo ""
if $DEV_MODE; then
    echo "  Mode: DEV  (hot-reload enabled)"
    echo "  Tip:  run \`make start\` in production mode"
else
    echo "  Mode: PROD (hot-reload disabled)"
    echo "  Tip:  run \`make dev\` to start in development mode"
fi
echo ""
echo "Services starting up..."
echo "  → Backend: LangGraph + Gateway"
echo "  → Frontend: Next.js"
echo "  → Nginx: Reverse Proxy"
echo ""

# ── Config check ─────────────────────────────────────────────────────────────

if ! { \
        [ -n "$DEER_FLOW_CONFIG_PATH" ] && [ -f "$DEER_FLOW_CONFIG_PATH" ] || \
        [ -f backend/config.yaml ] || \
        [ -f config.yaml ]; \
    }; then
    echo "✗ No DeerFlow config file found."
    echo "  Checked these locations:"
    echo "    - $DEER_FLOW_CONFIG_PATH (when DEER_FLOW_CONFIG_PATH is set)"
    echo "    - backend/config.yaml"
    echo "    - ./config.yaml"
    echo ""
    echo "  Run 'make config' from the repo root to generate ./config.yaml, then set required model API keys in .env or your config file."
    exit 1
fi

if [ -z "$NGINX_BIN" ]; then
    echo "✗ nginx not found in PATH or common Homebrew locations."
    echo "  Install with: brew install nginx"
    echo "  Or add nginx to PATH and rerun 'make dev'."
    exit 1
fi

# ── Auto-upgrade config ──────────────────────────────────────────────────

"$REPO_ROOT/scripts/config-upgrade.sh"

# ── Config preflight ──────────────────────────────────────────────────────

echo "Running config preflight..."
if (
    load_project_env
    cd backend
    PYTHONPATH=. uv run python - <<'PY'
from deerflow.config.app_config import AppConfig

cfg = AppConfig.from_file()
print(f"Config parsed successfully: models={len(cfg.models)}, tools={len(cfg.tools)}, tool_groups={len(cfg.tool_groups)}")

if not cfg.models:
    print("ERROR: No models configured in config.yaml")
    print("")
    print("Add at least one model under `models:`. Example for OpenAI-compatible GPT relay:")
    print("")
    print("models:")
    print("  - name: gpt-4o")
    print("    display_name: GPT-4o")
    print("    use: langchain_openai:ChatOpenAI")
    print("    model: gpt-4o")
    print("    api_base: https://YOUR-RELAY-BASE/v1")
    print("    api_key: $OPENAI_API_KEY")
    print("    supports_vision: true")
    raise SystemExit(2)
PY
) >/tmp/deerflow-config-preflight.log 2>&1
then
    echo "✓ Config preflight passed"
else
    echo "✗ Config preflight failed"
    if [ -f /tmp/deerflow-config-preflight.log ]; then
        sed 's/^/  /' /tmp/deerflow-config-preflight.log
    else
        echo "  No preflight log was produced."
    fi
    echo ""
    echo "Hint: local development still needs one model configured in config.yaml."
    exit 1
fi

if $DEV_MODE; then
    echo "Seeding local development auth user..."
    if (
        load_project_env
        cd backend
        PYTHONPATH=. uv run python dev_seed_auth_user.py
    ) >/tmp/deerflow-dev-seed.log 2>&1; then
        sed 's/^/  /' /tmp/deerflow-dev-seed.log
    else
        echo "✗ Failed to seed local development auth user"
        if [ -f /tmp/deerflow-dev-seed.log ]; then
            sed 's/^/  /' /tmp/deerflow-dev-seed.log
        fi
        exit 1
    fi
fi

# ── Cleanup trap ─────────────────────────────────────────────────────────────

cleanup() {
    trap - INT TERM
    echo ""
    echo "Shutting down services..."
    pkill -f "langgraph dev" 2>/dev/null || true
    pkill -f "uvicorn app.gateway.app:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "next start" 2>/dev/null || true
    pkill -f "next-server" 2>/dev/null || true
    # Kill nginx using the captured PID first (most reliable),
    # then fall back to pkill/killall for any stray nginx workers.
    if [ -n "${NGINX_PID:-}" ] && kill -0 "$NGINX_PID" 2>/dev/null; then
        kill -TERM "$NGINX_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$NGINX_PID" 2>/dev/null || true
    fi
    if [ -n "$NGINX_BIN" ]; then
        "$NGINX_BIN" -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
    fi
    pkill -9 nginx 2>/dev/null || true
    killall -9 nginx 2>/dev/null || true
    echo "Cleaning up sandbox containers..."
    ./scripts/cleanup-containers.sh deer-flow-sandbox 2>/dev/null || true
    echo "✓ All services stopped"
    exit 0
}
trap cleanup INT TERM

# ── Start services ────────────────────────────────────────────────────────────

mkdir -p logs

if $DEV_MODE; then
    LANGGRAPH_EXTRA_FLAGS=""
    GATEWAY_EXTRA_FLAGS="--reload --reload-include='*.yaml' --reload-include='.env'"
else
    LANGGRAPH_EXTRA_FLAGS="--no-reload"
    GATEWAY_EXTRA_FLAGS=""
fi

echo "Starting LangGraph server..."
(load_project_env && cd backend && env NO_COLOR=1 uv run langgraph dev --no-browser --allow-blocking $LANGGRAPH_EXTRA_FLAGS > ../logs/langgraph.log 2>&1) &
./scripts/wait-for-port.sh 2024 60 "LangGraph" "logs/langgraph.log" || {
    echo "  See logs/langgraph.log for details"
    tail -20 logs/langgraph.log
    if grep -qE "config_version|outdated|Environment variable .* not found|KeyError|ValidationError|config\.yaml" logs/langgraph.log 2>/dev/null; then
        echo ""
        echo "  Hint: This may be a configuration issue. Try running 'make config-upgrade' to update your config.yaml."
    fi
    cleanup
}
echo "✓ LangGraph server started on localhost:2024"

echo "Starting Gateway API..."
(load_project_env && cd backend && env $GATEWAY_ENV_PREFIX PYTHONPATH=. uv run uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001 $GATEWAY_EXTRA_FLAGS > ../logs/gateway.log 2>&1) &
./scripts/wait-for-port.sh 8001 30 "Gateway API" "logs/gateway.log" || {
    echo "✗ Gateway API failed to start. Last log output:"
    tail -60 logs/gateway.log
    echo ""
    echo "Likely configuration errors:"
    grep -E "Failed to load configuration|Environment variable .* not found|config\.yaml.*not found" logs/gateway.log | tail -5 || true
    echo ""
    echo "  Hint: Try running 'make config-upgrade' to update your config.yaml with the latest fields."
    cleanup
}
echo "✓ Gateway API started on localhost:8001"

echo "Starting Frontend..."
(cd frontend && $FRONTEND_CMD > ../logs/frontend.log 2>&1) &
./scripts/wait-for-port.sh 3000 120 "Frontend" "logs/frontend.log" || {
    echo "  See logs/frontend.log for details"
    tail -20 logs/frontend.log
    cleanup
}
echo "✓ Frontend started on localhost:3000"

echo "Starting Nginx reverse proxy..."
"$NGINX_BIN" -g 'daemon off;' -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" > logs/nginx.log 2>&1 &
NGINX_PID=$!
./scripts/wait-for-port.sh 2026 10 "Nginx" "logs/nginx.log" || {
    echo "  See logs/nginx.log for details"
    tail -10 logs/nginx.log
    cleanup
}
echo "✓ Nginx started on localhost:2026"

# ── Ready ─────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
if $DEV_MODE; then
    echo "  ✓ DeerFlow development server is running!"
else
    echo "  ✓ DeerFlow production server is running!"
fi
echo "=========================================="
echo ""
echo "  🌐 Application: http://localhost:2026"
echo "  📡 API Gateway: http://localhost:2026/api/*"
echo "  🤖 LangGraph:   http://localhost:2026/api/langgraph/*"
echo ""
echo "  📋 Logs:"
echo "     - LangGraph: logs/langgraph.log"
echo "     - Gateway:   logs/gateway.log"
echo "     - Frontend:  logs/frontend.log"
echo "     - Nginx:     logs/nginx.log"
echo ""
echo "Press Ctrl+C to stop all services"

wait
