"""Checksums and environment summary of one trace run, for the data card.

    python src/manifest.py runs/<tag>

Writes runs/<tag>/manifest.csv (path, bytes, sha256 of every file) and prints the
environment recorded by trace.sh (OS, kernel, Python, pip, bcc, strace, settings).
"""
import argparse, csv, hashlib, os
from collections import defaultdict


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    args = ap.parse_args()
    run = args.run.rstrip("/\\")

    rows, env = [], defaultdict(set)
    for root, _, files in os.walk(run):
        for name in sorted(files):
            path = os.path.join(root, name)
            rel = os.path.relpath(path, run).replace(os.sep, "/")
            if rel == "manifest.csv":
                continue
            rows.append({"path": rel, "bytes": os.path.getsize(path), "sha256": sha256(path)})
            if name == "meta.env":
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        k, _, v = line.rstrip("\n").partition("=")
                        if k in ("os", "kernel", "python", "pip", "bcc", "strace_version", "netmode",
                                 "offline", "strace", "poll", "pipcache", "duration"):
                            env[k].add(v)

    with open(os.path.join(run, "manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256"])
        w.writeheader()
        w.writerows(rows)

    print(f"[+] {len(rows)} files, {sum(r['bytes'] for r in rows) / 2**20:.1f} MB -> {run}/manifest.csv")
    for k, v in env.items():
        print(f"  {k:15s} {', '.join(sorted(v))}")


if __name__ == "__main__":
    main()
