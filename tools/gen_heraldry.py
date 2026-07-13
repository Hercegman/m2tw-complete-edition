#!/usr/bin/env python3
"""Generate real, unique heraldry for the factions that have no Kingdoms art.

Pure-Python pixel drawing -> TGA (ui/menu icons) and DDS (.texture banners,
strat-map symbol textures). Designs:
  croatia   - red/white chequy (sahovnica)
  serbia    - white cross on red with four firesteels (approximated)
  bulgaria  - gold saltire on dark red (Asen dynasty colours)
  ragusa    - white field, blue fess, red border (Libertas colours)
  wallachia - gold pale on azure with white sun disc

Outputs overwrite the wales-placeholder art. DLC factions (wales, ireland,
norway, jerusalem) keep their genuine Kingdoms assets and are not touched.
"""
import os
import struct
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
BASE_MS = os.path.join(ROOT, "research", "base-extract", "data", "models_strat")

GOLD = (212, 175, 55)
WHITE = (240, 240, 240)


# ---------------- pixel buffer helpers ----------------

def buf(w, h, color):
    return [[color] * w for _ in range(h)]


def rect(b, x0, y0, x1, y1, color):
    h = len(b)
    w = len(b[0])
    for y in range(max(0, int(y0)), min(h, int(y1))):
        for x in range(max(0, int(x0)), min(w, int(x1))):
            b[y][x] = color


def frect(b, fx0, fy0, fx1, fy1, color):
    h = len(b)
    w = len(b[0])
    rect(b, fx0 * w, fy0 * h, fx1 * w, fy1 * h, color)


def border(b, frac, color):
    h = len(b)
    w = len(b[0])
    t = max(1, int(min(w, h) * frac))
    rect(b, 0, 0, w, t, color)
    rect(b, 0, h - t, w, h, color)
    rect(b, 0, 0, t, h, color)
    rect(b, w - t, 0, w, h, color)


