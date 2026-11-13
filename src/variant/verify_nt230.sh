#!/bin/bash
# NT230 runs: same packages, order, exclusion rules and scoring as lap E (src/variant/verify_mix.sh),
# but under the NT230 sandbox settings. Rules: docs/protocols/PROTOCOL-NT230.md. VM ONLY, revert after.
#
#   sudo TAG=F1 NETMODE=mirror systemd-inhibit --what=sleep:idle --why=dysec bash src/variant/verify_nt230.sh 2>&1 | tee -a F1.log
#
# Environment:
#   TAG       run name, required (F1, F2, ...). Output files: <TAG>_ben_*, <TAG>_mal_*, <TAG>_out.tar.gz
#   NETMODE   off | fake | mirror, required (YC_R49: network disabled or simulated)
#   LIST      "B name" / "M name-version" lines, default data/mix-lapE.txt (270 packages of lap E)
#   DURATION  seconds per package, default 120 (paper)
#   PIPARGS   extra pip options, e.g. --no-deps
# Needs wheelhouse/ and the malicious archives from src/scripts/prepare_mirror.sh.
# Resumable: run again after a stop, packages already measured are skipped.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
: "${TAG:?set TAG, e.g. TAG=F1}"
: "${NETMODE:?set NETMODE=off|fake|mirror}"
case "$NETMODE" in off|fake) export OFFLINE=1 ;; mirror) ;; *) echo "NETMODE must be off, fake or mirror"; exit 1 ;; esac
export NETMODE
LIST="${LIST:-data/mix-lapE.txt}"
DURATION="${DURATION:-120}"
export PIPARGS="${PIPARGS:-}"
[ -d wheelhouse/python3 ] && [ -d wheelhouse/python3.8 ] || { echo "Missing wheelhouse: run src/scripts/prepare_mirror.sh first"; exit 1; }

echo "=== START $(date) | $TAG | NETMODE=$NETMODE DURATION=$DURATION PIPARGS='$PIPARGS' LIST=$LIST | $(nproc) CPU | $(uname -r) | $(. /etc/os-release && echo "$PRETTY_NAME") | commit $(git log --oneline -1 2>/dev/null)"
# use the committed variant models; train only if they are missing
[ -f models/variant/rf_drop_g1g2.pkl ] && [ -f models/variant/rf_drop_g1g2g3.pkl ] || python3 src/variant/train_variant.py || exit 1
sha256sum models/variant/*.pkl models/Random-Forest.pkl
if command -v vmware-hgfsclient >/dev/null && [ -n "$(vmware-hgfsclient 2>/dev/null)" ]; then echo "!!! Shared Folders on: stop"; exit 1; fi
if grep -qs hgfs /proc/mounts; then echo "!!! hgfs mounted: stop"; exit 1; fi
echo "=== malicious archives present: $(while read -r k n; do [ "$k" = M ] && [ -s "$n.tar.gz" ] && echo; done < "$LIST" | wc -l)/$(grep -c '^M ' "$LIST")"

run_list() {  # run_list <file with "B name"/"M name" lines> <suffix>
    local n=0 total kind name pkg py out
    total=$(wc -l < "$1")
    while read -r kind name; do
        name=${name%%[[:space:]]}; n=$((n + 1))
        if [ "$kind" = B ]; then pkg=$name; py=python3; out=${TAG}_ben$2
        else pkg=$name.tar.gz; py=python3.8; out=${TAG}_mal$2; [ -s "$pkg" ] || continue; fi
        grep -qs "^$pkg," "${out}_results.csv" && continue
        echo "--- [$n/$total] $kind $pkg ($(date '+%T'))"
        echo "$pkg" > "${TAG}_one.txt"
        PYTHON=$py python3 src/batch.py "${TAG}_one.txt" --duration "$DURATION" \
            --out "${out}_results.csv" --features "${out}_features.csv" < /dev/null | grep -v '^\[1/1\]'
    done < "$1"
}

run_list "$LIST" ""
# Same exclusion rule as lap C/D/E: probe died, or strace attached more than 10 s late -> re-run (max 2 times)
for i in 1 2; do
    TAG="$TAG" LIST="$LIST" python3 - > "${TAG}_bad.txt" <<'PY'
import glob, os
import pandas as pd
tag, lst = os.environ["TAG"], os.environ["LIST"]
bad = set()
for kind, pre in (("B", f"{tag}_ben"), ("M", f"{tag}_mal")):
    fs = [f for f in [pre + "_results.csv"] + sorted(glob.glob(pre + "_rerun*_results.csv")) if os.path.exists(f)]
    if not fs:
        continue
    d = pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates("Package_Name", keep="last")
    sel = (d.Probe_Died.astype(str) != "none") | (pd.to_numeric(d.Attach_Delay, errors="coerce") > 10)
    bad |= {(kind, p[:-7] if kind == "M" else p) for p in d.loc[sel, "Package_Name"]}
for l in open(lst):
    k, p = l.split()
    if (k, p) in bad:
        print(k, p)
PY
    [ -s "${TAG}_bad.txt" ] || break
    echo "=== rerun $i: $(wc -l < "${TAG}_bad.txt") packages ($(date '+%T'))"
    run_list "${TAG}_bad.txt" "_rerun$i"
done

echo "=================== BENIGN"
python3 src/variant/score_benign.py --features ${TAG}_ben_features.csv $(ls ${TAG}_ben_rerun*_features.csv 2>/dev/null) \
    --results ${TAG}_ben_results.csv $(ls ${TAG}_ben_rerun*_results.csv 2>/dev/null) --out ${TAG}_ben_scores.csv | tee ${TAG}_ben_summary.txt
echo "=================== MALICIOUS"
python3 src/variant/score_mal.py --features ${TAG}_mal_features.csv $(ls ${TAG}_mal_rerun*_features.csv 2>/dev/null) \
    --results ${TAG}_mal_results.csv $(ls ${TAG}_mal_rerun*_results.csv 2>/dev/null) --out ${TAG}_mal_scores.csv | tee ${TAG}_mal_summary.txt
tar -czf ${TAG}_out.tar.gz ${TAG}_*.csv ${TAG}_*.txt "$LIST" ${TAG}.log 2>/dev/null
chown "${SUDO_USER:-root}" ${TAG}_* 2>/dev/null
echo "=== ALL DONE $(date) | ${TAG}_out.tar.gz sha256 $(sha256sum ${TAG}_out.tar.gz | cut -d' ' -f1)"
