#!/usr/bin/env python3
"""Faction consistency validator for Complete Edition.

descr_sm_factions.txt is the single source of truth. Checks that every
faction-coupled file agrees with it:
  * descr_strat: all referenced factions are registered; playable/unlockable/
    nonplayable lists contain only registered factions; slave present.
  * export_descr_unit: every name in every `ownership` line is registered
    (or a culture keyword, which vanilla EDU also allows).
  * text/expanded.txt: name keys exist for every non-vanilla faction.
  * ui TGAs: symbol/rebel/loading-screen icons exist for every non-vanilla faction.

Exit code 0 = consistent, 1 = drift found.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
VANILLA_SMF = os.path.join(ROOT, "research", "vanilla-extract", "data", "descr_sm_factions.txt")

SMF = os.path.join(DATA, "descr_sm_factions.txt")
STRAT = os.path.join(DATA, "world", "maps", "campaign", "imperial_campaign", "descr_strat.txt")
EDU = os.path.join(DATA, "export_descr_unit.txt")
EXPANDED = os.path.join(DATA, "text", "expanded.txt")

# ownership lines may also name cultures
CULTURES = {
    "northern_european", "southern_european", "eastern_european",
    "middle_eastern", "greek", "mesoamerican",
}

errors = []


def err(msg):
    errors.append(msg)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def factions_of(smf_text):
    return [m.group(1) for m in re.finditer(r"^faction\s+(\w+)", smf_text, re.M)]


def main():
    smf_factions = factions_of(read(SMF))
    registered = set(smf_factions)

    if "slave" not in registered:
        err("descr_sm_factions: slave faction missing")
    elif smf_factions[-1] != "slave":
        err(f"descr_sm_factions: slave must be last (last is {smf_factions[-1]})")
    dupes = {f for f in smf_factions if smf_factions.count(f) > 1}
    if dupes:
        err(f"descr_sm_factions: duplicate factions {sorted(dupes)}")

    vanilla = set(factions_of(read(VANILLA_SMF)))
    new_factions = [f for f in smf_factions if f not in vanilla]

    # --- descr_strat ---
    strat = read(STRAT)
    strat_factions = re.findall(r"^faction\s+(\w+)", strat, re.M)
    for f in strat_factions:
        if f not in registered:
            err(f"descr_strat: faction block '{f}' not registered in descr_sm_factions")
    for section in ("playable", "unlockable", "nonplayable"):
        m = re.search(rf"^{section}\s*\n(.*?)^end", strat, re.M | re.S)
        if not m:
            err(f"descr_strat: missing {section} section")
            continue
        for f in re.findall(r"^\s*(\w+)\s*$", m.group(1), re.M):
            if f not in registered:
                err(f"descr_strat: {section} lists unregistered faction '{f}'")

    # --- EDU ownership ---
    for i, line in enumerate(read(EDU).split("\n"), 1):
        m = re.match(r"^ownership\s+(.*)$", line.strip())
        if not m:
            continue
        for name in re.split(r"[,\s]+", m.group(1).strip()):
            if name and name not in registered and name not in CULTURES:
                err(f"export_descr_unit:{i}: ownership names unknown faction '{name}'")

    # --- expanded.txt name keys for new factions ---
    if os.path.exists(EXPANDED):
        expanded = read(EXPANDED).lower()
        for f in new_factions:
            if f == "slave":
                continue
            if f not in expanded:
                err(f"text/expanded.txt: no name entry for new faction '{f}'")
    else:
        err("text/expanded.txt missing")

    # --- UI assets for new factions (vanilla ones live in packs) ---
    for f in new_factions:
        for rel in (
            f"ui/symbols/symbol_{f}.tga",
            f"ui/rebel_symbols/rebel_{f}.tga",
            f"ui/loading_screen/symbols/symbol128_{f}.tga",
        ):
            if not os.path.exists(os.path.join(DATA, rel)):
                err(f"missing UI asset for '{f}': data/{rel}")

    n_reg = len(smf_factions)
    n_campaign = len(strat_factions)
    if errors:
        print(f"FAIL — {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK — {n_reg} registered factions ({len(new_factions)} new), "
          f"{n_campaign} campaign faction blocks, all coupled files consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
