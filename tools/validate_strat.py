#!/usr/bin/env python3
"""descr_strat sanity validator for Complete Edition.

Checks:
  * every settlement region is owned by exactly one faction (incl. slave)
  * every settlement region exists in descr_regions
  (regions without a settlement are fine — the engine auto-creates a rebel
   village; vanilla itself leaves Durazzo_Province unassigned)

Exit code 0 = clean, 1 = problems.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
STRAT = os.path.join(DATA, "world", "maps", "campaign", "imperial_campaign", "descr_strat.txt")
REGIONS = os.path.join(DATA, "world", "maps", "base", "descr_regions.txt")

errors = []


def err(msg):
    errors.append(msg)


def main():
    strat = open(STRAT, encoding="utf-8", errors="replace").read()
    regions_txt = open(REGIONS, encoding="utf-8", errors="replace").read()

    # region names: non-indented identifier lines starting a region block
    # (\w plus '-' — e.g. Volga-Bulgar_Province)
    region_names = set(re.findall(r"^([\w-]+)\s*$",
                                  re.sub(r";.*", "", regions_txt), re.M))
    region_names = {r for r in region_names if not r.isdigit()}

    owners = {}  # region -> [faction, ...]
    current = None
    for line in strat.split("\n"):
        m = re.match(r"^faction\s+(\w+)", line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r"^\s+region\s+(\S+)", line)
        if m and current:
            owners.setdefault(m.group(1), []).append(current)

    for region, facs in sorted(owners.items()):
        if len(facs) > 1:
            err(f"region '{region}' owned by {len(facs)} factions: {facs}")
        if region not in region_names:
            err(f"region '{region}' in descr_strat not found in descr_regions")

    if errors:
        print(f"FAIL — {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK — {len(owners)} settlements, every region owned exactly once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
