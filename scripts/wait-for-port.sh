#!/usr/bin/env bash
#
# wait-for-port.sh - Wait for a TCP port to become available
#
# Usage: ./scripts/wait-for-port.sh <port> [timeout_seconds] [service_name] [log_file]
#
# Arguments:
#   port             - TCP port to wait for (required)
#   timeout_seconds  - Max seconds to wait (default: 60)
#   service_name     - Display name for messages (default: "Service")
#   log_file         - Optional log file to tail while waiting
#
# Exit codes:
#   0 - Port is listening
#   1 - Timed out waiting

PORT="${1:?Usage: wait-for-port.sh <port> [timeout] [service_name] [log_file]}"
TIMEOUT="${2:-60}"
SERVICE="${3:-Service}"
LOG_FILE="${4:-}"

elapsed=0
interval=1
last_log_lines=0

is_port_listening() {
    if command -v lsof >/dev/null 2>&1; then
        if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 0
        fi
    fi

    if command -v ss >/dev/null 2>&1; then
        if ss -ltn "( sport = :$PORT )" 2>/dev/null | tail -n +2 | grep -q .; then
            return 0
        fi
    fi

    if command -v netstat >/dev/null 2>&1; then
        if netstat -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "(^|[.:])${PORT}$"; then
            return 0
        fi
    fi

    if command -v timeout >/dev/null 2>&1; then
        timeout 1 bash -c "exec 3<>/dev/tcp/127.0.0.1/$PORT" >/dev/null 2>&1
        return $?
    fi

    return 1
}

# Show new log lines since last check
show_new_logs() {
    if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
        return
    fi
    local current_lines
    current_lines=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$current_lines" -gt "$last_log_lines" ]; then
        local new_count=$((current_lines - last_log_lines))
        # Show at most 5 new lines per tick to avoid flooding
        tail -n "$new_count" "$LOG_FILE" 2>/dev/null | tail -5 | while IFS= read -r line; do
            # Strip ANSI color codes for cleaner output
            clean=$(echo "$line" | sed 's/\x1b\[[0-9;]*m//g' 2>/dev/null || echo "$line")
            # Truncate long lines
            if [ ${#clean} -gt 120 ]; then
                clean="${clean:0:117}..."
            fi
            printf "    %s\n" "$clean"
        done
        last_log_lines=$current_lines
    fi
}

# Check for errors in log
check_log_errors() {
    if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
        return 1
    fi
    if grep -qiE "Error|Exception|Traceback|FAILED|FATAL" "$LOG_FILE" 2>/dev/null; then
        return 0
    fi
    return 1
}

printf "  Waiting for %s on port %s " "$SERVICE" "$PORT"

while ! is_port_listening; do
    if [ "$elapsed" -ge "$TIMEOUT" ]; then
        echo ""
        echo "  ✗ $SERVICE failed to start on port $PORT after ${TIMEOUT}s"
        if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
            echo ""
            echo "  Last 15 lines of $LOG_FILE:"
            tail -15 "$LOG_FILE" 2>/dev/null | sed 's/^/    /'
        fi
        exit 1
    fi

    # Print a dot every 5 seconds as heartbeat
    if [ $((elapsed % 5)) -eq 0 ] && [ "$elapsed" -gt 0 ]; then
        printf "."
        # Every 10 seconds, show recent log activity
        if [ $((elapsed % 10)) -eq 0 ]; then
            echo " (${elapsed}s)"
            show_new_logs
            printf "  Waiting for %s on port %s " "$SERVICE" "$PORT"
        fi
    fi

    # Early exit if log shows fatal errors
    if [ "$elapsed" -gt 5 ] && check_log_errors; then
        # Only bail if the process is no longer running
        if [ -n "$LOG_FILE" ]; then
            local_proc=$(lsof -nP -iTCP:"$PORT" -t 2>/dev/null || true)
            if [ -z "$local_proc" ] && grep -qiE "Traceback|FATAL" "$LOG_FILE" 2>/dev/null; then
                echo ""
                echo "  ✗ $SERVICE appears to have crashed. Log output:"
                tail -30 "$LOG_FILE" 2>/dev/null | sed 's/^/    /'
                exit 1
            fi
        fi
    fi

    sleep "$interval"
    elapsed=$((elapsed + interval))
done

printf " OK (%ds)\n" "$elapsed"
