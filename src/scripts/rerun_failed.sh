#!/bin/bash
# Usage: sudo [same options as trace.sh] ./rerun_failed.sh <run_tag> [max_tries=3]
#
# bcc's filetop sometimes dies in the middle of a trace (BPF_MAP_LOOKUP_AND_DELETE_BATCH: No space left on device),
# which loses part of the filetop features. This finds every package of runs/<run_tag>/ whose meta.env says
# probe_died != none, traces it again (same duration) until no probe died, then replaces the old trace.
# If it still fails after max_tries, the old trace is kept and the package is listed at the end.
set -u
if [ "$(id -u)" -ne 0 ]; then echo "Must run with sudo"; exit 1; fi
if [ -z "${1:-}" ]; then echo "Usage: sudo ./rerun_failed.sh <run_tag> [max_tries=3]"; exit 1; fi
tag="$1"
tries="${2:-3}"
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"
run="runs/$tag"
[ -d "$run/traces" ] || { echo "No such run: $run"; exit 1; }

still=""
for meta in "$run"/traces/*/meta.env; do
    name="$(basename "$(dirname "$meta")")"
    died="$(grep '^probe_died=' "$meta" | cut -d= -f2-)"
    [ "$died" = none ] && continue
    duration="$(grep '^duration=' "$meta" | cut -d= -f2)"
    echo "######## $name: probe died ($died), duration ${duration}s, up to $tries tries"
    list="$(mktemp)"
    { head -1 "$run/packages.csv"; grep "^$name," "$run/packages.csv"; } > "$list"
    ok=0
    for i in $(seq 1 "$tries"); do
        retry="${tag}-retry"
        rm -rf "runs/$retry"
        bash src/scripts/trace_batch.sh "$list" "$retry" "$duration" < /dev/null
        new="runs/$retry/traces/$name/meta.env"
        if [ -f "$new" ] && grep -q '^probe_died=none' "$new"; then
            rm -rf "$run/traces/$name" "$run/outputs/$name"
            mv "runs/$retry/traces/$name" "$run/traces/$name"
            [ -d "runs/$retry/outputs/$name" ] && mv "runs/$retry/outputs/$name" "$run/outputs/$name"
            echo "######## $name: OK on try $i"
            ok=1
            break
        fi
        echo "######## $name: try $i failed again"
    done
    rm -f "$list"
    rm -rf "runs/${tag}-retry"
    [ "$ok" = 1 ] || still="$still $name"
done
echo "################ rerun finished. Still failing (old trace kept):${still:- none}"
