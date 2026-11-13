#!/bin/bash
# Usage: sudo ./run_all_nt230.sh [part]
# Runs every trace run NT230 needs, one after another (about 1h50 in total). Part = which runs:
#   core  : d120-fake (21 packages) + delayed-120 + delayed-300     (about 55 min)  -> what Hung and Dang are waiting for
#   sens  : d60-fake + d300-fake (8 packages each)                  (about 55 min)  -> sensitivity table
#   all   : core, then sens   (default)
# Each run is independent: if the VM stops, re-run only the missing part. Finished runs are skipped.
set -u
if [ "$(id -u)" -ne 0 ]; then echo "Must run with sudo"; exit 1; fi
part="${1:-all}"
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"
chmod +x src/scripts/*.sh
export OFFLINE=1 NETMODE=fake DECOYS=1

run() {  # run <list> <tag> <seconds>
    if [ -f "results/runs/$2/packages.csv" ] && [ "$(ls "results/runs/$2/traces" 2>/dev/null | wc -l)" -ge "$(( $(wc -l < "$1") - 1 ))" ]; then
        echo "### skip $2 (already done)"; return
    fi
    echo "################ $2 ($3 s) $(date '+%F %T')"
    rm -rf "results/runs/$2"
    bash src/scripts/trace_batch.sh "$1" "$2" "$3"
}

if [ "$part" = core ] || [ "$part" = all ]; then
    run data/packages.csv d120-fake 120
    run data/packages_delayed.csv delayed-120 120
    run data/packages_delayed.csv delayed-300 300
fi
if [ "$part" = sens ] || [ "$part" = all ]; then
    run data/packages_sens.csv d60-fake 60
    run data/packages_sens.csv d300-fake 300
fi
echo "################ DONE $(date '+%F %T')"
ls runs
iptables -L OUTPUT | grep -c DYSEC_NET | sed 's/^/DYSEC_NET rules left (must be 0): /'
