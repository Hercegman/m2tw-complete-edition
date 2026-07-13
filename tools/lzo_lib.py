"""Canonical LZO1X via the system liblzo2 (ctypes). The game uses LZO; this is
the real library, so its output is guaranteed game-compatible. Compresses in
64KB blocks to match the pack's framing for files >64KB.
"""
import ctypes

_lzo = ctypes.CDLL("liblzo2.so.2")
_lzo.lzo1x_1_compress.restype = ctypes.c_int
_lzo.lzo1x_decompress.restype = ctypes.c_int
LZO1X_1_MEM_COMPRESS = 16384 * 8     # 64-bit: lzo_sizeof_dict_t = sizeof(ptr) = 8
BLOCK = 65536

# best-effort lzo_init (ABI check); ignore if signature differs
try:
    _lzo.__lzo_init_v2(ctypes.c_uint(0x2070), 2, 4, 8, 4, 8, 8, 8, 8, 8)
except Exception:
    pass

def compress_block(data):
    n = len(data)
    src = (ctypes.c_ubyte * n).from_buffer_copy(data)
    cap = n + n // 16 + 64 + 3
    dst = (ctypes.c_ubyte * cap)()
    dlen = ctypes.c_ulong(cap)
    wrk = (ctypes.c_ubyte * LZO1X_1_MEM_COMPRESS)()
    r = _lzo.lzo1x_1_compress(src, ctypes.c_ulong(n), dst, ctypes.byref(dlen), wrk)
    if r != 0:
        raise RuntimeError("lzo1x_1_compress rc=%d" % r)
    return bytes(dst[:dlen.value])

def compress(data):
    out = bytearray()
    for i in range(0, len(data), BLOCK):
        out += compress_block(data[i:i+BLOCK])
    if not out:
        out += b"\x11\x00\x00"
    return bytes(out)

def decompress_block(comp, unc_size):
    src = (ctypes.c_ubyte * len(comp)).from_buffer_copy(comp)
    dst = (ctypes.c_ubyte * unc_size)()
    dlen = ctypes.c_ulong(unc_size)
    r = _lzo.lzo1x_decompress(src, ctypes.c_ulong(len(comp)), dst, ctypes.byref(dlen), None)
    return bytes(dst[:dlen.value]), r


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    import lzo1x
    # 1) real lib decompresses the GAME's original sm_factions blob correctly?
    _W = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Medieval II Total War/packs/data_0.pack.bak"
    import struct
    data = open(_W, "rb").read()
    blob = data[955322878:955322878+2873]
    out, rc = decompress_block(blob, 18401)
    print("real-lib decompress original sm_factions: rc=%d len=%d head=%r" % (rc, len(out), out[:30]))
    # 2) round-trip our edited files through the real lib + our decoder
    for f in ["research/descr_sm_factions_final.txt", "research/export_descr_unit_edited.txt"]:
        s = open(f, "rb").read()
        c = compress(s)
        b = lzo1x.decompress_blocks(c, len(s))
        print("%s: unc=%d comp=%d ratio=%.3f mydecode_ok=%s" % (
            f.split("/")[-1], len(s), len(c), len(c)/len(s), bytes(b) == s))
