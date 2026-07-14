#!/usr/bin/env python3
"""Minimal TGA I/O for M2TW assets.

Reads type-2 (uncompressed) and type-10 (RLE) 24/32-bit TGAs with either
origin, returning a top-down matrix of (r, g, b, a) tuples. Writes type-2
32-bit with a chosen origin so outputs can match their donors byte-layout.
"""
import struct


def read(path):
    d = open(path, "rb").read()
    idlen, cmap, itype = d[0], d[1], d[2]
    w, h = struct.unpack_from("<HH", d, 12)
    bpp, desc = d[16], d[17]
    assert itype in (2, 10), f"{path}: unsupported TGA type {itype}"
    assert bpp in (24, 32), f"{path}: unsupported bpp {bpp}"
    nb = bpp // 8
    off = 18 + idlen + (d[3] and 0)
    px = []

    def emit(chunk):
        b, g, r = chunk[0], chunk[1], chunk[2]
        a = chunk[3] if nb == 4 else 255
        px.append((r, g, b, a))

    if itype == 2:
        for i in range(w * h):
            emit(d[off + i * nb: off + i * nb + nb])
    else:
        need = w * h
        while len(px) < need:
            hdr = d[off]
            off += 1
            count = (hdr & 0x7F) + 1
            if hdr & 0x80:
                chunk = d[off:off + nb]
                off += nb
                for _ in range(count):
                    emit(chunk)
            else:
                for _ in range(count):
                    emit(d[off:off + nb])
                    off += nb

    rows = [px[y * w:(y + 1) * w] for y in range(h)]
    if not (desc & 0x20):        # bottom-left origin -> flip to top-down
        rows.reverse()
    return rows                   # rows[0] = visual top row


def write(path, rows, origin_topdown=True):
    h = len(rows)
    w = len(rows[0])
    desc = 0x28 if origin_topdown else 0x08
    out_rows = rows if origin_topdown else list(reversed(rows))
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, desc)
    body = bytearray()
    for row in out_rows:
        for r, g, b, a in row:
            body += bytes((b, g, r, a))
    open(path, "wb").write(hdr + bytes(body))
