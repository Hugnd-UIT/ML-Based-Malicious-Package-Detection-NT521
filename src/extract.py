import argparse, collections, csv, glob, os, re, sys

FEATURES = [
    "Root_DIR_Installation",
    "Temporary_DIR_Installation",
    "Home_DIR_Installation",
    "User_Access",
    "Sys_Access",
    "Etc_DIR_Installation",
    "Other_DIR_Installation",

    "State_Transition",
    "Local_IP_Address_Access",
    "Remote_IP_Address_Access",
    "Local_Port_Access",
    "Remote_Port_Access",

    "Read_Processes",
    "Write_Processes",
    "Read_Data_Transfer_Processes",
    "Write_Data_Transfer_Processes",
    "File_Access_Processes",

    "Total_Dependencies",
    "Direct_Dependencies",
    "Indirect_Dependencies",

    "File_Operations",
    "Network_Operations",
    "Process_Management_Operations",
    "IO_Operations",
    "Time_Operations",
    "Security_Operations",

    *[f"Pattern_{i}" for i in range(1, 11)],
]

GROUPS = {
    "File_Operations": {
        "access", "chmod", "chown", "close", "dup2", "fstat", "fsync", "link",
        "lseek", "lstat", "mkdir", "newfstatat", "open", "openat", "read",
        "readlink", "rename", "rmdir", "stat", "symlink", "unlink", "write", "creat"
    },

    "Network_Operations": {
        "bind", "connect", "getpeername", "getsockname", "getsockopt", "recvfrom",
        "sendto", "setsockopt", "shutdown", "socket", "accept"
    },

    "Process_Management_Operations": {
        "clone", "execve", "getpgrp", "getpid", "kill", "setsid", "vfork",
        "wait4", "fork"
    },

    "IO_Operations": {
        "ioctl", "poll", "select", "writev", "readv"
    },

    "Time_Operations": {
        "clock_gettime", "time", "timer_delete"
    },

    "Security_Operations": {
        "capget", "faccessat", "fchmodat", "geteuid", "getgid", "getuid",
        "setuid", "setgid"
    },
}

RX_CALL = re.compile(r"^(?:\d+:\d+:\d+\s+)?([a-z_0-9]+)\(")
RX_ERR = re.compile(r"= -1 (E[A-Z]+)")
RX_FD = re.compile(r"fd=(\d+)")


