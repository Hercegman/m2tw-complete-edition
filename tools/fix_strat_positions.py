#!/usr/bin/env python3
"""Place every new faction's characters on verified tiles computed from
map_regions.tga, and evict foreign leftover garrisons from taken settlements.

Round-5 root causes this fixes:
  * croatia-overhaul strat coordinates were eyeballed — leaders spawned in the
    Vienna region (map tile ~157,11x) instead of Zagreb/Ragusa/etc., so
    settlements had no garrison and several agents sat on invalid tiles.
  * vanilla garrison generals were left standing ON settlements whose blocks
    were moved to new factions (venice's general on Ragusa, hungary's on
    Bran) — an army on a settlement tile owns it, so the engine handed those
    settlements back to venice/hungary and the new faction was destroyed.

Method: map_regions.tga (295x189, 24-bit, bottom-up; strat x,y == pixel x,row)
marks each region's city with a black pixel; the region is identified from
neighbouring pixels via the descr_regions colour table. The leader goes ON the
city tile (garrison), everyone else on distinct land tiles of the same region.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
STRAT = os.path.join(DATA, "world", "maps", "campaign", "imperial_campaign", "descr_strat.txt")
REGIONS_TXT = os.path.join(DATA, "world", "maps", "base", "descr_regions.txt")
MAP_TGA = os.path.join(ROOT, "research", "base-extract", "data_map", "map_regions.tga")

NEW_FACTIONS = ["croatia", "ragusa", "serbia", "bulgaria", "wallachia",
                "wales", "ireland", "norway", "jerusalem"]


def read_regions_colors():
    txt = open(REGIONS_TXT, encoding="latin-1").read()
    colors = {}
    name = None
    for line in txt.split("\n"):
        line = re.sub(r";.*", "", line)
        if re.match(r"^[\w-]+\s*$", line):
            name = line.strip()
            continue
        m = re.match(r"^\s+(\d+)\s+(\d+)\s+(\d+)\s*$", line)
        if m and name:
            colors[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = name
            name = None
    return colors


def read_map():
    d = open(MAP_TGA, "rb").read()
    w, h = struct.unpack_from("<HH", d, 12)
    assert d[2] == 2 and d[16] == 24, "expected uncompressed 24-bit map_regions"
    px = {}
    off = 18
    for row in range(h):          # bottom-up: file row == strat y
        for x in range(w):
            b, g, r = d[off], d[off + 1], d[off + 2]
            px[(x, row)] = (r, g, b)
            off += 3
    return w, h, px


def build_region_map():
    colors = read_regions_colors()
    w, h, px = read_map()
    city = {}
    tiles = {}
    for (x, y), c in px.items():
        if c in colors:
            tiles.setdefault(colors[c], []).append((x, y))
        elif c == (0, 0, 0):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = px.get((x + dx, y + dy))
                if n in colors:
                    city[colors[n]] = (x, y)
                    break
    return city, tiles


def main():
    city, tiles = build_region_map()

    strat = open(STRAT, encoding="latin-1").read()
    lines = strat.split("\n")

    # faction -> its settlement region (first settlement block in section)
    fac_region = {}
    cur = None
    for line in lines:
        m = re.match(r"^faction\s+(\w+)", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"^\s+region\s+(\S+)", line)
        if m and cur and cur not in fac_region:
            fac_region[cur] = m.group(1)

    for f in NEW_FACTIONS:
        assert f in fac_region, f"no settlement region for {f}"
        assert fac_region[f] in city, f"no city pixel for {fac_region[f]}"

    taken_cities = {city[fac_region[f]]: f for f in NEW_FACTIONS}
    used = set(taken_cities)

    def free_tile(region, near):
        cands = sorted(tiles.get(region, []),
                       key=lambda t: abs(t[0] - near[0]) + abs(t[1] - near[1]))
        for t in cands:
            if t not in used:
                used.add(t)
                return t
        raise RuntimeError(f"no free tile in {region}")

    char_re = re.compile(r"^(character\s+.*?,\s*)x\s+(\d+),\s*y\s+(\d+)(.*)$")

    out = []
    cur = None
    moved, evicted = 0, 0
    for line in lines:
        m = re.match(r"^faction\s+(\w+)", line)
        if m:
            cur = m.group(1)
            out.append(line)
            continue
        m = char_re.match(line)
        if not m:
            out.append(line)
            continue
        x, y = int(m.group(2)), int(m.group(3))
        if cur in NEW_FACTIONS:
            region = fac_region[cur]
            if ", leader," in line:
                nx, ny = city[region]           # leader garrisons the settlement
            else:
                nx, ny = free_tile(region, city[region])
            out.append(f"{m.group(1)}x {nx}, y {ny}{m.group(4)}")
            moved += 1
        elif (x, y) in taken_cities and taken_cities[(x, y)] != cur:
            # foreign leftover garrison standing on a taken settlement — send
            # it home to its own capital region
            home = fac_region.get(cur)
            if home and home in city:
                nx, ny = free_tile(home, city[home])
                out.append(f"{m.group(1)}x {nx}, y {ny}{m.group(4)}")
                evicted += 1
            else:
                out.append(line)
        else:
            out.append(line)

    with open(STRAT, "w", encoding="latin-1", newline="\n") as f:
        f.write("\n".join(out))
    print(f"strat positions: {moved} new-faction characters repositioned, "
          f"{evicted} foreign garrisons evicted")
    for f in NEW_FACTIONS:
        print(f"  {f}: {fac_region[f]} city at {city[fac_region[f]]}")
    if evicted == 0:
        print("  WARNING: no foreign garrison evicted — check venice/hungary manually")


if __name__ == "__main__":
    main()
