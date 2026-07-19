#!/usr/bin/env python3
"""Contact sheets for visual verification of generated faction shield art
(project rule: every visual asset is checked on a PNG before handoff).

Writes docs/verify/sheet_faction_select.png (symbol48 variants, symbol24,
fe_symbols_80) and docs/verify/sheet_campaign.png (68x76 + 32x32 crests
cropped from the shipped atlases, ui/faction_symbols 54x54, symbol128).
Rows: the 13 generated factions in CANVAS_DONOR order, then vanilla
reference rows at the bottom. Checkered background exposes alpha edges.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tga
import gen_heraldry
import gen_logos

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
D_MENU = gen_heraldry.D_MENU
D_UI = gen_heraldry.D_UI
OUT = os.path.join(ROOT, "docs", "verify")

PAD = 10


def write_png(path, img):
    h, w = len(img), len(img[0])
    raw = b"".join(b"\x00" + b"".join(bytes(px) for px in row) for row in img)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(png)


def board(w, h):
    return [[(60, 60, 60, 255) if ((x // 8) + (y // 8)) % 2 == 0
             else (95, 95, 95, 255) for x in range(w)] for y in range(h)]


def paste(dst, img, ox, oy, scale):
    H, W = len(dst), len(dst[0])
    for y in range(len(img)):
        for x in range(len(img[0])):
            r, g, b, a = img[y][x]
            if a == 0:
                continue
            for dy in range(scale):
                for dx in range(scale):
                    Y, X = oy + y * scale + dy, ox + x * scale + dx
                    if 0 <= Y < H and 0 <= X < W:
                        if a == 255:
                            dst[Y][X] = (r, g, b, 255)
                        else:
                            br, bg, bb, _ = dst[Y][X]
                            dst[Y][X] = ((r * a + br * (255 - a)) // 255,
                                         (g * a + bg * (255 - a)) // 255,
                                         (b * a + bb * (255 - a)) // 255, 255)


def maybe(path):
    return tga.read(path) if os.path.exists(path) else None


def render(rows, cols, out_name):
    """rows: [(label, cell_loader)]; cols: [(width_px, scale)] — the loader
    returns one image (or None) per column."""
    grid = [[c for c in loader()] for _, loader in rows]
    col_w = []
    for ci, (_, scale) in enumerate(cols):
        w = max((len(g[ci][0]) * scale) for g in grid if g[ci]) if any(
            g[ci] for g in grid) else 20
        col_w.append(w)
    row_hs = []
    for g in grid:
        row_hs.append(max((len(g[ci]) * cols[ci][1] if g[ci] else 20)
                          for ci in range(len(cols))))
    W = PAD + sum(w + PAD for w in col_w)
    H = PAD + sum(h + PAD for h in row_hs)
    img = board(W, H)
    oy = PAD
    for ri, g in enumerate(grid):
        ox = PAD
        for ci in range(len(cols)):
            if g[ci]:
                paste(img, g[ci], ox, oy, cols[ci][1])
            ox += col_w[ci] + PAD
        oy += row_hs[ri] + PAD
    write_png(os.path.join(OUT, out_name), img)
    print(f"{out_name}: {W}x{H}, rows: {[label for label, _ in rows]}")


def main():
    facs = list(gen_heraldry.CANVAS_DONOR)

    # ---- sheet 1: faction select screen assets ----
    def select_row(base, fac):
        def load():
            return [
                maybe(os.path.join(base, "fe_buttons_48", f"symbol48_{fac}.tga")),
                maybe(os.path.join(base, "fe_buttons_48", f"symbol48_{fac}_roll.tga")),
                maybe(os.path.join(base, "fe_buttons_48", f"symbol48_{fac}_select.tga")),
                maybe(os.path.join(base, "fe_buttons_48", f"symbol48_{fac}_grey.tga")),
                maybe(os.path.join(base, "fe_buttons_24", f"symbol24_{fac}.tga")),
                maybe(os.path.join(base, "fe_symbols_80", f"{fac}.tga")),
            ]
        return load

    mod_menu = os.path.join(DATA, "menu", "symbols")
    rows = [(f, select_row(mod_menu, f)) for f in facs]
    rows += [(f"vanilla:{f}", select_row(D_MENU, f))
             for f in ("england", "hungary", "venice")]
    render(rows, [(0, 2)] * 6, "sheet_faction_select.png")

    # ---- sheet 2: campaign crests + faction_symbols + loading emblem ----
    strat = tga.read(os.path.join(DATA, "ui", "stratpage_ce_01.tga"))
    shared = tga.read(os.path.join(DATA, "ui", "sharedpage_ce_00.tga"))

    def atlas_cells(fac):
        i = gen_logos.ORDER.index(fac)
        big = gen_logos.crop(strat, 2 + (i % 7) * 72, 2 + (i // 7) * 80, 68, 76)
        small = gen_logos.crop(shared, 2 + (i % 14) * 36, 2 + (i // 14) * 36, 32, 32)
        return big, small

    def campaign_row(fac):
        def load():
            big, small = atlas_cells(fac)
            return [
                big, small,
                maybe(os.path.join(DATA, "ui", "faction_symbols", f"{fac}.tga")),
                maybe(os.path.join(DATA, "loading_screen", "symbols",
                                   f"symbol128_{fac}.tga")),
            ]
        return load

    def vanilla_campaign_row(fac):
        def load():
            game_ui = os.path.join(gen_logos.GAME, "data", "ui")
            vp = os.path.join(gen_logos.PAGES, "vanilla")
            big = gen_logos.load_crest(os.path.join(game_ui, "strategy.sd.xml"),
                                       vp, f"FACTION_LOGO_{fac.upper()}", 68, 76)
            small = gen_logos.load_crest(os.path.join(game_ui, "shared.sd.xml"),
                                         vp, f"SMALL_FACTION_LOGO_{fac.upper()}", 32, 32)
            return [big, small,
                    maybe(os.path.join(D_UI, f"{fac}.tga")),
                    maybe(os.path.join(D_MENU, f"symbol128_{fac}.tga"))]
        return load

    rows = [(f, campaign_row(f)) for f in facs]
    rows += [(f"vanilla:{f}", vanilla_campaign_row(f))
             for f in ("hungary", "venice", "byzantium")]
    render(rows, [(0, 2), (0, 2), (0, 2), (0, 1)], "sheet_campaign.png")


if __name__ == "__main__":
    main()