def read(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def cast(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def opensnoop(path):
    order = [("Root_DIR_Installation", "/root"), ("Temporary_DIR_Installation", "/tmp"),
             ("Home_DIR_Installation", "/home"), ("User_Access", "/usr"),
             ("Sys_Access", "/sys"), ("Etc_DIR_Installation", "/etc")]
    counts = dict.fromkeys([k for k, _ in order] + ["Other_DIR_Installation"], 0)
    for line in read(path):
        parts = line.split()
        if len(parts) < 5 or not parts[0].isdigit():
            continue
        p = parts[4]
        for key, prefix in order:
            if p.startswith(prefix):
                counts[key] += 1
                break
        else:
            counts["Other_DIR_Installation"] += 1
    return counts


def tcp(path):
    rows = [p for p in (l.split() for l in read(path)) if p and p[0] != "SKADDR"]
    trans = collections.Counter(f"{r[7]} -> {r[8]}" for r in rows if len(r) > 8)
    uniq = lambda i: len({r[i] for r in rows if len(r) > i})
    return {
        "State_Transition": str(dict(trans.most_common())),
        "Local_IP_Address_Access": uniq(3),
        "Local_Port_Access": uniq(4),
        "Remote_IP_Address_Access": uniq(5),
        "Remote_Port_Access": uniq(6),
    }


def filetop(path):
    sums = {i: collections.Counter() for i in (2, 3, 4, 5)}
    occ = collections.Counter()
    for line in read(path):
        parts = line.split()
        if len(parts) < 7 or not parts[0].isdigit():
            continue
        comm = parts[1]
        occ[comm] += 1
        for i in sums:
            v = cast(parts[i])
            if v is not None:
                sums[i][comm] += v
    top5 = lambda c: ", ".join(k for k, _ in c.most_common(5))
    return {
        "Read_Processes": top5(sums[2]),
        "Write_Processes": top5(sums[3]),
        "Read_Data_Transfer_Processes": top5(sums[4]),
        "Write_Data_Transfer_Processes": top5(sums[5]),
        "File_Access_Processes": top5(occ),
    }


def clean(name):
    return name.lower().replace("_", "-")


def install(path, pkg):
    lines = read(path)
    wheel = {}
    for l in lines:
        m = re.search(r"Created wheel for (\S+): filename=([^\s]+?)-(\d[^-\s]*)-", l)
        if m:
            wheel[clean(m.group(1))] = m.group(3)

    total = []
    for l in lines:
        if l.startswith("Successfully installed "):
            for tok in l.split()[2:]:
                name, _, ver = tok.rpartition("-")
                if not (ver[:1].isdigit() and name):
                    name, ver = tok, wheel.get(clean(tok), "")
                if clean(name) == clean(pkg):
                    continue
                total.append(f"{name}-{ver}" if ver else name)

    direct, indirect = [], []
    for l in lines:
        m = re.match(r"\s*Collecting (\S+) \(from (.+)\)", l)
        if m:
            (indirect if "->" in m.group(2) else direct).append(m.group(1))

    join = lambda xs: "; ".join(xs) + ";" if xs else ""
    return {
        "Total_Dependencies": join(list(dict.fromkeys(total))),
        "Direct_Dependencies": join(sorted(set(direct))),
        "Indirect_Dependencies": join(sorted(set(indirect))),
    }


def target(path):
    if not path or not os.path.exists(path):
        return None
    files = glob.glob(os.path.join(path, "strace_output_*")) or glob.glob(os.path.join(path, "*"))
    files = [f for f in files if os.path.isfile(f)]
    roots = [f for f in files if re.search(r"(\d+)\.\1$", f)]
    cands = roots or files
    return max(cands, key=os.path.getsize) if cands else None


def calls(path):
    entries = []
    for line in read(target(path)):
        m = RX_CALL.match(line)
        if not m:
            continue
        e, fd = RX_ERR.search(line), RX_FD.search(line)
        entries.append((m.group(1),
                        f"error={e.group(1)}" if e else "no-error",
                        f"fd={fd.group(1)}" if fd else "no-fd"))
    return entries


def syscall(entries):
    counts = dict.fromkeys(GROUPS, 0)
    for name, _, _ in entries:
        for group, names in GROUPS.items():
            if name in names:
                counts[group] += 1
                break
    return counts


def pattern(entries):
    names = [e[0] for e in entries]
    tri = collections.Counter(tuple(names[i:i + 3]) for i in range(len(names) - 2))
    adv = collections.Counter(tuple(names[i:i + 3]) + entries[i + 1][1:] for i in range(len(names) - 2))
    top5 = lambda c: ([" -> ".join(t) for t, _ in c.most_common(5)] + [""] * 5)[:5]
    return {f"Pattern_{i}": v for i, v in enumerate(top5(tri) + top5(adv), 1)}


def files(root, pkg, layout):
    if layout == "qut":
        g = lambda sub, suffix: os.path.join(root, f"QUT-DV25_{sub}", f"{pkg}_{suffix}")
        return {"opensnoop": g("Opensnoop_Traces", "opensnoop_trace.txt"),
                "tcp": g("TCP_Traces", "tcptraces.txt"),
                "filetop": g("Filetop_Traces", "filetop_trace.txt"),
                "install": g("Installation_Traces", "install_log.txt"),
                "strace": os.path.join(root, "QUT-DV25_Pattern_Traces", pkg)}
    d = os.path.join(root, "traces", pkg)
    tcp_file = os.path.join(d, f"{pkg}_tcp_trace.txt")
    if not os.path.exists(tcp_file):
        tcp_file = os.path.join(d, f"{pkg}_tcptraces.txt")
    strace_dir = os.path.join(root, "outputs", pkg)
    if not os.path.exists(strace_dir):
        strace_dir = os.path.join(root, "Trace_Outputs", pkg)
    return {"opensnoop": os.path.join(d, f"{pkg}_opensnoop_trace.txt"),
            "tcp": tcp_file,
            "filetop": os.path.join(d, f"{pkg}_filetop_trace.txt"),
            "install": os.path.join(d, f"{pkg}_install_log.txt"),
            "strace": strace_dir}


def packages(root, layout):
    if layout == "qut":
        return sorted(os.listdir(os.path.join(root, "QUT-DV25_Pattern_Traces")))
    d = os.path.join(root, "traces")
    if not os.path.exists(d):
        return []
    return sorted(p for p in os.listdir(d) if os.path.isdir(os.path.join(d, p)))


def extract(root, pkg, layout="ours", level=None):
    f = files(root, pkg, layout)
    c = calls(f["strace"])
    row = {"Package_Name": pkg}
    row.update(opensnoop(f["opensnoop"]))
    row.update(tcp(f["tcp"]))
    row.update(filetop(f["filetop"]))
    row.update(install(f["install"], pkg))
    row.update(syscall(c))
    row.update(pattern(c))
    if level is not None:
        row["Level"] = level
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--layout", choices=["ours", "qut"], default="ours")
    ap.add_argument("--pkg", nargs="*")
    ap.add_argument("--level", type=int, choices=[0, 1])
    ap.add_argument("--out")
    args = ap.parse_args()

    pkgs = args.pkg or packages(args.root, args.layout)
    cols = ["Package_Name"] + FEATURES + (["Level"] if args.level is not None else [])
    out = open(args.out, "w", newline="", encoding="utf-8") if args.out else sys.stdout
    writer = csv.DictWriter(out, fieldnames=cols)
    writer.writeheader()
    for p in pkgs:
        writer.writerow(extract(args.root, p, args.layout, args.level))
    if args.out:
        out.close()


if __name__ == "__main__":
    main()
