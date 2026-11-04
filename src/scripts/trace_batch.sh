#!/bin/bash
# Usage: sudo [same options as trace.sh] ./trace_batch.sh <list.csv> <run_tag> [seconds=120]
#
# Traces every package of <list.csv> (columns: name,spec,label,group) one after another and
# moves each result to runs/<run_tag>/ so that runs with different settings never overwrite
# each other. Between two packages, leftovers of the simulated packages are removed
# (background processes, markers, dropped files) so they do not leak into the next trace.
# Real malicious packages must NOT be run with this script: trace them one by one and
# revert the VM snapshot after each (see SAFETY.md).
set -u

if [ $# -lt 2 ]; then
    echo "Usage: sudo [OFFLINE=1] [NETMODE=...] [STRACE=...] ./trace_batch.sh <list.csv> <run_tag> [seconds=120]"
    exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "Must run with sudo"
    exit 1
fi

list="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
tag="$2"
duration="${3:-120}"
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"
run="runs/${tag}"
mkdir -p "$run/traces" "$run/outputs"
cp "$list" "$run/packages.csv"

cleanup() {
    pkill -f dysec_sim_markers 2>/dev/null
    rm -rf /tmp/dysec_sim_markers /tmp/dysec_dropped_payload.py /tmp/benign-cext_build \
        "$HOME/.config/benign-config"
}

tail -n +2 "$list" | while IFS=, read -r name spec label group; do
    case "$name" in ""|\#*) continue ;; esac
    echo "=================== [$tag] $name ($spec, label=$label) ==================="
    cleanup
    bash "$base/src/scripts/trace.sh" "$spec" "$duration" < /dev/null
    rm -rf "$run/traces/$name" "$run/outputs/$name"
    src="$(basename "${spec%/}")"
    mv "traces/$src" "$run/traces/$name"
    # files are named after what was installed (e.g. requests-2.34.2.tar.gz_...); rename to the list name
    if [ "$src" != "$name" ]; then
        for f in "$run/traces/$name/${src}"_*; do
            [ -e "$f" ] && mv "$f" "$run/traces/$name/${name}_${f##*/${src}_}"
        done
    fi
    mv "outputs/$(basename "${spec%/}")" "$run/outputs/$name" 2>/dev/null
done
cleanup
echo "[+] Run saved in $run. Next: python3 src/collect.py $run"
