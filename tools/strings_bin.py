#!/usr/bin/env python3
"""M2TW .strings.bin <-> .txt converter.

Binary format (verified against vanilla localized.pack expanded.txt.strings.bin):
  u32 magic   0x08000002
  u32 count   number of key/value pairs
  per entry:
    u16 klen, klen UTF-16LE chars (key)
    u16 vlen, vlen UTF-16LE chars (value)

Text format is the standard M2TW data/text one: {KEY}value lines.

Usage:
  python3 tools/strings_bin.py decode <in.strings.bin> <out.txt>
  python3 tools/strings_bin.py encode <in.txt> <out.strings.bin>
  python3 tools/strings_bin.py merge  <base.strings.bin> <extra.txt> <out.strings.bin>
      (extra.txt keys override/append to base)
"""
import struct
import sys

MAGIC = 0x08000002


def read_bin(path):
    data = open(path, "rb").read()
    magic, count = struct.unpack_from("<II", data, 0)
    assert magic == MAGIC, f"bad magic {magic:#x} in {path}"
    off = 8
    entries = []
    for _ in range(count):
        (klen,) = struct.unpack_from("<H", data, off)
        off += 2
        key = data[off:off + klen * 2].decode("utf-16-le")
        off += klen * 2
        (vlen,) = struct.unpack_from("<H", data, off)
        off += 2
        val = data[off:off + vlen * 2].decode("utf-16-le")
        off += vlen * 2
        entries.append((key, val))
    tail = data[off:]
    assert tail in (b"", b"\x00\x00\x00\x00"), \
        f"unexpected trailing bytes at {off} of {len(data)}: {tail[:16]!r}"
    return entries


def write_bin(path, entries):
    out = bytearray(struct.pack("<II", MAGIC, len(entries)))
    for key, val in entries:
        k = key.encode("utf-16-le")
        v = val.encode("utf-16-le")
        out += struct.pack("<H", len(key)) + k
        out += struct.pack("<H", len(val)) + v
    out += b"\x00\x00\x00\x00"  # empty-entry terminator, present in retail bins
    open(path, "wb").write(bytes(out))


def read_names_bin(path):
    """names.txt.strings.bin variant: standard table + a second section
    (u32 count, then [u16 len][utf-16 chars] internal name tokens)."""
    data = open(path, "rb").read()
    magic, count = struct.unpack_from("<II", data, 0)
    assert magic == MAGIC, f"bad magic {magic:#x} in {path}"
    off = 8
    entries = []
    for _ in range(count):
        (klen,) = struct.unpack_from("<H", data, off)
        off += 2
        key = data[off:off + klen * 2].decode("utf-16-le")
        off += klen * 2
        (vlen,) = struct.unpack_from("<H", data, off)
        off += 2
        val = data[off:off + vlen * 2].decode("utf-16-le")
        off += vlen * 2
        entries.append((key, val))
    (tcount,) = struct.unpack_from("<I", data, off)
    off += 4
    tokens = []
    for _ in range(tcount):
        (tlen,) = struct.unpack_from("<H", data, off)
        off += 2
        tokens.append(data[off:off + tlen * 2].decode("utf-16-le"))
        off += tlen * 2
    assert off == len(data), f"trailing bytes at {off} of {len(data)}"
    return entries, tokens


def write_names_bin(path, entries, tokens):
    out = bytearray(struct.pack("<II", MAGIC, len(entries)))
    for key, val in entries:
        out += struct.pack("<H", len(key)) + key.encode("utf-16-le")
        out += struct.pack("<H", len(val)) + val.encode("utf-16-le")
    out += struct.pack("<I", len(tokens))
    for t in tokens:
        out += struct.pack("<H", len(t)) + t.encode("utf-16-le")
    open(path, "wb").write(bytes(out))


def read_txt(path):
    """Parse {KEY}value text (any encoding: try utf-16, then utf-8/latin-1)."""
    raw = open(path, "rb").read()
    for enc in ("utf-16", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    entries = []
    for line in text.splitlines():
        line = line.strip("﻿").rstrip("\r\n")
        if not line.startswith("{"):
            continue
        end = line.find("}")
        if end < 0:
            continue
        entries.append((line[1:end], line[end + 1:]))
    return entries


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "decode":
        entries = read_bin(sys.argv[2])
        with open(sys.argv[3], "w", encoding="utf-8", newline="\n") as f:
            for k, v in entries:
                f.write("{%s}%s\n" % (k, v))
        print(f"decoded {len(entries)} entries -> {sys.argv[3]}")
    elif cmd == "encode":
        entries = read_txt(sys.argv[2])
        write_bin(sys.argv[3], entries)
        print(f"encoded {len(entries)} entries -> {sys.argv[3]}")
    elif cmd == "merge":
        base = read_bin(sys.argv[2])
        extra = read_txt(sys.argv[3])
        merged = dict(base)
        added = replaced = 0
        for k, v in extra:
            if k in merged:
                replaced += 1
            else:
                added += 1
            merged[k] = v
        # keep base order, append new keys at the end in extra order
        base_keys = [k for k, _ in base]
        extra_new = [k for k, _ in extra if k not in set(base_keys)]
        seen = set()
        ordered = []
        for k in base_keys + extra_new:
            if k in seen:
                continue
            seen.add(k)
            ordered.append((k, merged[k]))
        write_bin(sys.argv[4], ordered)
        print(f"merged: {len(base)} base + {added} new, {replaced} overridden -> {sys.argv[4]}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