def checker(b, n, c1, c2):
    h = len(b)
    w = len(b[0])
    for y in range(h):
        for x in range(w):
            b[y][x] = c1 if ((x * n // w) + (y * n // h)) % 2 == 0 else c2


def saltire(b, frac, color):
    h = len(b)
    w = len(b[0])
    t = min(w, h) * frac
    for y in range(h):
        for x in range(w):
            fx, fy = x / w, y / h
            if abs(fx - fy) * min(w, h) < t or abs(fx + fy - 1) * min(w, h) < t:
                b[y][x] = color


def circle(b, fcx, fcy, frad, color):
    h = len(b)
    w = len(b[0])
    cx, cy, r = fcx * w, fcy * h, frad * min(w, h)
    for y in range(h):
        for x in range(w):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                b[y][x] = color


def transform(b, fn):
    return [[fn(px) for px in row] for row in b]


def greyscale(b):
    return transform(b, lambda p: ((p[0] * 3 + p[1] * 6 + p[2]) // 10,) * 3)


def brighten(b, d):
    return transform(b, lambda p: tuple(min(255, c + d) for c in p))


def desaturate(b):
    def f(p):
        g = (p[0] + p[1] + p[2]) // 3
        return ((p[0] + g) // 2, (p[1] + g) // 2, (p[2] + g) // 2)
    return transform(b, f)


# ---------------- designs ----------------

def draw_design(fac, w, h):
    b = buf(w, h, WHITE)
    if fac == "croatia":
        checker(b, 5, (200, 25, 35), WHITE)
    elif fac == "serbia":
        b = buf(w, h, (175, 20, 30))
        frect(b, 0.42, 0.0, 0.58, 1.0, WHITE)   # vertical arm
        frect(b, 0.0, 0.42, 1.0, 0.58, WHITE)   # horizontal arm
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


# ---------------- writers ----------------

def write_tga(path, b):
    h = len(b)
    w = len(b[0])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 24, 0x20)
    body = bytearray()
    for row in b:
        for r, g, bl in row:
            body += bytes((bl, g, r))
    open(path, "wb").write(hdr + bytes(body))


def shield_alpha(w, h):
    """Heater-shield alpha mask: straight top, sides tapering to a bottom
    point — the shape all vanilla faction icons use (32-bit TGA, alpha 0
    outside). Returns per-pixel 0/255 alpha rows."""
    alpha = []
    for y in range(h):
        fy = y / (h - 1)
        if fy < 0.02 or fy > 0.97:
            hw = 0.0
        elif fy <= 0.5:
            hw = 0.46
        else:
            t = (fy - 0.5) / 0.47
            hw = 0.46 * max(0.0, 1.0 - t ** 1.7)
        row = []
        for x in range(w):
            fx = x / (w - 1)
            row.append(255 if abs(fx - 0.5) <= hw else 0)
        alpha.append(row)
    return alpha


def write_shield_tga(path, b):
    """32-bit TGA with the design clipped to a shield shape (dark outline,
    transparent outside) — matches the vanilla icon format (bpp=32, desc 0x28)."""
    h = len(b)
    w = len(b[0])
    alpha = shield_alpha(w, h)
    outline = (35, 30, 30)
    t = max(1, min(w, h) // 24)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x28)
    body = bytearray()
    for y in range(h):
        for x in range(w):
            a = alpha[y][x]
            if a == 0:
                body += b"\x00\x00\x00\x00"
                continue
            edge = False
            for dy in range(-t, t + 1):
                for dx in range(-t, t + 1):
                    yy, xx = y + dy, x + dx
                    if not (0 <= yy < h and 0 <= xx < w) or alpha[yy][xx] == 0:
                        edge = True
                        break
                if edge:
                    break
            r, g, bl = outline if edge else b[y][x]
            body += bytes((bl, g, r, 255))
    open(path, "wb").write(hdr + bytes(body))


def dds_bytes(b):
    h = len(b)
    w = len(b[0])
    hdr = struct.pack(
        "<4sIIIIIII44xIIIIIIIIIIII4x",
        b"DDS ", 124, 0x0000100F, h, w, w * 4, 0, 0,
        32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000,
        0x1000, 0, 0, 0)
    assert len(hdr) == 128, len(hdr)
    body = bytearray()
    for row in b:
        for r, g, bl in row:
            body += bytes((bl, g, r, 255))
    return hdr + bytes(body)


def write_dds(path, b):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(dds_bytes(b))


def write_texture(path, b, wrapper):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(wrapper + dds_bytes(b))


def tga_dims(path):
    d = open(path, "rb").read(18)
    return struct.unpack_from("<HH", d, 12)


# ---------------- main ----------------

# faction -> .cas donor whose texture-path string has the SAME LENGTH
CAS_DONOR = {
    "croatia": "hungary",      # 7 = 7
    "ragusa": "venice",        # 6 = 6
    "serbia": "france",        # 6 = 6
    "bulgaria": "scotland",    # 8 = 8
    "wallachia": "byzantium",  # 9 = 9
}
# banner _trans (banner shape alpha) donor — the roster mate looks right
TRANS_DONOR = {
    "croatia": "hungary", "ragusa": "venice", "serbia": "byzantium",
    "bulgaria": "byzantium", "wallachia": "hungary",
}

BANNER_W, BANNER_H = 1024, 512


def main():
    wales_banner = os.path.join(DATA, "banners", "textures", "faction_banner_wales.texture")
    wrapper = open(wales_banner, "rb").read(48)

    menu = os.path.join(DATA, "menu", "symbols")
    dims24 = tga_dims(os.path.join(menu, "fe_buttons_24", "symbol24_wales.tga"))
    dims48 = tga_dims(os.path.join(menu, "fe_buttons_48", "symbol48_wales.tga"))
    dims80 = tga_dims(os.path.join(menu, "fe_symbols_80", "wales.tga"))
    dimsfu = tga_dims(os.path.join(menu, "fe_faction_units", "wales.tga"))

    for fac in CAS_DONOR:
        # --- ui icons (shield-shaped, 32-bit alpha like vanilla) ---
        write_shield_tga(os.path.join(DATA, "ui", "symbols", f"symbol_{fac}.tga"),
                         draw_design(fac, 32, 32))
        write_shield_tga(os.path.join(DATA, "ui", "rebel_symbols", f"rebel_{fac}.tga"),
                         desaturate(draw_design(fac, 32, 32)))
        write_shield_tga(os.path.join(DATA, "ui", "faction_symbols", f"{fac}.tga"),
                         draw_design(fac, 54, 54))
        write_shield_tga(os.path.join(DATA, "ui", "loading_screen", "symbols", f"symbol128_{fac}.tga"),
                         draw_design(fac, 128, 128))

        # --- menu selector art (shield-shaped buttons) ---
        write_shield_tga(os.path.join(menu, "fe_symbols_80", f"{fac}.tga"),
                         draw_design(fac, *dims80))
        write_tga(os.path.join(menu, "fe_faction_units", f"{fac}.tga"),
                  draw_design(fac, *dimsfu))
        for size, dname, prefix in ((dims48, "fe_buttons_48", "symbol48"),
                                    (dims24, "fe_buttons_24", "symbol24")):
            base = draw_design(fac, *size)
            sel = [row[:] for row in base]
            border(sel, 0.07, GOLD)
            for suffix, img in (("", base), ("_roll", brighten(base, 35)),
                                ("_select", sel), ("_grey", greyscale(base))):
                write_shield_tga(os.path.join(menu, dname, f"{prefix}_{fac}{suffix}.tga"), img)

        # --- battle banner textures (.texture wrapper + DDS) ---
        tex_dir = os.path.join(DATA, "banners", "textures")
        design = draw_design(fac, BANNER_W, BANNER_H)
        write_texture(os.path.join(tex_dir, f"faction_banner_{fac}.texture"), design, wrapper)
        royal = [row[:] for row in design]
        border(royal, 0.04, GOLD)
        write_texture(os.path.join(tex_dir, f"royal_banner_{fac}.texture"), royal, wrapper)
        # vanilla banner textures live in packs; reuse the DLC wales _trans
        # shape which we already ship (same mesh family)
        shutil.copyfile(os.path.join(tex_dir, "faction_banner_wales_trans.texture"),
                        os.path.join(tex_dir, f"faction_banner_{fac}_trans.texture"))

        # --- strat-map symbol: donor .cas with patched texture path + our dds ---
        donor = CAS_DONOR[fac]
        cas = open(os.path.join(BASE_MS, f"symbol_{donor}.cas"), "rb").read()
        old = f"#banner_symbol_{donor}.tga".encode()
        new = f"#banner_symbol_{fac}.tga".encode()
        assert len(old) == len(new), (fac, donor)
        assert old in cas, f"{old} not found in donor cas"
        cas = cas.replace(old, new)
        ms_dir = os.path.join(DATA, "models_strat")
        os.makedirs(ms_dir, exist_ok=True)
        open(os.path.join(ms_dir, f"symbol_{fac}.cas"), "wb").write(cas)
        write_dds(os.path.join(ms_dir, "textures", f"#banner_symbol_{fac}.tga.dds"),
                  draw_design(fac, 128, 128))

    print(f"heraldry generated for {list(CAS_DONOR)}")


if __name__ == "__main__":
    main()
