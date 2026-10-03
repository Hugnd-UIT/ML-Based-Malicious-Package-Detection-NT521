#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: monitor.sh <package_name>"
    exit 1
fi

pkg=$1

out="outputs/${pkg}"
rm -rf "$out"
mkdir -p "$out"

pids="PIDs"
mkdir -p "$pids"
pids_file="${pids}/${pkg}.txt"
rm -f "$pids_file"
touch "$pids_file"

trap 'pkill -P $$ strace 2>/dev/null; echo "monitor.sh: stopped"; exit 0' INT TERM

trace() {
    local pid=$1
    echo "$pid" >> "$pids_file"
    strace -f -ff -o "${out}/${pid}" -s 4096 -t -v -p "$pid" 2>/dev/null &
    echo "Tracing PID $pid ($2)"
}

check() {
    grep -q "^$1$" "$pids_file"
}

echo "Monitoring package $pkg ..."
while true; do
    for proc in python python3 pip pip3; do
        for pid in $(pgrep -x "$proc"); do
            if ! check "$pid"; then
                trace "$pid" "$proc"
            fi
        done
    done
    sleep 1
done