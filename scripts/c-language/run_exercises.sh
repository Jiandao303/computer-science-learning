#!/usr/bin/env bash
# 在 WSL / Linux 下编译并运行 C 语言练习，记录真实结果。
# 用法：bash scripts/c-language/run_exercises.sh
set -u

R="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$R/exercises/C-Language" || exit 1

FLAGS="-std=c11 -Wall -Wextra -Wpedantic -g -O0"
FAILED=0

compile_and_run() {
    local src="$1"
    local out="/tmp/$(basename "$src" .c)"
    echo "=== $src"
    if gcc $FLAGS "$src" -o "$out" 2>/tmp/cerr.txt; then
        echo "COMPILE OK"
        if [ -s /tmp/cerr.txt ]; then
            echo "WARNINGS:"; cat /tmp/cerr.txt
        fi
        "$out" || { echo "RUN FAILED (exit $?)"; FAILED=$((FAILED+1)); }
    else
        echo "COMPILE FAILED"
        cat /tmp/cerr.txt
        FAILED=$((FAILED+1))
    fi
    echo
}

for f in $(find Day-* -maxdepth 1 -name '*.c' | sort); do
    compile_and_run "$f"
done

echo "=== SUMMARY: failures=$FAILED"
exit "$FAILED"
