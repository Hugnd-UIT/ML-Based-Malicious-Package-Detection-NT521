#!/bin/bash
# Usage: sudo [options] ./trace.sh <package|file.tar.gz|./local/dir> [seconds=120]
#
# Default = the authors' trace.sh (QUT-DV25): strace monitor + filetop, opensnoop, tcpstates for
# <seconds>, pip flags --break-system-packages --no-build-isolation --no-cache-dir with the authors'
# 3-attempt fallback, pip 24.3.1 / setuptools 75.3.0 pinned as in the QUT-DV25 raw traces.
#
# Options (environment variables):
#   PYTHON=python3       interpreter of the venv (QUT-DV25: python3.12 benign, python3.8 malicious)
#   NETMODE=real         real | off | fake | mirror | pypi
#                          off : iptables rejects all outbound traffic except loopback
#                          fake: off + fake C2 (127.0.0.1:9999) and fake HTTP (127.0.0.1:8000)
#                          mirror: fake + local package index on 127.0.0.1:8081 serving wheelhouse/<python>/,
#                                so pip downloads over (loopback) network while the network stays simulated
#                          pypi: fake + DNS and HTTPS to the real PyPI open (NOT disabled/simulated network)
#   OFFLINE=1            pip installs only from wheelhouse/<python>/ (required for off / fake)
#   DECOYS=1             create decoy ~/fake_secret.txt and FAKE_TOKEN (src/harness/setup_decoys.sh)
#   STRACE=poll          poll: monitor.sh attaches strace to python/pip every POLL s (authors)
#                        wrap: pip runs under strace from its first syscall (NT230 extension)
#   POLL=1               polling interval of monitor.sh (authors: 1 s)
#   PIPCACHE=0           1 = drop --no-cache-dir (cache sensitivity, NT230 extension)
#   PIPARGS=             extra pip options, e.g. --no-deps (dependency sensitivity, NT230 extension)
#
# Output: traces/<name>/ (eBPF logs, install log, attach_delay.txt, install_seconds.txt, meta.env),
#         outputs/<name>/ (strace), one line in traces/status.csv.
set -u

if [ -z "${1:-}" ]; then
    echo "Usage: sudo [PYTHON=..] [NETMODE=real|off|fake|pypi] [OFFLINE=1] [STRACE=poll|wrap] ./trace.sh <package|file.tar.gz|./dir> [seconds=120]"
    exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "Must run with sudo"
    exit 1
fi

# Stop leftovers of an earlier run (a stale monitor.sh would grab pip with its own strace
# and leave this run with an empty system call trace). [x] keeps pkill from matching itself.
cleanup_stale() {
    pkill -KILL -f '[s]rc/scripts/monitor.sh' 2>/dev/null
    pkill -KILL -f '[f]iletop-bpfcc|[o]pensnoop-bpfcc|[t]cpstates-bpfcc' 2>/dev/null
    pkill -KILL -x strace 2>/dev/null
    pkill -KILL -f '[e]nv/.*/bin/(pip|python)' 2>/dev/null   # orphan pip of an earlier killed run
    return 0
}
cleanup_stale

