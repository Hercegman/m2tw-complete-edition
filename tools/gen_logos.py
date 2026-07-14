#!/usr/bin/env python3
"""Unique faction crests for the ranking screen, diplomacy scroll and the
campaign HUD shield — the way the Kingdoms DLCs did it.

Reverse-engineering result (verified): `logo_index`/`small_logo_index` tokens
are resolved BY SPRITE NAME in the runtime sprite registry, not via a
compiled enum (the BI DLC's FACTION_LOGO_WALES exists in no exe, yet works).
M2EX runs `sprite_format xml`, so sprites are authored in ui/strategy.sd.xml
and ui/shared.sd.xml with plain TGA atlas pages — no binary .sd editing.

We ship: complete strategy.sd.xml + shared.sd.xml (M2EX's root files + our
page block), stratpage_ce_01.tga (big 68x76 crests) and sharedpage_ce_00.tga
(small 32x32), and point each new faction's logo_index at its own token.
Kingdoms four get their genuine DLC crest pixels; the Balkan five get the
heraldry composited into the CA crest frame (donor crests define the mask).
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tga
import gen_heraldry

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
GAME = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Medieval II Total War"
PAGES = os.path.join(ROOT, "research", "base-extract", "data_pages")

BIG_W, BIG_H = 68, 76
SM_W, SM_H = 32, 32

ORDER = ["croatia", "ragusa", "serbia", "bulgaria", "wallachia",
         "wales", "ireland", "norway", "jerusalem"]
BALKAN = ORDER[:5]
# DLC faction -> (dlc mod name, page tga prefix dir in our dlc-extract)
DLC = {
    "wales": "british_isles", "ireland": "british_isles",
    "norway": "british_isles", "jerusalem": "crusades",
}
FRAME_DONORS = ["hungary", "venice", "byzantium"]

INTERFACE = os.path.join("ui", "southern_european", "interface")  # full vanilla page set


def parse_sprites(xml_text):
    """{sprite name: (page_file, x, y, w, h)}"""
    out = {}
    page = None
    for m in re.finditer(r'<page file="([^"]+)"|<sprite name="([^"]+)" x="(\d+)" y="(\d+)" w="(\d+)" h="(\d+)"', xml_text):
        if m.group(1):
            page = m.group(1)
        else:
            out[m.group(2)] = (page, int(m.group(3)), int(m.group(4)),
                               int(m.group(5)), int(m.group(6)))
    return out


def crop(img, x, y, w, h):
    return [row[x:x + w] for row in img[y:y + h]]


def load_crest(sd_xml_path, page_dir, token, want_w, want_h):
    sprites = parse_sprites(open(sd_xml_path, encoding="latin-1").read())
    assert token in sprites, f"{token} not in {sd_xml_path}"
    page, x, y, w, h = sprites[token]
    img = tga.read(os.path.join(page_dir, page))
    c = crop(img, x, y, w, h)
    # pad if the source sprite is slightly smaller (e.g. 68x73 timurid style)
    while len(c) < want_h:
        c.append([(0, 0, 0, 0)] * len(c[0]))
    for row in c:
        while len(row) < want_w:
            row.append((0, 0, 0, 0))
    return [row[:want_w] for row in c[:want_h]]


def frame_mask(crests):
    h, w = len(crests[0]), len(crests[0][0])
    mask = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            p0 = crests[0][y][x]
            if p0[3] == 0:
                continue
            if all(c[y][x] == p0 for c in crests[1:]):
                mask[y][x] = True
    return mask


def composite_crest(canvas, mask, fac):
    h, w = len(canvas), len(canvas[0])
    design = gen_heraldry.draw_design(fac, w, h)
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b, a = canvas[y][x]
            if a == 0 or mask[y][x]:
                row.append((r, g, b, a))
            else:
                dr, dg, db = design[y][x]
                row.append((dr, dg, db, a))
        out.append(row)
    return out


def build_atlas(crests, cw, ch, cols):
    rows = (len(crests) + cols - 1) // cols
    W = H = 512
    atlas = [[(0, 0, 0, 0)] * W for _ in range(H)]
    coords = []
    for i, crest in enumerate(crests):
        x = 2 + (i % cols) * (cw + 4)
        y = 2 + (i // cols) * (ch + 4)
        for yy in range(ch):
            for xx in range(cw):
                atlas[y + yy][x + xx] = crest[yy][xx]
        coords.append((x, y))
    return atlas, coords


def main():
    game_ui = os.path.join(GAME, "data", "ui")
    strat_xml = open(os.path.join(game_ui, "strategy.sd.xml"), encoding="latin-1").read()
    shared_xml = open(os.path.join(game_ui, "shared.sd.xml"), encoding="latin-1").read()

    vanilla_pages = os.path.join(PAGES, "vanilla")

    # donor crests for the frame mask + canvases
    big_donors = [load_crest(os.path.join(game_ui, "strategy.sd.xml"), vanilla_pages,
                             f"FACTION_LOGO_{d.upper()}", BIG_W, BIG_H)
                  for d in FRAME_DONORS]
    small_donors = [load_crest(os.path.join(game_ui, "shared.sd.xml"), vanilla_pages,
                               f"SMALL_FACTION_LOGO_{d.upper()}", SM_W, SM_H)
                    for d in FRAME_DONORS]
    big_mask = frame_mask(big_donors)
    small_mask = frame_mask(small_donors)

    big, small = [], []
    for fac in ORDER:
        if fac in DLC:
            dlc = DLC[fac]
            dlc_ui = os.path.join(GAME, "mods", dlc, "data", "ui")
            dlc_pages = os.path.join(PAGES, dlc)
            big.append(load_crest(os.path.join(dlc_ui, "strategy.sd.xml"), dlc_pages,
                                  f"FACTION_LOGO_{fac.upper()}", BIG_W, BIG_H))
            small.append(load_crest(os.path.join(dlc_ui, "shared.sd.xml"), dlc_pages,
                                    f"SMALL_FACTION_LOGO_{fac.upper()}", SM_W, SM_H))
        else:
            big.append(composite_crest(big_donors[0], big_mask, fac))
            small.append(composite_crest(small_donors[0], small_mask, fac))

    big_atlas, big_xy = build_atlas(big, BIG_W, BIG_H, 7)
    small_atlas, small_xy = build_atlas(small, SM_W, SM_H, 14)

    out_ui = os.path.join(DATA, "ui")
    os.makedirs(out_ui, exist_ok=True)
    tga.write(os.path.join(out_ui, "stratpage_ce_01.tga"), big_atlas, origin_topdown=True)
    tga.write(os.path.join(out_ui, "sharedpage_ce_00.tga"), small_atlas, origin_topdown=True)

    def page_block(pagefile, tokens, coords, w, h):
        lines = [f'  <page file="{pagefile}" w="512" h="512">']
        for (x, y), tok in zip(coords, tokens):
            lines.append(f'    <sprite name="{tok}" x="{x}" y="{y}" w="{w}" h="{h}" alpha="1"/>')
        lines.append("  </page>")
        return "\n".join(lines) + "\n"

    big_tokens = [f"FACTION_LOGO_{f.upper()}" for f in ORDER]
    small_tokens = [f"SMALL_FACTION_LOGO_{f.upper()}" for f in ORDER]
    strat_out = strat_xml.replace("</sprite_definitions>",
                                  page_block("stratpage_ce_01.tga", big_tokens, big_xy, BIG_W, BIG_H)
                                  + "</sprite_definitions>")
    shared_out = shared_xml.replace("</sprite_definitions>",
                                    page_block("sharedpage_ce_00.tga", small_tokens, small_xy, SM_W, SM_H)
                                    + "</sprite_definitions>")
    with open(os.path.join(out_ui, "strategy.sd.xml"), "w", encoding="latin-1", newline="\n") as f:
        f.write(strat_out)
    with open(os.path.join(out_ui, "shared.sd.xml"), "w", encoding="latin-1", newline="\n") as f:
        f.write(shared_out)

    # page TGAs must be findable from every culture's interface dir as well
    for culture in ("southern_european", "northern_european", "eastern_european",
                    "middle_eastern", "greek"):
        cdir = os.path.join(out_ui, culture, "interface")
        os.makedirs(cdir, exist_ok=True)
        for fn in ("stratpage_ce_01.tga", "sharedpage_ce_00.tga"):
            shutil.copyfile(os.path.join(out_ui, fn), os.path.join(cdir, fn))

    # point descr_sm_factions at the new tokens
    smf_path = os.path.join(DATA, "descr_sm_factions.txt")
    smf = open(smf_path, encoding="latin-1").read()
    for fac in ORDER:
        up = fac.upper()
        smf = re.sub(rf"(^faction\s+{fac}\b.*?^logo_index\s+)\S+",
                     rf"\g<1>FACTION_LOGO_{up}", smf, count=1, flags=re.M | re.S)
        smf = re.sub(rf"(^faction\s+{fac}\b.*?^small_logo_index\s+)\S+",
                     rf"\g<1>SMALL_FACTION_LOGO_{up}", smf, count=1, flags=re.M | re.S)
    with open(smf_path, "w", encoding="latin-1", newline="\n") as f:
        f.write(smf)

    print(f"logos: {len(ORDER)} big + small crests -> stratpage_ce_01/sharedpage_ce_00, "
          f"sd.xml shipped, sm_factions tokens set")


if __name__ == "__main__":
    main()
