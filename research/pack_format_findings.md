# data_0.pack format — findings (2026-06-20)

Reverse-engineering of `packs/data_0.pack` (1,013,426,292 B) to patch
`descr_sm_factions` (the one file the game refuses to load as a loose override).

## Overall layout (confirmed)

| Region | Bytes | Contents |
|---|---|---|
| Header | `[0, 16)` | `magic="PACK"`, `type=0x00030000`, `file_count=7293`, `index_size=810040` |
| Header extra | `[16, 24)` | `extra1=29938`, `extra2=0` |
| **Binary section** | `[16/20, 148960)` | columnar uint32 table, ~20.4 B/entry. **col0 = name-offset of each entry into the filename manifest** (verified: col0[sm_factions]=783516 = 932476−148960 ✓). Other columns are NOT clean data-offset columns. |
| **Filename manifest** | `[148960, 958940)` | 7293 contiguous entries. **Entry = `name` + `\0` + pad-to-4-byte-align + `crc32(4)` + `id(4)` + `unc(4)` + `comp(4)`** (all uint32 LE). |
| **Data section** | `[958940, EOF)` | stored/compressed blobs, concatenated in **manifest order**, each sized `comp`. |

## descr_sm_factions manifest entry (byte 932476)

```
name = "data/descr_sm_factions.txt"
crc  = 0x38F11D37   (@932504)
id   = 27913        (@932508)
unc  = 3886         (@932512)
comp = 976          (@932516)
```
manifest index = **6901** of 7293.

## Data offset — SOLVED (exact, verified by content)

`descr_sm_factions` is stored **UNCOMPRESSED** in `data_0.pack` at:

```
[955,322,841 , 955,326,727)   length = 3886 bytes  (== manifest `unc`)
```

Verified: the blob starts with the compiled faction binary (`;; faction descrip…`,
`logo_index`), contains `england\r\nculture…northern_european` at +233, and **ends
exactly where `descr_solar_system.txt` begins** (the `;;;; solar system bodies…` banner
at 955,326,727). Tool: `find_text_anchors.py` + `probe_size_offset.py`.

### Consequences (these change everything for Option A)

1. **No compression codec to crack.** The on-disk form is the full 3886-byte compiled
   binary. The manifest's `comp=976` is NOT the data_0 storage size — ignore it for
   editing. We edit the 3886-byte binary directly.
2. **The 7293-entry manifest spans ALL FIVE packs** (data_0..data_4), not just data_0.
   Proof: cumulative `Σ unc` over the manifest reaches ~1.46e9 — larger than data_0
   itself (1.01e9). So only a subset of manifest files actually live in data_0.
3. **No offset table exists.** Searched the whole 1 GB pack for the data offset as a
   uint32 (absolute + every plausible relative base) → **0 hits**. The game locates file
   data by **sequential accumulation** of per-file sizes within a pack (each manifest
   file carries a pack-id + size; offset = Σ sizes of preceding same-pack files).

### What a patch must do (and must NOT)

- **Insert** the new bytes into `data_0.pack` at the sm_factions blob (grows it by N).
- **Update the size** the game reads for sm_factions: manifest `unc` at byte 932512
  (currently 3886 → 3886+N). Confirm whether a second size copy exists in the binary
  section before relying on this (scan for `3886` in binsec returned 0 hits, so the
  size may live ONLY in the manifest `unc` — to be confirmed).
- Because offsets are computed sequentially, **subsequent same-pack files shift
  automatically** — no offset table to rewrite. 
- **Backup `data_0.pack` first** (1 GB) before any write.

## ✅ CODEC SOLVED — it is LZO1X (pure-Python decoder works)

The pack uses **LZO** (community-confirmed; the TWC "PACK tool" uses LZO, storing files
≤1024 B uncompressed). A faithful pure-Python **LZO1X decompressor** (`tools/lzo1x.py`)
now decodes the data correctly.

**descr_sm_factions — exact, verified:**
- compressed LZO blob: **[955,322,878 , 955,325,751)** = **2873 bytes**
- decompresses to **18,401 bytes** of clean 100%-printable text — the real, complete
  `descr_sm_factions.txt` (starts with the `;;;;` banner + `faction england / culture
  northern_european …`, ends with the `rebels` faction). Saved to
  `research/descr_sm_factions_decompressed.txt`.
