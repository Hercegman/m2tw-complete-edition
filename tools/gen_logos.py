#!/usr/bin/env python3
"""Unique faction crests for the ranking screen, diplomacy scroll and the
campaign HUD shield — the way the Kingdoms DLCs did it.

Reverse-engineering result (verified): `logo_index`/`small_logo_index` tokens
are resolved BY SPRITE NAME in the runtime sprite registry, not via a
compiled enum (the BI DLC's FACTION_LOGO_WALES exists in no exe, yet works).

Round-7 lesson: the `sprite_format xml` route broke the registry in mod
scope (engine's xml->sd conversion failed; every unresolved sprite defaulted
to atlas index 0 -> "tower"/"1" everywhere). So we do EXACTLY what the BI
DLC ships: **patched BINARY ui/strategy.sd + ui/shared.sd** in the mod.
Binary layout (calibrated against the .sd.xml coords, byte-verified):
  header:  u32 magic=6, u32 numPages, u32 numSprites
  page:    u32 nameLen, name, blob = 14-byte header + (w*h)//8 hit-mask
           (32782 bytes for every 512x512 page - copied verbatim for ours)
  sprite:  u32 nameLen, name, 8 x u16 = (page, x0, x0+w-1, y0, y0+h-1, 1,0,0)
We append one page + 9 sprites to each file and bump the header counts.
Atlas TGAs: stratpage_ce_01.tga (68x76 crests), sharedpage_ce_00.tga (32x32);
Kingdoms four get genuine DLC crest pixels, the Balkan five get heraldry
composited into the CA crest frame.
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
         "wales", "ireland", "norway", "jerusalem",
         "teutonic_order", "lithuania", "novgorod", "antioch", "sweden",
         "bohemia", "aragon", "genoa", "pisa", "georgia", "armenia", "kievan_rus"]
# DLC faction -> (dlc mod name, page tga prefix dir in our dlc-extract)
DLC = {
    "wales": "british_isles", "ireland": "british_isles",
    "norway": "british_isles", "jerusalem": "crusades",
    "teutonic_order": "teutonic", "lithuania": "teutonic",
    "novgorod": "teutonic", "antioch": "crusades",
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
    """Write the heraldry into the donor crest, MODULATED by the donor's
    luminance so the CA embossing/shading survives — the design looks
    painted onto the sculpted shield instead of a flat sticker."""
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
                lum = (r * 30 + g * 55 + b * 15) // 100
                f = 0.45 + (lum / 255.0) * 0.85       # 0.45 .. 1.30
                dr, dg, db = design[y][x]
                row.append((min(255, int(dr * f)), min(255, int(dg * f)),
                            min(255, int(db * f)), a))
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


def parse_pages(xml_text):
    """ordered [(page_file, w, h)] from an sd.xml (dims drive blob sizes)."""
    return [(m.group(1), int(m.group(2)), int(m.group(3))) for m in
            re.finditer(r'<page file="([^"]+)" w="(\d+)" h="(\d+)"', xml_text)]


def patch_sd(base_sd_path, xml_text, page_name, sprites, out_path):
    """Append one 512x512 page + sprite records to a binary .sd (BI-style)."""
    import struct
    d = open(base_sd_path, "rb").read()
    magic, npages, nsprites = struct.unpack("<III", d[:12])
    assert magic == 6, base_sd_path
    pages = parse_pages(xml_text)[:npages]

    off = 12
    donor_blob = None
    for name, w, h in pages:
        (nl,) = struct.unpack_from("<I", d, off)
        fname = d[off + 4:off + 4 + nl].decode("latin1")
        assert fname == name, (fname, name)
        blob_len = 14 + (w * h) // 8
        blob = d[off + 4 + nl: off + 4 + nl + blob_len]
        if w == 512 and h == 512 and donor_blob is None:
            donor_blob = blob
        off += 4 + nl + blob_len
    pages_end = off
    assert donor_blob is not None and len(donor_blob) == 32782

    # sanity: the sprite table starts here with a plausible name record
    (first_len,) = struct.unpack_from("<I", d, pages_end)
    assert 0 < first_len < 128, f"bad sprite table start in {base_sd_path}"

    new_page = struct.pack("<I", len(page_name)) + page_name.encode() + donor_blob
    new_sprites = b""
    for tok, (x, y, w, h) in sprites:
        new_sprites += struct.pack("<I", len(tok)) + tok.encode()
        new_sprites += struct.pack("<8H", npages, x, x + w - 1, y, y + h - 1, 1, 0, 0)

    out = (struct.pack("<III", magic, npages + 1, nsprites + len(sprites))
           + d[12:pages_end] + new_page + d[pages_end:] + new_sprites)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "wb").write(out)
    return npages


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

    # patch the BINARY .sd files (the mechanism the BI DLC ships and the
    # engine provenly loads from mod scope)
    sd_src = os.path.join(ROOT, "research", "base-extract", "data_sd")
    big_tokens = [f"FACTION_LOGO_{f.upper()}" for f in ORDER]
    small_tokens = [f"SMALL_FACTION_LOGO_{f.upper()}" for f in ORDER]
    patch_sd(os.path.join(sd_src, "strategy.sd"), strat_xml, "stratpage_ce_01.tga",
             [(tok, (x, y, BIG_W, BIG_H)) for tok, (x, y) in zip(big_tokens, big_xy)],
             os.path.join(out_ui, "strategy.sd"))
    patch_sd(os.path.join(sd_src, "shared.sd"), shared_xml, "sharedpage_ce_00.tga",
             [(tok, (x, y, SM_W, SM_H)) for tok, (x, y) in zip(small_tokens, small_xy)],
             os.path.join(out_ui, "shared.sd"))

    # the failed round-7 xml route must not linger in the mod
    for stale in ("strategy.sd.xml", "shared.sd.xml"):
        p = os.path.join(out_ui, stale)
        if os.path.exists(p):
            os.remove(p)

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
          f"patched binary strategy.sd + shared.sd shipped, sm_factions tokens set")


if __name__ == "__main__":
    main()
