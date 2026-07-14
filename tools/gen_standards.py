#!/usr/bin/env python3
"""Unique strat-map standards (the flags above armies and settlements).

`standard_index` in descr_sm_factions indexes into 64x64 cells of the atlas
TGAs listed in descr_standards.txt's `factions` block (4 cells per 128x128
file: UL, UR, BL, BR — proven extensible by the British Isles DLC, which
appended banners/symbols9.tga and gave wales index 24).

We ship symbols9/10/11.tga with 9 crest cells (indices 24-32): the Kingdoms
four get their genuine DLC atlas cells copied over; the Balkan five get the
generated heraldry. descr_sm_factions gets a unique standard_index each.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tga
import gen_heraldry

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
VAN_STD = os.path.join(ROOT, "research", "vanilla-extract", "data", "descr_standards.txt")
DLC = {
    "british_isles": os.path.join(ROOT, "research", "dlc-extract", "british_isles", "mods", "british_isles", "data"),
    "crusades": os.path.join(ROOT, "research", "dlc-extract", "crusades", "mods", "crusades", "data"),
}

# fixed assignment, appended after vanilla's 0-23
ORDER = ["croatia", "ragusa", "serbia", "bulgaria", "wallachia",
         "wales", "ireland", "norway", "jerusalem"]
BASE_INDEX = 24
DLC_SOURCE = {"wales": "british_isles", "ireland": "british_isles",
              "norway": "british_isles", "jerusalem": "crusades"}

CELL = 64


def factions_atlas_files(dlc):
    """Ordered symbols files of the `factions` block (index // 4 keys into
    THIS list — symbols7/8 belong to rebels_factions and are not in it)."""
    std = open(os.path.join(DLC[dlc], "descr_standards.txt"), encoding="latin-1").read()
    block = re.search(r"^factions\s*\n(.*?)^rebels_factions", std, re.M | re.S).group(1)
    return re.findall(r"^symbols\s+(\S+)", block, re.M)


def dlc_cell(fac):
    """Copy the faction's genuine crest cell from its DLC atlas."""
    dlc = DLC_SOURCE[fac]
    smf = open(os.path.join(DLC[dlc], "descr_sm_factions.txt"), encoding="latin-1").read()
    m = re.search(rf"^faction\s+{fac}\b.*?^standard_index\s+(\d+)", smf, re.M | re.S)
    assert m, f"no standard_index for {fac} in {dlc}"
    idx = int(m.group(1))
    files = factions_atlas_files(dlc)
    rel = files[idx // 4]        # e.g. banners/symbols9.tga
    cell = idx % 4
    atlas = tga.read(os.path.join(DLC[dlc], rel.replace("banners/", "banners" + os.sep)))
    cy, cx = (cell // 2) * CELL, (cell % 2) * CELL
    return [row[cx:cx + CELL] for row in atlas[cy:cy + CELL]]


def heraldry_cell(fac):
    """64x64 crest cell from the generated heraldry, shield-masked with alpha."""
    design = gen_heraldry.draw_design(fac, CELL, CELL)
    alpha = gen_heraldry.shield_alpha(CELL, CELL)
    out = []
    for y in range(CELL):
        row = []
        for x in range(CELL):
            r, g, b = design[y][x]
            row.append((r, g, b, alpha[y][x]))
        out.append(row)
    return out


def main():
    cells = {}
    for fac in ORDER:
        cells[fac] = dlc_cell(fac) if fac in DLC_SOURCE else heraldry_cell(fac)

    out_dir = os.path.join(DATA, "banners")
    os.makedirs(out_dir, exist_ok=True)
    n_files = (len(ORDER) + 3) // 4
    for f in range(n_files):
        atlas = [[(0, 0, 0, 0)] * 128 for _ in range(128)]
        for c in range(4):
            i = f * 4 + c
            if i >= len(ORDER):
                break
            cell = cells[ORDER[i]]
            cy, cx = (c // 2) * CELL, (c % 2) * CELL
            for y in range(CELL):
                for x in range(CELL):
                    atlas[cy + y][cx + x] = cell[y][x]
        # match the BI DLC container: uncompressed 32-bit, bottom-left origin
        tga.write(os.path.join(out_dir, f"symbols{9 + f}.tga"), atlas,
                  origin_topdown=False)

    std = open(VAN_STD, encoding="latin-1").read()
    extra = "".join(f"symbols\t\t\t\tbanners/symbols{9 + f}.tga\n" for f in range(n_files))
    std, n = re.subn(r"(^symbols\s+banners/symbols6\.tga\s*\n)", r"\1" + extra,
                     std, count=1, flags=re.M)
    assert n == 1, "failed to extend the factions symbols block"
    with open(os.path.join(DATA, "descr_standards.txt"), "w",
              encoding="latin-1", newline="\n") as f:
        f.write(std)

    smf_path = os.path.join(DATA, "descr_sm_factions.txt")
    smf = open(smf_path, encoding="latin-1").read()
    for i, fac in enumerate(ORDER):
        smf = re.sub(rf"(^faction\s+{fac}\b.*?^standard_index\s+)\d+",
                     rf"\g<1>{BASE_INDEX + i}", smf, count=1, flags=re.M | re.S)
    with open(smf_path, "w", encoding="latin-1", newline="\n") as f:
        f.write(smf)

    assign = {fac: BASE_INDEX + i for i, fac in enumerate(ORDER)}
    print(f"standards: {n_files} atlas files, indices {assign}")


if __name__ == "__main__":
    main()
