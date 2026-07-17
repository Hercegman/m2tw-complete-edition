#!/usr/bin/env python3
"""Unit cards (recruitment pictures + info portraits) for the new factions.

The engine looks up ui/units/<faction>/#<dictionary>.tga (fallback
ui/units/mercs/) and ui/unit_info/<faction>/<dictionary>_info.tga (fallback
ui/unit_info/merc/); with no faction folder every card falls through to the
peasant default — exactly the reported symptom. Generals/captains use their
bodyguard unit's card, so this fixes those too.

Donor card folders are staged in research/base-extract/data_cards (from
data_3.pack) — whole-folder copies per faction, later donors filling gaps
without overwriting earlier ones.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
CARDS = os.path.join(ROOT, "research", "base-extract", "data_cards")
BI = os.path.join(ROOT, "research", "dlc-extract", "british_isles", "mods", "british_isles", "data")

# donors in priority order (first = primary; later only fill missing files)
TEU = os.path.join(ROOT, "research", "dlc-extract", "teutonic", "mods", "teutonic", "data")
CRU = os.path.join(ROOT, "research", "dlc-extract", "crusades", "mods", "crusades", "data")

DONORS = {
    "croatia": ["hungary", "russia"],
    "wallachia": ["hungary", "russia"],
    "serbia": ["byzantium", "hungary", "russia"],
    "bulgaria": ["byzantium", "hungary", "russia"],
    "ragusa": ["venice"],
    "wales": ["england"],
    "ireland": ["scotland"],
    "norway": ["denmark"],
    "jerusalem": ["france"],
    "teutonic_order": ["hre", "poland"],
    "lithuania": ["poland", "russia"],
    "novgorod": ["russia", "denmark"],
    "antioch": ["france", "england"],
    "sweden": ["denmark"],
    "bohemia": ["hre", "poland"],
    "aragon": ["spain", "portugal"],
    "genoa": ["milan", "venice"],
    "pisa": ["milan", "venice"],
    "georgia": ["byzantium", "russia"],
    "armenia": ["byzantium", "turks"],
    "kievan_rus": ["russia", "poland"],
}


def _dlc_pair(root, fac):
    return (os.path.join(root, "ui", "units", fac),
            os.path.join(root, "ui", "unit_info", fac))


# authentic DLC art layered on top (overwrites donor files of the same name)
DLC_OVERLAY = {
    "norway": _dlc_pair(BI, "norway"),
    "teutonic_order": _dlc_pair(TEU, "teutonic_order"),
    "lithuania": _dlc_pair(TEU, "lithuania"),
    "novgorod": _dlc_pair(TEU, "novgorod"),
    "antioch": _dlc_pair(CRU, "antioch"),
}
# single-file extras outside the donor folders
EXTRA_INFO = {f: [("poland", "ce_wagon_fort_info.tga")]
              for f in ("croatia", "wallachia", "serbia", "bulgaria",
                        "lithuania", "novgorod", "kievan_rus", "georgia")}


def copy_fill(src, dst, overwrite=False):
    """copy src dir contents into dst; skip existing unless overwrite."""
    if not os.path.isdir(src):
        return 0
    os.makedirs(dst, exist_ok=True)
    n = 0
    for fn in os.listdir(src):
        s = os.path.join(src, fn)
        d = os.path.join(dst, fn)
        if os.path.isfile(s) and (overwrite or not os.path.exists(d)):
            shutil.copyfile(s, d)
            n += 1
    return n


def main():
    counts = {}
    for fac, donors in DONORS.items():
        u_dst = os.path.join(DATA, "ui", "units", fac)
        i_dst = os.path.join(DATA, "ui", "unit_info", fac)
        total = 0
        for donor in donors:
            total += copy_fill(os.path.join(CARDS, "units", donor), u_dst)
            total += copy_fill(os.path.join(CARDS, "unit_info", donor), i_dst)
        if fac in DLC_OVERLAY:
            du, di = DLC_OVERLAY[fac]
            total += copy_fill(du, u_dst, overwrite=True)
            total += copy_fill(di, i_dst, overwrite=True)
        for donor, fn in EXTRA_INFO.get(fac, []):
            src = os.path.join(CARDS, "unit_info", donor, fn)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(i_dst, fn))
                total += 1
        counts[fac] = total
    print("unit cards copied:", counts)

    # coverage check against the EDU: every owned unit's card must resolve
    # in the faction folder or the mercs fallback
    edu = open(os.path.join(DATA, "export_descr_unit.txt"), encoding="latin-1").read()
    mercs = set(os.listdir(os.path.join(CARDS, "units", "mercs")))
    missing = []
    for block in re.split(r"^type\s+", edu, flags=re.M)[1:]:
        dict_m = re.search(r"^dictionary\s+(\S+)", block, re.M)
        own_m = re.search(r"^ownership\s+(.*)$", block, re.M)
        if not dict_m or not own_m:
            continue
        card = f"#{dict_m.group(1).lower()}.tga"
        owners = {o.strip() for o in own_m.group(1).split(",")}
        for fac in DONORS:
            if fac in owners:
                fdir = os.path.join(DATA, "ui", "units", fac)
                if not os.path.exists(os.path.join(fdir, card)) and card not in mercs:
                    missing.append((fac, card))
    if missing:
        print(f"  WARNING {len(missing)} cards unresolved: {missing[:10]}")
    else:
        print("  card coverage: 100% (faction folder or mercs fallback)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
