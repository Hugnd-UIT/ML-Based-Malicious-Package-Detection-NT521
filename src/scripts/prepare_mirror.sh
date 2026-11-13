#!/bin/bash
# Usage: bash src/scripts/prepare_mirror.sh [list=data/mix-lapE.txt]
#
# Run ONCE in the VM while it still has internet (not as root is fine). Fills the local package
# index that trace.sh serves on 127.0.0.1:8081 with NETMODE=mirror (and reads from disk with OFFLINE=1):
#   wheelhouse/python3/    pinned pip/setuptools/wheel + every benign package of the list ("B name") and its dependencies
#   wheelhouse/python3.8/  pinned pip/setuptools/wheel + the dependencies of every malicious archive ("M name-version")
#   <name-version>.tar.gz  malicious archives in the repo root (as src/variant/verify*.sh expect), from pypi_malregistry
# Dependencies of a malicious archive are read STATICALLY from its PKG-INFO / *.egg-info/requires.txt /
# pyproject.toml: nothing inside the archive is executed. Writes wheelhouse/missing.txt for what could not be fetched.
set -u
list="${1:-data/mix-lapE.txt}"
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"
[ -f "$list" ] || { echo "Missing $list"; exit 1; }
command -v python3.8 >/dev/null || { echo "python3.8 is required (malicious packages are installed with it, as QUT-DV25)"; exit 1; }
mkdir -p wheelhouse/python3 wheelhouse/python3.8
: > wheelhouse/missing.txt

tmp="$(mktemp -d)"
python3 -m venv "$tmp/v3"; python3.8 -m venv "$tmp/v38"
p3="$tmp/v3/bin/pip"; p38="$tmp/v38/bin/pip"
# versions pinned by trace.sh (as in the QUT-DV25 raw traces)
$p3 download -q -d wheelhouse/python3 "pip==24.3.1" "setuptools==75.3.0" "wheel==0.43.0"
$p38 download -q -d wheelhouse/python3.8 "pip==24.3.1" "setuptools==75.3.0" "wheel==0.45.1"

# Static reader: prints one requirement per line (runtime + build-system), never imports the package
cat > "$tmp/reqs.py" <<'PY'
import sys, tarfile, zipfile, re
try:
    import tomllib
except ImportError:
    tomllib = None
p = sys.argv[1]
try:
    if p.endswith(".zip"):
        z = zipfile.ZipFile(p); names = z.namelist(); get = lambda n: z.read(n).decode("utf-8", "replace")
    else:
        t = tarfile.open(p); names = t.getnames(); get = lambda n: t.extractfile(n).read().decode("utf-8", "replace")
except Exception:
    sys.exit(0)
out = []
for n in names:
    b = n.rsplit("/", 1)[-1]
    if b == "PKG-INFO" and n.count("/") == 1:
        for line in get(n).splitlines():
            if line.startswith("Requires-Dist:"):
                out.append(line.split(":", 1)[1].strip())
    elif n.endswith(".egg-info/requires.txt"):
        for line in get(n).splitlines():
            line = line.strip()
            if line.startswith("["):
                break                      # extras sections are not installed by default
            if line and not line.startswith("#"):
                out.append(line)
    elif b == "pyproject.toml" and n.count("/") == 1 and tomllib:
        try:
            d = tomllib.loads(get(n))
        except Exception:
            continue
        out += d.get("build-system", {}).get("requires", [])
        out += d.get("project", {}).get("dependencies", [])
for r in dict.fromkeys(out):
    r = r.split(";")[0].strip()            # drop environment markers
    if re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*", r):
        print(r)
PY

nb=0; nm=0
while read -r kind name; do
    name=${name%%[[:space:]]}
    [ -z "$name" ] && continue
    if [ "$kind" = B ]; then
        nb=$((nb + 1))
        $p3 download -q -d wheelhouse/python3 "$name" >/dev/null 2>&1 || echo "B $name" >> wheelhouse/missing.txt
    else
        nm=$((nm + 1))
        f="$name.tar.gz"
        [ -s "$f" ] || wget -q "https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/${name%-*}/${name##*-}/$f" \
            || { echo "M $name (archive)" >> wheelhouse/missing.txt; continue; }
        python3 "$tmp/reqs.py" "$f" > "$tmp/r.txt"
        while read -r r; do
            $p38 download -q -d wheelhouse/python3.8 "$r" >/dev/null 2>&1 || echo "M $name needs $r" >> wheelhouse/missing.txt
        done < "$tmp/r.txt"
    fi
    printf "\r[%s] benign %d, malicious %d" "$(date +%T)" "$nb" "$nm"
done < "$list"
rm -rf "$tmp"
echo
echo "[+] wheelhouse/python3: $(ls wheelhouse/python3 | wc -l) files, wheelhouse/python3.8: $(ls wheelhouse/python3.8 | wc -l) files"
echo "[+] could not fetch: $(wc -l < wheelhouse/missing.txt) (see wheelhouse/missing.txt)"