spec="$1"
duration="${2:-120}"
py="${PYTHON:-python3}"
netmode="${NETMODE:-real}"
mode="${STRACE:-poll}"
pipcache="${PIPCACHE:-0}"
base="$(cd "$(dirname "$0")/../.." && pwd)"
# A local folder or archive is installed from its path but stored under its base name
if [ -f "$spec" ] || { [[ "$spec" == */* ]] && [ -e "$spec" ]; }; then
    spec="$(cd "$(dirname "$spec")" && pwd)/$(basename "$spec")"
fi
pkg="$(basename "${spec%/}")"
cd "$base"
harness="$base/src/harness"

out="traces/${pkg}"
venv="env/${pkg}"
rm -rf "$out"
mkdir -p "$out/errors" env

opts=""
if [ "${OFFLINE:-0}" = 1 ]; then
    opts="--no-index --find-links $(pwd)/wheelhouse/${py}"
    [ -d "wheelhouse/${py}" ] || { echo "Missing wheelhouse/${py} - run prepare_wheelhouse.sh first"; exit 1; }
fi
case "$netmode" in
    real|pypi) ;;
    off|fake) [ "${OFFLINE:-0}" = 1 ] || { echo "NETMODE=$netmode blocks PyPI: also set OFFLINE=1"; exit 1; } ;;
    mirror)
        [ -d "wheelhouse/${py}" ] || { echo "Missing wheelhouse/${py} - run prepare_wheelhouse.sh first"; exit 1; }
        opts="--no-index --find-links http://127.0.0.1:8081/" ;;
    *) echo "Unknown NETMODE=$netmode"; exit 1 ;;
esac

# the mirror is not up yet while the venv is prepared: read the same wheelhouse from disk
prep_opts="$opts"
[ "$netmode" = mirror ] && prep_opts="--no-index --find-links $(pwd)/wheelhouse/${py}"
rm -rf "$venv"
$py -m venv "$venv" || { echo "Failed to create venv with $py"; exit 1; }
# Versions seen in QUT-DV25 raw traces: pip 24.3.1, setuptools 75.3.0, wheel 0.43.0 (benign, py3.12) / 0.45.1 (malicious, py3.8)
[ "$py" = python3.8 ] && wheel_ver=0.45.1 || wheel_ver=0.43.0
"$venv/bin/pip" install $prep_opts --upgrade "pip==24.3.1" "setuptools==75.3.0" "wheel==${WHEEL:-$wheel_ver}" >/dev/null 2>&1 \
    || { echo "Failed to prepare venv (pip/setuptools/wheel)"; exit 1; }

# ---- network sandbox (NT230) ----
fakes=""
net_on() {
    [ "$netmode" = real ] && return
    for t in iptables ip6tables; do
        $t -N DYSEC_NET 2>/dev/null || $t -F DYSEC_NET
        $t -A DYSEC_NET -o lo -j ACCEPT
        if [ "$netmode" = pypi ]; then
            $t -A DYSEC_NET -p udp --dport 53 -j ACCEPT
            $t -A DYSEC_NET -p tcp --dport 53 -j ACCEPT
            fam=ahostsv4; [ "$t" = ip6tables ] && fam=ahostsv6
            for ip in $(getent $fam pypi.org files.pythonhosted.org | awk '{print $1}' | sort -u); do
                $t -A DYSEC_NET -p tcp -d "$ip" --dport 443 -j ACCEPT
            done
        fi
        $t -A DYSEC_NET -j REJECT
        $t -I OUTPUT 1 -j DYSEC_NET
    done
    if [ "$netmode" = mirror ]; then
        $py -m http.server 8081 --bind 127.0.0.1 --directory "$base/wheelhouse/${py}" > "$out/mirror.log" 2>&1 & fakes="$fakes $!"
    fi
    if [ "$netmode" != off ]; then
        $py "$harness/fake_c2.py" > "$out/fake_c2.log" 2>&1 & fakes="$fakes $!"
        $py "$harness/fake_http.py" > "$out/fake_http.log" 2>&1 & fakes="$fakes $!"
        sleep 1
    fi
}
net_off() {
    [ -n "$fakes" ] && kill $fakes 2>/dev/null
    fakes=""
    [ "$netmode" = real ] && return
    for t in iptables ip6tables; do
        $t -D OUTPUT -j DYSEC_NET 2>/dev/null
        $t -F DYSEC_NET 2>/dev/null
        $t -X DYSEC_NET 2>/dev/null
    done
}
trap net_off EXIT
[ "${DECOYS:-0}" = 1 ] && source "$harness/setup_decoys.sh" > "$out/decoys.log" 2>&1
net_on

export PYTHONUNBUFFERED=1
# Same order as the authors' trace.sh: strace monitor first, then the 3 eBPF tools, wait 5 s
mpid=""
if [ "$mode" = wrap ]; then
    rm -rf "outputs/$pkg"; mkdir -p "outputs/$pkg"
else
    IGNORE_PIDS="$fakes" bash "$base/src/scripts/monitor.sh" "$pkg" > "$out/monitor.log" 2>&1 & mpid=$!
fi
filetop-bpfcc 5 > "$out/${pkg}_filetop_trace.txt" 2>"$out/errors/filetop_trace.err" & fpid=$!
opensnoop-bpfcc -d 10 > "$out/${pkg}_opensnoop_trace.txt" 2>"$out/errors/opensnoop_trace.err" & opid=$!
tcpstates-bpfcc > "$out/${pkg}_tcp_trace.txt" 2>"$out/errors/tcp_trace.err" & tpid=$!
sleep 5

rm -rf /tmp/dysec_sim_markers
start=$(date +%s)
echo "Installing $spec ..."
log="$out/${pkg}_install_log.txt"
run() {
    if [ "$mode" = wrap ]; then
        strace -f -ff -o "outputs/$pkg/strace_output_pip" -s 4096 -t -v "$@"
    else
        "$@"
    fi
}
cache_opt="--no-cache-dir"
[ "$pipcache" = 1 ] && cache_opt=""
t0=$(date +%s.%N)
# pip flags and the 3-attempt fallback are copied from the authors' trace.sh
run "$venv/bin/pip" install $opts "$spec" --break-system-packages --no-build-isolation $cache_opt ${PIPARGS:-} 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then
    echo "First attempt failed, retrying with pip3 ..."
    run "$venv/bin/pip3" install $opts "$spec" ${PIPARGS:-} 2>&1 | tee "$log"
    status=${PIPESTATUS[0]}
fi
if [ "$status" -ne 0 ]; then
    echo "Second attempt failed, retrying with --break-system-packages ..."
    run "$venv/bin/pip" install $opts "$spec" --break-system-packages ${PIPARGS:-} 2>&1 | tee "$log"
    status=${PIPESTATUS[0]}
fi
# Logging only: wall-clock seconds pip took (all attempts)
install_s=$(awk -v a="$t0" -v b="$(date +%s.%N)" 'BEGIN { printf "%.2f", b - a }')
echo "$install_s" > "$out/install_seconds.txt"

remain=$(( duration - ($(date +%s) - start) ))
[ "$remain" -gt 0 ] && sleep "$remain"

warn=""
for pair in "filetop:$fpid" "tcpstates:$tpid"; do
    kill -0 "${pair#*:}" 2>/dev/null || warn="$warn ${pair%%:*}"
done
kill $fpid $opid $tpid $mpid 2>/dev/null
pkill -x strace 2>/dev/null
sleep 2
# Anything that ignored SIGTERM is killed for sure
kill -KILL $fpid $opid $tpid $mpid 2>/dev/null
cleanup_stale
net_off
trace_s=$(( $(date +%s) - start ))

# An empty strace directory means no system call was recorded: the run is not valid
if [ -z "$(find "outputs/$pkg" -type f -size +0 2>/dev/null | head -1)" ]; then
    warn="$warn strace"
fi
# Markers written by the simulated packages show what each one actually did
[ -d /tmp/dysec_sim_markers ] && cp -r /tmp/dysec_sim_markers "$out/markers"

[ "$status" -eq 0 ] && result=Success || result=Failed
cat > "$out/meta.env" <<EOF
pkg=$pkg
spec=$spec
result=$result
duration=$duration
netmode=$netmode
offline=${OFFLINE:-0}
strace=$mode
poll=${POLL:-1}
pipcache=$pipcache
pipargs=${PIPARGS:-}
python=$($py --version 2>&1 | cut -d' ' -f2)
pip=$("$venv/bin/pip" --version | cut -d' ' -f2)
kernel=$(uname -r)
os=$(. /etc/os-release && echo "$PRETTY_NAME")
bcc=$(dpkg-query -W -f='${Version}' bpfcc-tools 2>/dev/null)
strace_version=$(strace -V | head -1 | awk '{print $NF}')
install_seconds=$install_s
trace_seconds=$trace_s
ebpf_bytes=$(du -sb "$out" | cut -f1)
strace_bytes=$(du -sb "outputs/${pkg}" 2>/dev/null | cut -f1)
probe_died=$(echo ${warn:-none})
finished=$(date '+%F %T')
EOF

echo "$pkg,$result,$(date '+%F %T'),probe_died:${warn:- none}" >> traces/status.csv
echo "[+] Done - $result. eBPF trace: $out | system call trace: outputs/$pkg"
if [ -n "$warn" ]; then
    echo "[!] Probes died early:$warn -> check $out/errors/*.err and re-run"
fi