- The size fields live in the manifest trailer: **unc=18401 @ byte 932468**,
  **comp=2873 @ byte 932472** (the entry the manifest labels `descr_skeleton.txt`; the
  name↔data label offset is a cosmetic puzzle, irrelevant to patching — the blob content
  and its 2873/18401 sizes are what matter).

**Patch recipe (no LZO *compressor* needed):**
1. `backup data_0.pack` (1 GB) → `data_0.pack.bak`.
2. Decompress the blob (lzo1x) → edit the 18401-byte text: add the new faction blocks.
3. Store the edited text **UNCOMPRESSED** (the format supports it — `descr_sm_resources`
   is stored with comp==unc). Set the manifest `unc` AND `comp` (932468/932472) to the
   new byte length; splice the raw text in place of the 2873-byte blob.
4. Subsequent same-pack data shifts automatically (offsets are sequential — no table).
5. Hand the build to the maintainer to test (do NOT launch the game).

Risk to verify on first build: that the game accepts comp==unc as "stored uncompressed"
for this file. If not, implement an LZO1X *compressor* (or reuse a real lzo lib) instead.

---
### (historical) earlier reasoning — kept for context

The earlier "stored uncompressed, no codec" claim was wrong. Proof: in the 3886-byte
blob each field keyword (`culture`, `religion`, `primary_colour`, `can_sap`, …) and
`northern_european` each appears **exactly once**, although ~20 factions share those
fields → later factions use **back-references**. The real `descr_sm_factions.txt` is
~17 KB, so 17 KB → 3886 B is genuine compression (~4.4×). The offset 955322841 / size
3886 are still correct; the blob is just compressed, not plain.

### Codec characterisation (LZ77/LZ4 family, custom)
- Clean ASCII literal runs separated by control bytes ⇒ `[token | literals | offset |
  match]` layout. Brute force best fit: **token hi-nibble = literal length, lo-nibble =
  match length, 2-byte LE offset, min-match 4** (classic LZ4 token), which decodes the
  literals correctly (fragments like `…ction descrip…`, `logo_ind…`, `…gets removed
  fr…`, `…match` appear).
- BUT matches don't resolve: blob starts `2f bc 00 8c 14 …` → first token would need a
  match ~5260 bytes back while only 2 bytes are output ⇒ **not vanilla LZ4**. Likely a
  **preset dictionary** (static window before pos 0) or a non-standard offset scheme.
- Tools: `crack_lzss.py` (flag-byte LZSS variants — rejected), `crack_lz4.py`
  (LZ4-family variants — literals OK, offsets unresolved), `dump_factions_binary.py`.

### Two ways forward for Option A
1. **Fully reverse the codec** (find the preset dictionary / true offset semantics),
   decode → edit text → re-encode. Cleanest but deep & uncertain.
2. **All-literal re-emit:** if the codec accepts an all-literals stream (LZ4 does),
   emit the entire edited ~17 KB text as literals only (no matches needed to ENCODE),
   then update the size field(s). Needs the outer token/literal-length framing confirmed
   and the game's decompressor to accept it + the decompressed-size field located.

## Open items
- Crack the offset/dictionary scheme OR confirm the all-literal framing (#2).
- Locate the **decompressed-size** field the allocator uses (not yet found; `comp=976`
  in the manifest may be it — needs checking).
- Confirm size field(s) the game reads for the stored blob (manifest `unc`, or binsec).

## Patch plan implications (Option A)

Adding faction blocks grows the uncompressed (and stored) size, which **shifts every
subsequent data blob**. Because data offsets are cumulative (not stored), we do NOT have
to rewrite an offset table — but we MUST:
1. write the new stored blob at the right place,
2. update `unc`/`comp`/`crc32` in the manifest entry,
3. shift all following data bytes by the size delta,
4. keep everything else byte-identical.
The name-offset column (col0) only changes if the manifest itself grows; the manifest
entry for sm_factions keeps the same name length, so only its trailer changes → col0
stays valid. (Verify no other table encodes absolute data offsets before relying on this.)

## Tools (in `tools/`)
- `probe_pack_format.py` — header + manifest entry layout proof
- `locate_factions_blob.py` — full manifest walk, cumulative offset estimate
- `decode_offset_table.py` — proves binary section col0 = name-offsets (no data offsets)
- `probe_columns.py` — columnar analysis of the binary section
