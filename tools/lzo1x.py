"""Pure-Python LZO1X decompressor — faithful port of minilzo lzo1x_decompress.
M2TW .pack data blobs are LZO-compressed. No external deps.

decompress(src) -> bytearray.  Control flow mirrors the C labels exactly
(top / first_literal_run / match / copy_match / match_done / match_next).
"""

def decompress(src, return_consumed=False):
    src = bytes(src)
    n = len(src)
    out = bytearray()
    ip = 0

    def lit(t):
        nonlocal ip
        out.extend(src[ip:ip + t]); ip += t

    t = 0
    label = "init"

    while True:
        if label == "init":
            if src[ip] > 17:
                t = src[ip] - 17; ip += 1
                if t < 4:
                    label = "match_next"; continue
                lit(t)
                label = "first_literal_run"; continue
            label = "top"; continue

        if label == "top":
            t = src[ip]; ip += 1
            if t >= 16:
                label = "match"; continue
            # literal run
            if t == 0:
                while src[ip] == 0:
                    t += 255; ip += 1
                t += 15 + src[ip]; ip += 1
            lit(t + 3)
            label = "first_literal_run"; continue

        if label == "first_literal_run":
            t = src[ip]; ip += 1
            if t >= 16:
                label = "match"; continue
            m = len(out) - (1 + 0x0800) - (t >> 2) - (src[ip] << 2); ip += 1
            out.append(out[m]); out.append(out[m + 1]); out.append(out[m + 2])
            label = "match_done"; continue

        if label == "match":
            if t >= 64:
                m = len(out) - 1 - ((t >> 2) & 7) - (src[ip] << 3); ip += 1
                t = (t >> 5) - 1
            elif t >= 32:
                t &= 31
                if t == 0:
                    while src[ip] == 0:
                        t += 255; ip += 1
                    t += 31 + src[ip]; ip += 1
                m = len(out) - 1 - ((src[ip] >> 2) + (src[ip + 1] << 6)); ip += 2
            elif t >= 16:
                m = len(out) - ((t & 8) << 11)
                t &= 7
                if t == 0:
                    while src[ip] == 0:
                        t += 255; ip += 1
                    t += 7 + src[ip]; ip += 1
                m -= (src[ip] >> 2) + (src[ip + 1] << 6); ip += 2
                if m == len(out):
                    return (out, ip) if return_consumed else out  # end of stream
                m -= 0x4000
            else:
                m = len(out) - 1 - (t >> 2) - (src[ip] << 2); ip += 1
                out.append(out[m]); out.append(out[m + 1])
                label = "match_done"; continue
            # copy_match: copy t+2 bytes from m
            for _ in range(t + 2):
                out.append(out[m]); m += 1
            label = "match_done"; continue

        if label == "match_done":
            t = src[ip - 2] & 3
            if t == 0:
                label = "top"; continue
            label = "match_next"; continue

        if label == "match_next":
            lit(t)
            t = src[ip]; ip += 1
            label = "match"; continue

    return (out, ip) if return_consumed else out


def decompress_blocks(src, total_unc):
    """M2TW stores files >64KB as concatenated 64KB LZO blocks (no inter-block
    header). Decompress block by block until total_unc bytes are produced."""
    out = bytearray()
    pos = 0
    n = len(src)
    while len(out) < total_unc and pos < n:
        block, consumed = decompress(src[pos:], return_consumed=True)
        if not block or consumed <= 0:
            break
        out += block
        pos += consumed
    return out


if __name__ == "__main__":
    blob = open("research/sm_factions_compiled.bin", "rb").read()
    try:
        d = decompress(blob)
        pr = sum(1 for c in d if 9 <= c <= 13 or 32 <= c <= 126) / max(1, len(d))
        facs = sum(1 for f in (b"england", b"france", b"spain", b"hungary",
                               b"poland", b"sicily", b"venice", b"byzantium")
                   if f in d)
        print(f"decompressed {len(blob)} -> {len(d)} bytes, printable={pr:.2f}, factions_found={facs}/8")
        print("---- head ----")
        print(d[:700].decode("latin1"))
    except Exception as e:
        import traceback; traceback.print_exc()
        print("FAIL:", e, "ip-ish out_len=", len(out) if 'out' in dir() else '?')
