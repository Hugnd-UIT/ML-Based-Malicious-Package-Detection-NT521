#!/bin/bash
# Usage: sudo [options] ./trace.sh <package|file.tar.gz|./local/dir> [seconds=120]
#
# Options (environment variables):
#   OFFLINE=1          pip uses only wheelhouse/<python>/ (no index). Required for NETMODE=off|fake.
#   PYTHON=python3.8   interpreter used for the venv.
#   NETMODE=real       real | off | fake
#                        off : iptables rejects all outbound traffic except loopback
#                        fake: like off, plus fake C2 (127.0.0.1:9999) and fake HTTP (127.0.0.1:8000)
#                        pypi: like fake, but DNS and HTTPS to PyPI stay open so pip downloads
#                              dependencies online as in the DySec paper (no OFFLINE needed)
#   SIM_DIR=sim_packages  folder of the simulated packages; its _harness/ provides decoys and fake servers.
#   DECOYS=1           create ~/fake_secret.txt and FAKE_TOKEN (for root, since pip runs as root).
#   STRACE=poll        poll: monitor.sh attaches to python/pip PIDs every POLL seconds (as QUT-DV25)
#                      wrap: pip runs under strace from the first syscall (nothing is missed)
#   POLL=1             polling interval of monitor.sh in seconds.
#   PIPCACHE=0         0: --no-cache-dir (as QUT-DV25) | 1: use pip cache.
#   PIPARGS=           extra pip install options, e.g. --no-deps (dependency sensitivity).
#
# Output: traces/<name>/ (eBPF logs, install log, meta.env) and outputs/<name>/ (strace).
set -u

if [ -z "${1:-}" ]; then
    echo "Usage: sudo [OFFLINE=1] [NETMODE=real|off|fake|pypi] [STRACE=poll|wrap] ./trace.sh <package|file.tar.gz|./dir> [seconds=120]"
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Must run with sudo"
    exit 1
fi

spec="$1"
duration="${2:-120}"
py="${PYTHON:-python3}"
netmode="${NETMODE:-real}"
strace_mode="${STRACE:-poll}"
pipcache="${PIPCACHE:-0}"
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"
sim_dir="${SIM_DIR:-$base/sim_packages}"

