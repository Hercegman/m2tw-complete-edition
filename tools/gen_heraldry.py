#!/usr/bin/env python3
"""Generate faction art for the Balkan five by compositing custom heraldry
INTO genuine CA icon canvases — frame, shape, alpha and anti-aliasing stay
byte-for-byte vanilla (the maintainer: "identical").

Method (verified on the extracted vanilla art):
  * every menu icon type shares its alpha mask across ALL factions;
  * the metallic frame = pixels identical across factions;
  * so: canvas = donor faction's file (per variant), frame mask = pixels
    identical across three donors, heraldry written only into the interior.

Designs: croatia chequy (Croatian checkerboard), serbian cross with firesteels,
bulgarian gold saltire, ragusan white/blue/red, wallachian gold pale + sun.

Also regenerates the battle-banner .texture files and the strat symbol .cas
textures (unchanged mechanics from earlier rounds).

DLC factions (wales/ireland/norway/jerusalem) keep their genuine Kingdoms
art and are not touched here.
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tga

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
BASE_MS = os.path.join(ROOT, "research", "base-extract", "data", "models_strat")
D_MENU = os.path.join(ROOT, "research", "base-extract", "data_menu")
D_UI = os.path.join(ROOT, "research", "base-extract", "data_ui")

GOLD = (212, 175, 55)
WHITE = (240, 240, 240)

FRAME_DONORS = ["hungary", "venice", "england"]

# canvas donor per faction (visual base whose frame we keep — any works,
# use the roster mate for consistency); also the fe_faction_units montage
CANVAS_DONOR = {
    "croatia": "hungary",
    "ragusa": "venice",
    "serbia": "byzantium",
    "bulgaria": "byzantium",
    "wallachia": "hungary",
}

# .cas donor whose texture-path string has the SAME LENGTH (binary patch)
CAS_DONOR = {
    "croatia": "hungary",      # 7 = 7
    "ragusa": "venice",        # 6 = 6
    "serbia": "france",        # 6 = 6
    "bulgaria": "scotland",    # 8 = 8
    "wallachia": "byzantium",  # 9 = 9
}

BANNER_W, BANNER_H = 1024, 512


# ---------------- designs (RGB matrix) ----------------

def buf(w, h, color):
    return [[color] * w for _ in range(h)]


def frect(b, fx0, fy0, fx1, fy1, color):
    h, w = len(b), len(b[0])
    for y in range(max(0, int(fy0 * h)), min(h, int(fy1 * h))):
        for x in range(max(0, int(fx0 * w)), min(w, int(fx1 * w))):
            b[y][x] = color


def border(b, frac, color):
    h, w = len(b), len(b[0])
    t = max(1, int(min(w, h) * frac))
    frect(b, 0, 0, 1, 0, color)
    for y in range(h):
        for x in range(w):
            if x < t or x >= w - t or y < t or y >= h - t:
                b[y][x] = color


def checker(b, n, c1, c2):
    h, w = len(b), len(b[0])
    for y in range(h):
        for x in range(w):
            b[y][x] = c1 if ((x * n // w) + (y * n // h)) % 2 == 0 else c2


def saltire(b, frac, color):
    h, w = len(b), len(b[0])
    t = min(w, h) * frac
    for y in range(h):
        for x in range(w):
            fx, fy = x / w, y / h
            if abs(fx - fy) * min(w, h) < t or abs(fx + fy - 1) * min(w, h) < t:
                b[y][x] = color


def circle(b, fcx, fcy, frad, color):
    h, w = len(b), len(b[0])
    cx, cy, r = fcx * w, fcy * h, frad * min(w, h)
    for y in range(h):
        for x in range(w):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                b[y][x] = color


def draw_design(fac, w, h):
    b = buf(w, h, WHITE)
    if fac == "croatia":
        checker(b, 5, (200, 25, 35), WHITE)
    elif fac == "serbia":
        b = buf(w, h, (175, 20, 30))
        frect(b, 0.42, 0.0, 0.58, 1.0, WHITE)
        frect(b, 0.0, 0.42, 1.0, 0.58, WHITE)
        for fx, fy in ((0.17, 0.17), (0.67, 0.17), (0.17, 0.67), (0.67, 0.67)):
            frect(b, fx, fy, fx + 0.16, fy + 0.16, WHITE)
            frect(b, fx + 0.04, fy + 0.04, fx + 0.12, fy + 0.12, (175, 20, 30))
    elif fac == "bulgaria":
        b = buf(w, h, (135, 15, 25))
        saltire(b, 0.09, GOLD)
        border(b, 0.05, GOLD)
    elif fac == "ragusa":
        b = buf(w, h, WHITE)
        frect(b, 0.0, 0.36, 1.0, 0.64, (35, 85, 165))
        border(b, 0.06, (190, 30, 35))
    elif fac == "wallachia":
        b = buf(w, h, (25, 55, 135))
        frect(b, 0.40, 0.0, 0.60, 1.0, GOLD)
        circle(b, 0.5, 0.26, 0.11, WHITE)
    else:
        raise ValueError(fac)
    return b


def shield_alpha(w, h):
    """Heater-shield alpha used only where no CA canvas exists (standards
    atlas cells)."""
    alpha = []
    for y in range(h):
        fy = y / (h - 1)
        if fy < 0.02 or fy > 0.97:
            hw = 0.0
        elif fy <= 0.5:
            hw = 0.46
        else:
            hw = 0.46 * max(0.0, 1.0 - ((fy - 0.5) / 0.47) ** 1.7)
        alpha.append([255 if abs(x / (w - 1) - 0.5) <= hw else 0 for x in range(w)])
    return alpha


# ---------------- variant tints ----------------

def tint(px, variant):
    r, g, b = px
    if variant == "roll":
        return (min(255, r + 40), min(255, g + 40), min(255, b + 40))
    if variant == "select":
        return (min(255, r + 25), min(255, g + 25), min(255, b + 25))
    if variant == "grey":
        l = (r * 3 + g * 6 + b) // 10
        return (max(0, l - 15), max(0, l - 10), min(255, l + 15))
    return px


# ---------------- compositing ----------------

def frame_mask(paths):
    """pixels identical across all given canvases (and opaque) = frame."""
    imgs = [tga.read(p) for p in paths]
    h, w = len(imgs[0]), len(imgs[0][0])
    mask = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            p0 = imgs[0][y][x]
            if p0[3] == 0:
                continue
            if all(im[y][x] == p0 for im in imgs[1:]):
                mask[y][x] = True
    return mask


def composite(canvas_path, mask, fac, variant, out_path):
    canvas = tga.read(canvas_path)
    h, w = len(canvas), len(canvas[0])
    design = draw_design(fac, w, h)
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b, a = canvas[y][x]
            if a == 0 or mask[y][x]:
                row.append((r, g, b, a))          # outside or frame: keep CA art
            else:
                dr, dg, db = tint(design[y][x], variant)
                row.append((dr, dg, db, a))       # interior: our heraldry
        out.append(row)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tga.write(out_path, out, origin_topdown=False)


# ---------------- DDS / .texture writers (battle banners, strat symbols) ----

def dds_bytes(rgb):
    h, w = len(rgb), len(rgb[0])
    hdr = struct.pack(
        "<4sIIIIIII44xIIIIIIIIIIII4x",
        b"DDS ", 124, 0x0000100F, h, w, w * 4, 0, 0,
        32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000,
        0x1000, 0, 0, 0)
    body = bytearray()
    for row in rgb:
        for r, g, b in row:
            body += bytes((b, g, r, 255))
    return hdr + bytes(body)


def main():
    menu_out = os.path.join(DATA, "menu", "symbols")
    variants = [("", "base"), ("_roll", "roll"), ("_select", "select"), ("_grey", "grey")]

    # precompute frame masks per (dir, pattern, variant)
    button_sets = [("fe_buttons_48", "symbol48_{f}{v}.tga"),
                   ("fe_buttons_24", "symbol24_{f}{v}.tga")]
    single_sets = [("fe_symbols_80", "{f}.tga")]

    for fac in CANVAS_DONOR:
        donor = CANVAS_DONOR[fac]

        # --- menu buttons with 4 variants ---
        for d, pat in button_sets:
            for suffix, variant in variants:
                paths = [os.path.join(D_MENU, d, pat.format(f=df, v=suffix))
                         for df in FRAME_DONORS]
                mask = frame_mask(paths)
                canvas = os.path.join(D_MENU, d, pat.format(f=donor, v=suffix))
                if not os.path.exists(canvas):
                    canvas = paths[0]
                composite(canvas, mask, fac, variant,
                          os.path.join(menu_out, d, pat.format(f=fac, v=suffix)))

        # --- single-file menu emblems ---
        for d, pat in single_sets:
            paths = [os.path.join(D_MENU, d, pat.format(f=df)) for df in FRAME_DONORS]
            mask = frame_mask(paths)
            canvas = os.path.join(D_MENU, d, pat.format(f=donor))
            if not os.path.exists(canvas):
                canvas = paths[0]
            composite(canvas, mask, fac, "base",
                      os.path.join(menu_out, d, pat.format(f=fac)))

        # --- fe_faction_units: unit-roster montage, no compositable frame ---
        src = os.path.join(D_MENU, "fe_faction_units", f"{donor}.tga")
        dst = os.path.join(menu_out, "fe_faction_units", f"{fac}.tga")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)

        # --- loading screen emblem (correct path: data/loading_screen/...) ---
        paths = [os.path.join(D_MENU, f"symbol128_{df}.tga") for df in FRAME_DONORS]
        mask = frame_mask(paths)
        canvas = os.path.join(D_MENU, f"symbol128_{donor}.tga")
        composite(canvas, mask, fac, "base",
                  os.path.join(DATA, "loading_screen", "symbols", f"symbol128_{fac}.tga"))

        # --- ui/faction_symbols (54x54): donor alpha, heraldry fills shape ---
        donor_fs = tga.read(os.path.join(D_UI, f"{donor}.tga"))
        h, w = len(donor_fs), len(donor_fs[0])
        design = draw_design(fac, w, h)
        out = []
        for y in range(h):
            row = []
            for x in range(w):
                a = donor_fs[y][x][3]
                near_edge = a > 0 and any(
                    not (0 <= y + dy < h and 0 <= x + dx < w) or donor_fs[y + dy][x + dx][3] == 0
                    for dy in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2))
                if a == 0:
                    row.append((0, 0, 0, 0))
                elif near_edge:
                    r, g, b = design[y][x]
                    row.append((r * 11 // 20, g * 11 // 20, b * 11 // 20, a))
                else:
                    r, g, b = design[y][x]
                    row.append((r, g, b, a))
            out.append(row)
        fs_path = os.path.join(DATA, "ui", "faction_symbols", f"{fac}.tga")
        os.makedirs(os.path.dirname(fs_path), exist_ok=True)
        tga.write(fs_path, out, origin_topdown=True)

        # --- battle banner .texture + strat symbol .cas/dds (as before) ---
        tex_dir = os.path.join(DATA, "banners", "textures")
        os.makedirs(tex_dir, exist_ok=True)
        wrapper = open(os.path.join(tex_dir, "faction_banner_wales.texture"), "rb").read(48)
        design = draw_design(fac, BANNER_W, BANNER_H)
        open(os.path.join(tex_dir, f"faction_banner_{fac}.texture"), "wb").write(
            wrapper + dds_bytes(design))
        royal = [row[:] for row in design]
        border(royal, 0.04, GOLD)
        open(os.path.join(tex_dir, f"royal_banner_{fac}.texture"), "wb").write(
            wrapper + dds_bytes(royal))
        shutil.copyfile(os.path.join(tex_dir, "faction_banner_wales_trans.texture"),
                        os.path.join(tex_dir, f"faction_banner_{fac}_trans.texture"))

        cas_donor = CAS_DONOR[fac]
        cas = open(os.path.join(BASE_MS, f"symbol_{cas_donor}.cas"), "rb").read()
        old = f"#banner_symbol_{cas_donor}.tga".encode()
        new = f"#banner_symbol_{fac}.tga".encode()
        assert len(old) == len(new) and old in cas
        ms_dir = os.path.join(DATA, "models_strat")
        os.makedirs(os.path.join(ms_dir, "textures"), exist_ok=True)
        open(os.path.join(ms_dir, f"symbol_{fac}.cas"), "wb").write(cas.replace(old, new))
        open(os.path.join(ms_dir, "textures", f"#banner_symbol_{fac}.tga.dds"), "wb").write(
            dds_bytes(draw_design(fac, 128, 128)))

    # DLC factions: genuine loading-screen emblems to the CORRECT path
    DLC_LOAD = {
        "wales": "british_isles", "ireland": "british_isles",
        "norway": "british_isles", "jerusalem": "crusades",
    }
    for fac, dlc in DLC_LOAD.items():
        dst = os.path.join(DATA, "loading_screen", "symbols", f"symbol128_{fac}.tga")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        src = os.path.join(ROOT, "research", "dlc-extract", dlc, "mods", dlc,
                           "data", "loading_screen", "symbols", f"symbol128_{fac}.tga")
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            continue
        # british_isles ships no symbol128 art — scale its genuine 90x90
        # fe_symbols_80 emblem up to 128 (nearest neighbour, alpha kept)
        emblem = tga.read(os.path.join(ROOT, "research", "dlc-extract", dlc, "mods",
                                       dlc, "data", "menu", "symbols",
                                       "fe_symbols_80", f"{fac}.tga"))
        sh, sw = len(emblem), len(emblem[0])
        scaled = [[emblem[y * sh // 128][x * sw // 128] for x in range(128)]
                  for y in range(128)]
        tga.write(dst, scaled, origin_topdown=False)

    # retire the invented paths from earlier rounds (wrong locations)
    for stale in ("ui/symbols", "ui/rebel_symbols", "ui/loading_screen"):
        p = os.path.join(DATA, *stale.split("/"))
        if os.path.isdir(p):
            shutil.rmtree(p)

    print(f"heraldry composited onto CA canvases for {list(CANVAS_DONOR)}; "
          f"loading emblems at data/loading_screen/symbols; stale ui dirs removed")


if __name__ == "__main__":
    main()
