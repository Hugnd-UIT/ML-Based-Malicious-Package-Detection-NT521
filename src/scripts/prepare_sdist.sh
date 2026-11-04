#!/bin/bash
# Usage: ./prepare_sdist.sh <list.csv> [python=python3]
#
# DySec paper, Algorithm 1 (line 8): only .tar.gz / .zip archives are installed, so every
# package goes through a source build (setup.py / pyproject). pip on its own prefers wheels for
# PyPI packages, which skips the build and makes benign traces look unlike QUT-DV25.
# This script turns every row of <list.csv> into a .tar.gz in sdist/ and writes
# <list>_sdist.csv (same name,label,group; spec points to the archive).
# Run ONCE while the VM still has internet, after prepare_wheelhouse.sh (runtime dependencies and
# build backends of the archives go to wheelhouse/ and are installed offline from there).
set -u

if [ -z "${1:-}" ]; then
    echo "Usage: ./prepare_sdist.sh <list.csv> [python=python3]"
    exit 1
fi

list="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
py="${2:-python3}"
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"
dst="sdist"
mkdir -p "$dst"
out="${list%.csv}_sdist.csv"

tmp="$(mktemp -d)"
$py -m venv "$tmp/venv"
pip="$tmp/venv/bin/pip"
$pip install -q --upgrade pip setuptools wheel build

echo "name,spec,label,group" > "$out"
tail -n +2 "$list" | while IFS=, read -r name spec label group; do
    case "$name" in ""|\#*) continue ;; esac
    before="$(ls "$dst")"
    case "$spec" in
        *.tar.gz|*.zip) cp "$spec" "$dst/" ;;
        */*) "$tmp/venv/bin/python" -m build --sdist --outdir "$dst" "$spec" >/dev/null ;;
        *)   $pip download -q --no-binary :all: --no-deps -d "$dst" "$spec" ;;
    esac
    file="$(comm -13 <(echo "$before") <(ls "$dst") | head -1)"
    if [ -z "$file" ]; then
        echo "[!] No archive for $name - skipped"
        continue
    fi
    # Building an archive offline needs its build backend (flit_core, hatchling, ...) in the
    # wheelhouse, so read [build-system] requires from the archive and download them.
    reqs="$("$tmp/venv/bin/python" - "$dst/$file" <<'EOF'
import sys, tarfile, zipfile, tomllib
p = sys.argv[1]
def read(names, get):
    cands = [n for n in names if n.count("/") == 1 and n.endswith("/pyproject.toml")]
    return tomllib.loads(get(cands[0]).decode()) if cands else {}
if p.endswith(".zip"):
    z = zipfile.ZipFile(p); d = read(z.namelist(), z.read)
else:
    t = tarfile.open(p); d = read(t.getnames(), lambda n: t.extractfile(n).read())
print("\n".join(d.get("build-system", {}).get("requires", ["setuptools", "wheel"])))
EOF
)"
    if [ -n "$reqs" ]; then
        echo "$reqs" > "$tmp/req.txt"
        $pip download -q -d "wheelhouse/${py}" -r "$tmp/req.txt" || echo "[!] build deps of $name incomplete"
    fi
    echo "$name,$dst/$file,$label,$group" >> "$out"
    echo "[+] $name -> $dst/$file"
done
rm -rf "$tmp"
echo "[+] List written to $out"
