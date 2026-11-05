#!/bin/sh
# Full test cycle. Needs a display on Linux (run under xvfb-run),
# Python 3.10+ for the lab, and network for e2e. Usage:
# tests/run_all.sh [--no-e2e] [--no-lab] [--rounds N]
# Exit status is non-zero if any part fails.
set -u
# Each test starts native browser processes; match CI's default concurrency.
# Override explicitly when stress-testing concurrent sessions.
RUST_TEST_THREADS=${RUST_TEST_THREADS:-1}
export RUST_TEST_THREADS
E2E=1
LAB=1
ROUNDS=1
while [ $# -gt 0 ]; do
  case "$1" in
    --no-e2e) E2E=0 ;;
    --no-lab) LAB=0 ;;
    --rounds) ROUNDS="$2"; shift ;;
  esac
  shift
done
cd "$(dirname "$0")/.." || exit 1

status=0
run() {
  name=$1; shift
  if "$@" > "/tmp/bruster-test-$name.log" 2>&1; then
    echo "PASS $name"
  else
    echo "FAIL $name  (see /tmp/bruster-test-$name.log)"
    tail -n 30 "/tmp/bruster-test-$name.log"
    status=1
  fi
}

run build cargo build --release --locked --tests
run unit cargo test --release --locked --bin bruster
run testing cargo test --release --locked --test testing
i=1
while [ "$i" -le "$ROUNDS" ]; do
  run "smoke-$i" cargo test --release --locked --test smoke
  run "edge-$i" cargo test --release --locked --test edge
  i=$((i + 1))
done
if [ "$LAB" = 1 ]; then
  run test-lab cargo test --release --test test_lab
fi
# Process-tree hygiene: every bruster the tests spawned is gone.
sleep 1
if pgrep -f '^[^ ]*/bruster --hidden' > /dev/null; then
  echo "FAIL leftover bruster processes:"; pgrep -af '^[^ ]*/bruster --hidden'; status=1
else
  echo "PASS no leftover processes"
fi
BIN="${CARGO_TARGET_DIR:-target}/release/bruster"
run mcp-launch sh tests/mcp_launch.sh "$BIN" --hidden --mcp --quiet
if [ "$E2E" = 1 ]; then
  run e2e cargo test --release --test e2e -- --ignored --test-threads=2
  if [ "$LAB" = 1 ]; then
    run test-lab-published cargo test --release --test test_lab -- --ignored --exact published_test_lab
  fi
fi
exit $status
