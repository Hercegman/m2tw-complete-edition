"""Remove dropped factions (normans, saxons) from export_descr_unit ownership
lines, so the file is consistent with a sm_factions that omits them.
Reads research/vanilla-extract/data/export_descr_unit.txt, writes
research/export_descr_unit_edited.txt.
"""
import re, os

DROP = {"normans", "saxons"}
src = os.path.join("research", "vanilla-extract", "data", "export_descr_unit.txt")
text = open(src, "rb").read().decode("latin1")

out = []
fixed = 0
emptied = 0
for line in text.split("\n"):
    m = re.match(r"^(ownership\s+)(.*?)(\r?)$", line)
    if m:
        head, rest, cr = m.groups()
        toks = [t.strip() for t in rest.split(",")]
        kept = [t for t in toks if t.lower() not in DROP]
        if len(kept) != len(toks):
            fixed += 1
            if not kept:
                kept = ["slave"]   # avoid empty ownership
                emptied += 1
            line = head + ", ".join(kept) + cr
    out.append(line)

res = "\n".join(out).encode("latin1")
open(os.path.join("research", "export_descr_unit_edited.txt"), "wb").write(res)
print(f"ownership lines fixed: {fixed} (emptied->slave: {emptied})")
print(f"size {len(text.encode('latin1'))} -> {len(res)}")
print("normans remaining:", res.count(b'normans'), " saxons remaining:", res.count(b'saxons'))