# A local folder or archive is installed from its path but stored under its base name.
pkg="$(basename "${spec%/}")"
case "$spec" in
    */*) [ -e "$spec" ] && spec="$(cd "$(dirname "$spec")" && pwd)/$(basename "$spec")" ;;
esac

out="traces/${pkg}"
venv="env/${pkg}"
rm -rf "$out"
mkdir -p "$out" env

opts=""
if [ "${OFFLINE:-0}" = 1 ]; then
    opts="--no-index --find-links $(pwd)/wheelhouse/${py}"
    [ -d "wheelhouse/${py}" ] || { echo "Missing wheelhouse/${py} - run prepare_wheelhouse.sh before offline run"; exit 1; }
fi
if [ "$netmode" != real ] && [ "$netmode" != pypi ] && [ "${OFFLINE:-0}" != 1 ]; then
    echo "NETMODE=$netmode blocks PyPI: also set OFFLINE=1"
    exit 1
fi
cache_opt="--no-cache-dir"
[ "$pipcache" = 1 ] && cache_opt=""
cache_opt="$cache_opt ${PIPARGS:-}"

rm -rf "$venv"
$py -m venv "$venv" || { echo "Failed to create venv with $py"; exit 1; }
"$venv/bin/pip" install $opts --upgrade pip setuptools wheel >/dev/null 2>&1

export PYTHONUNBUFFERED=1
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
    if [ "$netmode" = fake ] || [ "$netmode" = pypi ]; then
        $py "$sim_dir/_harness/fake_c2.py" > "$out/fake_c2.log" 2>&1 & fakes="$fakes $!"
        $py "$sim_dir/_harness/fake_http.py" > "$out/fake_http.log" 2>&1 & fakes="$fakes $!"
        sleep 1
    fi
}
net_off() {
    [ -n "$fakes" ] && kill $fakes 2>/dev/null
    [ "$netmode" = real ] && return
    for t in iptables ip6tables; do
        $t -D OUTPUT -j DYSEC_NET 2>/dev/null
        $t -F DYSEC_NET 2>/dev/null
        $t -X DYSEC_NET 2>/dev/null
    done
}
trap net_off EXIT

if [ "${DECOYS:-0}" = 1 ]; then
    source "$sim_dir/_harness/setup_decoys.sh" > "$out/decoys.log" 2>&1
fi

net_on

mkdir -p "$out/errors"
filetop-bpfcc 5 > "$out/${pkg}_filetop_trace.txt" 2>"$out/errors/filetop_trace.err" & fpid=$!
opensnoop-bpfcc -d 10 > "$out/${pkg}_opensnoop_trace.txt" 2>"$out/errors/opensnoop_trace.err" & opid=$!
tcpstates-bpfcc > "$out/${pkg}_tcp_trace.txt" 2>"$out/errors/tcp_trace.err" & tpid=$!
mpid=""
if [ "$strace_mode" = poll ]; then
    IGNORE_PIDS="$fakes" POLL="${POLL:-1}" bash "$base/src/scripts/monitor.sh" "$pkg" > "$out/monitor.log" 2>&1 & mpid=$!
else
    rm -rf "outputs/${pkg}"
    mkdir -p "outputs/${pkg}"
fi
sleep 5

rm -rf /tmp/dysec_sim_markers
start=$(date +%s.%N)
echo "Installing $spec ..."
if [ "$strace_mode" = poll ]; then
    "$venv/bin/pip" install $opts "$spec" $cache_opt 2>&1 | tee "$out/${pkg}_install_log.txt"
else
    strace -f -ff -o "outputs/${pkg}/strace_output" -s 4096 -t -v \
        "$venv/bin/pip" install $opts "$spec" $cache_opt 2>&1 | tee "$out/${pkg}_install_log.txt"
fi
status=${PIPESTATUS[0]}
installed=$(date +%s.%N)

remain=$(( duration - ($(date +%s) - ${start%.*}) ))
if [ "$remain" -gt 0 ]; then
    sleep "$remain"
fi

warn=""
for pair in "filetop:$fpid" "tcpstates:$tpid"; do
    kill -0 "${pair#*:}" 2>/dev/null || warn="$warn ${pair%%:*}"
done
kill $fpid $opid $tpid $mpid 2>/dev/null
pkill -x strace 2>/dev/null
sleep 1
end=$(date +%s.%N)
net_off
fakes=""

# Markers written by the simulated packages show what each one actually did.
if [ -d /tmp/dysec_sim_markers ]; then
    cp -r /tmp/dysec_sim_markers "$out/markers"
fi

[ "$status" -eq 0 ] && result=Success || result=Failed
cat > "$out/meta.env" <<EOF
pkg=$pkg
spec=$spec
result=$result
duration=$duration
netmode=$netmode
offline=${OFFLINE:-0}
strace=$strace_mode
poll=${POLL:-1}
pipcache=$pipcache
pipargs=${PIPARGS:-}
python=$($py --version 2>&1 | cut -d' ' -f2)
pip=$("$venv/bin/pip" --version | cut -d' ' -f2)
kernel=$(uname -r)
os=$(. /etc/os-release && echo "$PRETTY_NAME")
bcc=$(dpkg-query -W -f='${Version}' bpfcc-tools 2>/dev/null)
strace_version=$(strace -V | head -1 | awk '{print $NF}')
install_seconds=$(awk "BEGIN{printf \"%.2f\", $installed - $start}")
trace_seconds=$(awk "BEGIN{printf \"%.2f\", $end - $start}")
ebpf_bytes=$(du -sb "$out" | cut -f1)
strace_bytes=$(du -sb "outputs/${pkg}" 2>/dev/null | cut -f1)
probe_died=${warn:-none}
finished=$(date '+%F %T')
EOF

echo "$pkg,$result,$(date '+%F %T'),probe_died:${warn:- none}" >> traces/status.csv
echo "[+] Done - $result. eBPF trace: $out | system call trace: outputs/$pkg"
if [ -n "$warn" ]; then
    echo "[!] Probes died early:$warn -> check $out/errors/*.err and re-run"
fi
