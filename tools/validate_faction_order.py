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
sys.path.insert(0, HERE)
import strings_bin

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
VANILLA_SMF = os.path.join(ROOT, "research", "vanilla-extract", "data", "descr_sm_factions.txt")

SMF = os.path.join(DATA, "descr_sm_factions.txt")
STRAT = os.path.join(DATA, "world", "maps", "campaign", "imperial_campaign", "descr_strat.txt")
EDU = os.path.join(DATA, "export_descr_unit.txt")
EXPANDED_BIN = os.path.join(DATA, "text", "expanded.txt.strings.bin")
NAMES_TXT = os.path.join(DATA, "descr_names.txt")

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

    # --- EDU ownership + per-faction general unit ---
    general_owners = set()
    edu_lines = read(EDU).split("\n")
    in_attrs_general = False
    for i, line in enumerate(edu_lines, 1):
        s = line.strip()
        if s.startswith("attributes"):
            in_attrs_general = re.search(r"\bgeneral_unit\b", s) is not None
        m = re.match(r"^ownership\s+(.*)$", s)
        if not m:
            continue
        owners = [n for n in re.split(r"[,\s]+", m.group(1).strip()) if n]
        for name in owners:
            if name not in registered and name not in CULTURES:
                err(f"export_descr_unit:{i}: ownership names unknown faction '{name}'")
        if in_attrs_general:
            general_owners.update(owners)
            in_attrs_general = False
    for f in strat_factions:
        if f == "slave":
            continue
        if f not in general_owners:
            err(f"export_descr_unit: no general_unit (bodyguard) owned by campaign faction '{f}'")

    # --- expanded.txt.strings.bin name keys for new factions ---
    if os.path.exists(EXPANDED_BIN):
        keys = {k for k, _ in strings_bin.read_bin(EXPANDED_BIN)}
        for f in new_factions:
            if f == "slave":
                continue
            for req in (f.upper(), f"{f.upper()}_STRENGTH", f"{f.upper()}_WEAKNESS"):
                if req not in keys:
                    err(f"expanded.txt.strings.bin: missing key {{{req}}} for '{f}'")
    else:
        err("text/expanded.txt.strings.bin missing")

    # --- descr_names: block + named strat characters present in pools ---
    if os.path.exists(NAMES_TXT):
        names_txt = read(NAMES_TXT)
        name_factions = set(re.findall(r"^faction:\s*(\w+)", names_txt, re.M))
        for f in strat_factions:
            if f != "slave" and f not in name_factions:
                err(f"descr_names.txt: no name-pool block for campaign faction '{f}'")
        pool_words = set(re.findall(r"^\t\t(.+?)\s*$", names_txt, re.M))
        strat_text = read(STRAT)
        char_refs = [m.group(1).strip() for m in re.finditer(
            r"^character\s+([^,]+),\s*named character", strat_text, re.M)]
        char_refs += [m.group(1).strip() for m in re.finditer(
            r"^character_record\s+([A-Za-z' ]+?),\s*(?:male|female)",
            strat_text.replace("\t", " "), re.M)]
        for full in char_refs:
            for p in full.split(" ", 1):
                # strat writes multi-word pool names with underscores (al_Alai
                # in strat = "al Alai" in the pool)
                norm = p.replace("_", " ")
                if norm not in pool_words and full not in pool_words:
                    err(f"descr_strat character '{full}': '{norm}' not in any descr_names pool")
    else:
        err("descr_names.txt missing")

    # --- EDB recruitment/building availability ---
    edb_path = os.path.join(DATA, "export_descr_buildings.txt")
    if os.path.exists(edb_path):
        edb = read(edb_path).lower()
        for f in new_factions:
            if f == "slave":
                continue
            if f in strat_factions and not re.search(rf"\b{f}\b", edb):
                err(f"export_descr_buildings: faction '{f}' has no entries (cannot recruit/build)")
    else:
        err("export_descr_buildings.txt missing (new factions cannot recruit)")

    # --- UI assets for new factions (vanilla ones live in packs) ---
    for f in new_factions:
        for rel in (
            f"ui/faction_symbols/{f}.tga",
            f"loading_screen/symbols/symbol128_{f}.tga",
            f"menu/symbols/fe_buttons_48/symbol48_{f}.tga",
            f"menu/symbols/fe_symbols_80/{f}.tga",
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
