#!/bin/bash
# Usage: ./prepare_wheelhouse.sh <list.csv> [python=python3]
#
# Run ONCE while the VM still has internet. Downloads into wheelhouse/<python>/ everything
# pip needs to install the packages of <list.csv> offline (OFFLINE=1, NETMODE=off|fake):
# pip/setuptools/wheel for the venv and build isolation, plus every PyPI package and its
# dependencies. Local folders (simulated packages) need nothing beyond setuptools/wheel.
set -u

if [ -z "${1:-}" ]; then
    echo "Usage: ./prepare_wheelhouse.sh <list.csv> [python=python3]"
    exit 1
fi

list="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
py="${2:-python3}"
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"
dst="wheelhouse/${py}"
mkdir -p "$dst"

tmp="$(mktemp -d)"
$py -m venv "$tmp/venv"
pip="$tmp/venv/bin/pip"
$pip download -d "$dst" pip setuptools wheel

tail -n +2 "$list" | while IFS=, read -r name spec label group; do
    case "$name" in ""|\#*) continue ;; esac
    case "$spec" in
        */*|*.tar.gz) continue ;;
    esac
    $pip download -d "$dst" "$spec"
done
rm -rf "$tmp"
echo "[+] $(ls "$dst" | wc -l) files in $dst"
