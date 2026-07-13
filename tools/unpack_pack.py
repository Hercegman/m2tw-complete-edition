"""Full sequential unpacker for M2TW data_N.pack files.

Proven format (data_0.pack):
  header: [0]=magic 'PACK', [8]=file_count, [12]=index_size, [16]=extra1, [20]=...
  binary section [16,148960): col0 name-offset table at offset 20 (file_count uint32)
  manifest [148960,...): per file [trailer crc,id,unc,comp (16B)][name\0 align-4]
                         -> trailer is the 16 bytes IMMEDIATELY BEFORE the name
  data section: starts at data_start = packsize - sum(comp); files concatenated in
                manifest order, each stored `comp` bytes (LZO if comp<unc else raw)

Usage: python3 tools/unpack_pack.py <pack> <out_dir> [name-substr-filter ...]
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
import lzo1x

def unpack(pack_path, out_dir, filters):
    data = open(pack_path, "rb").read()
    magic = data[0:4]
    file_count = struct.unpack_from("<I", data, 8)[0]
    index_size = struct.unpack_from("<I", data, 12)[0]
    assert magic == b"PACK", magic
    NAMES_BASE = 16 + index_size + 16   # = 148960 for data_0 (16 + 810040 + ... )
    # derive names base empirically: first name offset region. Use known 148960 if matches.
    # The name-offset table (col0) starts at offset 20.
    col0 = 20
    # find manifest base = where first name 'data/' lives
    man_base = data.find(b"data/", 16 + 4*file_count)
    # entries: name at man_base + nameoff[i]
    entries = []
    total_comp = 0
    for i in range(file_count):
        noff = struct.unpack_from("<I", data, col0 + i*4)[0]
        p = man_base + noff
        e = data.find(b"\x00", p)
        name = data[p:e].decode("latin1")
        crc, fid, unc, comp = struct.unpack_from("<IIII", data, p - 16)
        entries.append((name, unc, comp))
        total_comp += comp
    data_start = len(data) - total_comp
    print(f"{os.path.basename(pack_path)}: files={file_count} man_base={man_base} "
          f"data_start={data_start} total_comp={total_comp} (start+total={data_start+total_comp} size={len(data)})")
    assert data_start + total_comp == len(data), "sequential model mismatch!"

    cursor = data_start
    written = 0
    for name, unc, comp in entries:
        blob = data[cursor:cursor+comp]
        cursor += comp
        if filters and not any(f in name for f in filters):
            continue
        try:
            out = lzo1x.decompress_blocks(blob, unc) if comp < unc else blob
        except Exception as ex:
            print(f"  DECOMP FAIL {name}: {ex}")
            continue
        if len(out) != unc:
            print(f"  SIZE MISMATCH {name}: got {len(out)} want {unc}")
        dst = os.path.join(out_dir, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(out)
        written += 1
    print(f"  wrote {written} files to {out_dir}")

if __name__ == "__main__":
    pack = sys.argv[1]
    out = sys.argv[2]
    filt = sys.argv[3:]
    unpack(pack, out, filt)
