"""Split the F1-F6 package lists into three folders, one per person, written before any F run.

Sources: data/mix-lapE.txt (F1, 270 packages) and data/mix-sens.txt (F2-F6, 100 packages).
Rule, no randomness:
  1. Walk data/mix-lapE.txt in its order. Count benign (B) and malicious (M) lines separately; the k-th line
     of a class (k from 0) goes to person k % 3. Each person keeps the lap E order and gets almost the same B:M ratio.
  2. data/mix-sens.txt is a subset of data/mix-lapE.txt. Each of its lines goes to the person who got that line in step 1,
     so one package is traced by one person in F1 and in F2-F6. Paired comparisons F1 vs Fk then differ in the factor only,
     not in the machine.
Order of people: Hoang, Dang, Hung.
  python3 src/data/split-mix-3.py  -> data/split/<Name>/mix-lapE.txt and data/split/<Name>/mix-sens.txt
"""
import hashlib, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "data")
PEOPLE = ["Hoang", "Dang", "Hung"]


def read(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def main():
    lap_e, sens = read("mix-lapE.txt"), read("mix-sens.txt")
    assert len(set(lap_e)) == len(lap_e), "duplicate lines in mix-lapE.txt"
    assert set(sens) <= set(lap_e), "mix-sens.txt must be a subset of mix-lapE.txt"

    owner, seen = {}, {"B": 0, "M": 0}
    for line in lap_e:
        kind = line[0]
        owner[line] = PEOPLE[seen[kind] % len(PEOPLE)]
        seen[kind] += 1

    for name in PEOPLE:
        out = os.path.join(D, "split", name)
        os.makedirs(out, exist_ok=True)
        for fname, lines in (("mix-lapE.txt", lap_e), ("mix-sens.txt", sens)):
            mine = [l for l in lines if owner[l] == name]
            with open(os.path.join(out, fname), "w", newline="\n", encoding="utf-8") as f:
                f.writelines(l + "\n" for l in mine)

    print(f"{'person':6s} | lapE  B    M  total | sens  B    M  total | sha256 (mix-lapE, mix-sens)")
    total = {"lapE": 0, "sens": 0}
    for name in PEOPLE:
        row = []
        for fname in ("mix-lapE.txt", "mix-sens.txt"):
            path = os.path.join(D, "split", name, fname)
            lines = read(os.path.join("split", name, fname))
            b = sum(l.startswith("B ") for l in lines)
            row.append((b, len(lines) - b, len(lines), hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]))
        total["lapE"] += row[0][2]
        total["sens"] += row[1][2]
        print(f"{name:6s} | {row[0][0]:9d} {row[0][1]:4d} {row[0][2]:5d} | {row[1][0]:9d} {row[1][1]:4d} {row[1][2]:5d} | {row[0][3]} {row[1][3]}")
    assert total == {"lapE": len(lap_e), "sens": len(sens)}, "split lost or duplicated lines"
    print(f"total: mix-lapE {total['lapE']} / {len(lap_e)}, mix-sens {total['sens']} / {len(sens)}")


if __name__ == "__main__":
    main()
