"""General data_0.pack repacker: replace any set of files (by name) with new text,
LZO-recompress, and rebuild the pack with correct data offsets in every trailer.

Manifest trailer (16B, immediately BEFORE each name): [data_offset][id][unc][comp].
Files are concatenated in data-offset order from data_start. We do a clean full
rebuild: keep header/binary/manifest prefix, rewrite trailers, append new data.

Usage: python3 tools/repack_multi.py name1=path1 name2=path2 ...
  (name like 'data/descr_sm_factions.txt'; use '@null' as path to re-store the
   file unchanged, i.e. re-LZO its own current content.)
Reads data_0.pack.bak (vanilla), writes data_0.pack.
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
import lzo1x, lzo_lib

GAME = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Medieval II Total War/packs"
PACK = GAME + "/data_0.pack"
BAK  = GAME + "/data_0.pack.bak"
MAN  = 148960
DATA_START = 958984

def main():
    repl = {}
    for a in sys.argv[1:]:
        name, _, path = a.partition("=")
        repl[name] = path
    data = open(BAK, "rb").read()
    fc = struct.unpack_from("<I", data, 8)[0]

    # parse all entries
    entries = []   # (data_offset, trailer_pos, name, unc, comp)
    for i in range(fc):
        noff = struct.unpack_from("<I", data, 20 + i*4)[0]
        p = MAN + noff
        e = data.find(b"\x00", p)
        name = data[p:e].decode("latin1")
        tr = p - 16
        doff, fid, unc, comp = struct.unpack_from("<IIII", data, tr)
        entries.append([doff, tr, name, unc, comp])
    entries.sort(key=lambda x: x[0])   # data order

    out = bytearray(data[:DATA_START])  # header + binary + manifest prefix
    new_data = bytearray()
    cursor = DATA_START
    changed = 0
    for ent in entries:
        doff, tr, name, unc, comp = ent
        if name in repl:
            path = repl[name]
            if path == "@null":
                text = lzo1x.decompress_blocks(data[doff:doff+comp], unc) if comp < unc else data[doff:doff+comp]
                text = bytes(text)
            else:
                text = open(path, "rb").read()
            blob = lzo_lib.compress(text)
            new_unc, new_comp = len(text), len(blob)
            changed += 1
        else:
            blob = data[doff:doff+comp]
            new_unc, new_comp = unc, comp
        # write updated trailer (offset + sizes) into the prefix
        struct.pack_into("<I", out, tr,      cursor)
        struct.pack_into("<I", out, tr + 8,  new_unc)
        struct.pack_into("<I", out, tr + 12, new_comp)
        new_data += blob
        cursor += new_comp
    out += new_data
    print(f"replaced {changed} files; pack {len(data)} -> {len(out)}")
    open(PACK, "wb").write(out)

    # verify a couple of replaced files round-trip from the new pack
    chk = open(PACK, "rb").read()
    for i in range(fc):
        noff = struct.unpack_from("<I", chk, 20 + i*4)[0]
        p = MAN + noff; e = chk.find(b"\x00", p); name = chk[p:e].decode("latin1")
        if name in repl:
            doff, fid, unc, comp = struct.unpack_from("<IIII", chk, p-16)
            t = lzo1x.decompress_blocks(chk[doff:doff+comp], unc) if comp < unc else chk[doff:doff+comp]
            print(f"  {name}: off={doff} unc={unc} comp={comp} decompress_ok={len(t)==unc}")

if __name__ == "__main__":
    main()
