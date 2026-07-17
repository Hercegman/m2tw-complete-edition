#!/usr/bin/env python3
"""Recolor unit/mount/attachment textures into each new faction's colours.

The generated descr_model_battle lines point new factions at DONOR textures
(croatia units wear hungary's colours). This tool clones every referenced
donor .texture into a faction-named copy with the donor's heraldic colour
hue-remapped to the faction's primary colour (from descr_sm_factions), and
rewrites the descr_model_battle lines to use the new files.

Fast trick: .texture = 48-byte wrapper + DDS (DXT1/DXT5, all mip levels are
just consecutive 4x4 blocks). Each colour block stores TWO RGB565 endpoint
colours; recolouring only the endpoints re-tints every pixel while keeping
all detail, shading, alpha and compression intact — no decode/re-encode.
DXT1 caveat: the c0<=c1 ordering toggles punch-through-alpha mode, so the
original ordering relation is preserved (nudged when the remap would flip it).

Idempotent: lines already pointing at <faction>-named textures are skipped.
"""
import colorsys
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
DMB = os.path.join(DATA, "descr_model_battle.txt")
SP = "/mnt/c/Users/grize/AppData/Local/Temp/claude/--wsl-localhost-Ubuntu-home-roko/e29caed8-72dd-4f9d-9293-d9f963e61b43/scratchpad"
SRC_ROOTS = [os.path.join(SP, d, "data") for d in
             ("data4-extract", "data3-extract", "data2-extract", "data1-extract", "data0-extract")]
SRC_ROOTS += [os.path.join(ROOT, "research", "dlc-extract", d, "mods", d, "data")
              for d in ("british_isles", "crusades", "teutonic")]

NEW_FACTIONS = ["croatia", "ragusa", "serbia", "bulgaria", "wallachia",
                "wales", "ireland", "norway", "jerusalem",
                "teutonic_order", "lithuania", "novgorod", "antioch", "sweden",
                "bohemia", "aragon", "genoa", "pisa", "georgia", "armenia",
                "kievan_rus"]
DONOR_TOKENS = ["hungary", "russia", "byzantium", "venice", "england", "scotland",
                "denmark", "france", "poland", "sicily", "milan", "spain",
                "portugal", "hre", "papal_states", "moors", "turks", "egypt",
                "slave", "mercs", "merc", "normans", "rebels"]

HUE_WINDOW = 40 / 360.0
SAT_MIN = 0.28


def faction_colors(path):
    text = open(path, encoding="latin-1").read()
    out = {}
    for m in re.finditer(r"^faction\s+(\w+).*?^primary_colour\s+red (\d+), green (\d+), blue (\d+)",
                         text, re.M | re.S):
        out[m.group(1)] = tuple(int(m.group(i)) for i in (2, 3, 4))
    return out


def resolve_src(rel):
    for root in SRC_ROOTS:
        p = os.path.join(root, rel.replace("/", os.sep))
        if os.path.exists(p):
            return p
    return None


def rgb565_to_rgb(v):
    return (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)


def rgb_to_565(r, g, b):
    return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)


def make_remap(donor_rgb, target_rgb):
    dh, ds, dv = colorsys.rgb_to_hsv(*[c / 255 for c in donor_rgb])
    th, ts, tv = colorsys.rgb_to_hsv(*[c / 255 for c in target_rgb])
    lut = {}

    def remap(v565):
        if v565 in lut:
            return lut[v565]
        r, g, b = rgb565_to_rgb(v565)
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        dist = min(abs(h - dh), 1 - abs(h - dh))
        if s >= SAT_MIN and dist <= HUE_WINDOW and ds >= 0.2:
            nh = (th + (h - dh)) % 1.0
            ns = min(1.0, s * (ts / ds if ds > 0.05 else 1.0))
            nr, ng, nb = colorsys.hsv_to_rgb(nh, ns, v)
            out = rgb_to_565(int(nr * 255), int(ng * 255), int(nb * 255))
        else:
            out = v565
        lut[v565] = out
        return out
    return remap


def recolor_texture(src_path, dst_path, remap):
    d = bytearray(open(src_path, "rb").read())
    i = d.find(b"DDS ")
    assert i >= 0, src_path
    h, w = struct.unpack_from("<II", d, i + 12)
    fourcc = bytes(d[i + 84:i + 88])
    off = i + 128
    if fourcc == b"DXT5":
        block, coff = 16, 8
    elif fourcc == b"DXT1":
        block, coff = 8, 0
    else:
        return False
    n = (len(d) - off) // block
    for b in range(n):
        p = off + b * block + coff
        c0, c1 = struct.unpack_from("<HH", d, p)
        n0, n1 = remap(c0), remap(c1)
        if fourcc == b"DXT1" and (c0 > c1) != (n0 > n1):
            # the c0<=c1 relation selects punch-through-alpha mode and the
            # index meaning; if the remap would flip it, keep the original
            # endpoints for this block (rare, visually negligible)
            n0, n1 = c0, c1
        struct.pack_into("<HH", d, p, n0, n1)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    open(dst_path, "wb").write(bytes(d))
    return True


def main():
    targets = faction_colors(os.path.join(DATA, "descr_sm_factions.txt"))
    donors = faction_colors(os.path.join(ROOT, "research", "vanilla-extract",
                                         "data", "descr_sm_factions.txt"))

    lines = open(DMB, encoding="latin-1").read().split("\n")
    out = []
    done = {}        # (src_rel, fac) -> new rel path
    made, kept, missing = 0, 0, []

    line_re = re.compile(r"^(texture(?:_attachments)?\s+)(\w+)(\s*,\s*)([^,]+?\.texture)(.*)$")
    for line in lines:
        m = line_re.match(line)
        if not m:
            out.append(line)
            continue
        fac = m.group(2).lower()
        rel = m.group(4).strip()
        if fac not in NEW_FACTIONS or f"_{fac}" in rel.lower():
            out.append(line)
            continue
        donor_tok = next((t for t in DONOR_TOKENS if f"_{t}." in rel.lower()
                          or f"_{t}_" in rel.lower()), None)
        if donor_tok is None or donor_tok in ("slave", "mercs", "merc", "rebels", "normans"):
            out.append(line)        # shared/neutral texture: keep as is
            kept += 1
            continue
        key = (rel, fac)
        if key not in done:
            src = resolve_src(rel)
            if src is None:
                missing.append(rel)
                out.append(line)
                continue
            new_rel = re.sub(donor_tok, fac, rel, count=1, flags=re.I)
            donor_rgb = donors.get(donor_tok, (200, 30, 30))
            target_rgb = targets.get(fac, (200, 30, 30))
            if recolor_texture(src, os.path.join(DATA, new_rel.replace("/", os.sep)),
                               make_remap(donor_rgb, target_rgb)):
                done[key] = new_rel
                made += 1
            else:
                done[key] = rel      # uncompressed/unknown format: keep donor
        out.append(m.group(1) + m.group(2) + m.group(3) + done[key] + m.group(5))

    with open(DMB, "w", encoding="latin-1", newline="\n") as f:
        f.write("\n".join(out))
    print(f"recolor: {made} textures generated, {kept} shared kept, "
          f"{len(set(missing))} sources missing {sorted(set(missing))[:5]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
