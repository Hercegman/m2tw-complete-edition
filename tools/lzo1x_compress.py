"""Minimal VALID LZO1X compressor (all-literals, no matches) in 64KB blocks.
Produces a stream that tools/lzo1x.py decompresses back to the input.
comp size ~= unc + small overhead (no actual compression). Used to re-store
edited text files into the pack in the exact LZO1X framing the game expects.
"""

BLOCK = 65536

def _emit_block(src):
    """Encode one block (<=65536 bytes) as a single literal run + end marker."""
    out = bytearray()
    L = len(src)
    # literal-run token: decoder at 'top' reads t; if t<16 -> run of (t==0?ext:t)+3.
    t = L - 3
    if t < 0:
        # tiny block: pad logic not needed for our files; emit raw-ish
        # (L in 0..2) — use initial-literal-run path: first byte >17 => copy (b-17)
        out.append(17 + L)
        out += src
        out += b"\x11\x00\x00"
        return out
    if 1 <= t <= 15:
        out.append(t)               # inline literal length
    else:
        out.append(0x00)            # extended
        rem = t - 15                # decoder: t starts 0, +255 per zero byte, +15+final
        while rem > 255:
            out.append(0x00); rem -= 255
        # final byte must be the one that stops the zero-run (can be 0..255 but if
        # rem==0 and we already emitted zeros, the next byte is rem -> 0 is fine ONLY
        # as the terminating read). decoder: while ==0 add 255; then t+=15+next.
        out.append(rem)             # terminating byte (15+rem already accounted)
    out += src
    out += b"\x11\x00\x00"          # end-of-stream marker
    return out

def compress(data):
    """All-literal fallback (comp > unc). Kept for reference/round-trip tests."""
    out = bytearray()
    for i in range(0, len(data), BLOCK):
        out += _emit_block(data[i:i+BLOCK])
    return bytes(out)


# ---------------------------------------------------------------------------
# Real LZO1X compressor (produces comp < unc). Inverts tools/lzo1x.py.
# Stream shape we emit: [lit-run][match][lit-run][match]...[lit-run][11 00 00]
#   - first token must be a literal run (init treats first byte>17 as a run)
#   - literal runs are >=3 bytes (token t<16 -> count t+3, or t=0 extended)
#   - matches use the t>=32 encoding, 0 trailing literals, dist 1..16384, len>=4
#   - gaps between matches are 0 or >=3 literals (never 1-2)
# ---------------------------------------------------------------------------
MIN_MATCH = 4
MAX_DIST  = 16384            # actual back-distance; encoded value D = dist-1 (<=16383)
MAX_LEN_INLINE = 33

def _emit_lit_run(out, data, s, e):
    L = e - s
    t = L - 3
    if t < 0:
        raise ValueError("literal run < 3")
    if t <= 15:
        out.append(t)
    else:
        out.append(0x00)
        rem = t - 15
        while rem > 255:
            out.append(0x00); rem -= 255
        out.append(rem)
    out += data[s:e]

def _emit_match_hdr(out, length):
    if length <= MAX_LEN_INLINE:
        out.append(0x20 | (length - 2))
    else:
        out.append(0x20)               # t&31 == 0 -> extended length
        rem = length - 33
        while rem > 255:
            out.append(0x00); rem -= 255
        out.append(rem)

def compress_real(data):
    """LZO1X in 64KB blocks (matches the game's framing for files >64KB)."""
    out = bytearray()
    for i in range(0, len(data), BLOCK):
        out += _compress_block(data[i:i+BLOCK])
    if not out:                      # empty input -> single end marker
        out += b"\x11\x00\x00"
    return bytes(out)


def _compress_block(data):
    """Greedy LZO1X for ONE block (<=64KB). Literal runs of 1-3 are encoded as
    trailing literals on the PREVIOUS match (its distance low byte's low 2 bits);
    4+ via a literal-run token; the very first run via the init byte (17+count)."""
    n = len(data)
    out = bytearray()
    ht = {}
    ii = 0                              # start of current pending literal run
    i = 0
    last_lo = -1                        # index in `out` of prev match's low dist byte

    def emit_lits(s, e):
        nonlocal last_lo
        L = e - s
        if L == 0:
            return
        if last_lo >= 0 and L <= 3:
            out[last_lo] |= L           # trailing literals on previous match
        elif last_lo < 0:               # very first run: init path
            assert 1 <= L <= 238, L
            out.append(17 + L)
        else:                           # standalone literal run (L >= 4)
            if L <= 18:
                out.append(L - 3)
            else:
                out.append(0x00)
                rem = L - 18
                while rem > 255:
                    out.append(0x00); rem -= 255
                out.append(rem)
        out.extend(data[s:e])

    while i < n:
        m_pos, mlen = -1, 0
        if i + MIN_MATCH <= n:
            cand = ht.get(bytes(data[i:i+3]), -1)
            if cand >= 0 and 0 < i - cand <= MAX_DIST:
                maxlen = n - i
                ml = 0
                while ml < maxlen and data[cand+ml] == data[i+ml]:
                    ml += 1
                if ml >= MIN_MATCH:
                    m_pos, mlen = cand, ml
        # never start the stream with a match (need >=1 initial literal); never
        # let a match run to the very end without leaving 0 trailing room
        if m_pos >= 0 and i >= 1:
            emit_lits(ii, i)            # flush literals before this match
            _emit_match_hdr(out, mlen)
            D = (i - m_pos) - 1
            out.append((D & 0x3F) << 2)   # low distance byte (trailing bits go here)
            last_lo = len(out) - 1
            out.append(D >> 6)            # high distance byte
            for j in range(i, min(i + mlen, n - 2)):
                ht[bytes(data[j:j+3])] = j
            i += mlen
            ii = i
        else:
            if i + 3 <= n:
                ht[bytes(data[i:i+3])] = i
            i += 1
    emit_lits(ii, n)                    # final literals (trailing on last match if <=3)
    out += b"\x11\x00\x00"
    return bytes(out)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    import lzo1x
    src = open("research/descr_sm_factions_decompressed.txt", "rb").read()
    comp = compress_real(src)
    back = lzo1x.decompress_blocks(comp, len(src))
    print(f"src={len(src)} comp={len(comp)} (ratio {len(comp)/len(src):.3f})  comp<unc={len(comp)<len(src)}")
    print("round-trip OK:", bytes(back) == src)
    if bytes(back) != src:
        for i,(a,b) in enumerate(zip(back,src)):
            if a!=b: print("first diff @",i,hex(a),hex(b)); break
        print("len back",len(back),"len src",len(src))
