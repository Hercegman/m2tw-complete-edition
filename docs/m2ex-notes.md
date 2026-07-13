# M2EX/REX notes (research 2026-07-13)

## Pinned release

- **Release `21/06`** (published 2026-06-22), asset `M2EX.7z` (144,909,117 B)
- https://github.com/Pannoniae/rex/releases/download/21/06/M2EX.7z
- Do NOT update M2EX mid-milestone: saves use an upgraded format per release and are
  **not backward-compatible** with older M2EX versions (old saves do load in newer).

## What the archive contains (verified by listing M2EX.7z, full list in this repo's docs)

- **Own 64-bit executable `M2EX.exe`** + full DLL set (steam_api64.dll, granny2_x64.dll,
  binkw64.dll, msvc runtimes, Miles sound in `miles/`), `steam_appid.txt` (4700 = Kingdoms).
  It does NOT replace `medieval2.exe` — it sits alongside it.
- Loose data overrides in `data/` (fonts, menu, shaders, terrain, text, ui, vegetation,
  `descr_ex.txt`, `descr_caps_ex.txt`, `descr_model_battle.txt`, …) and per-DLC files
  under `mods/{americas,british_isles,crusades,teutonic}/`.
- `packs/voices.pack`, `tools/pack.exe` (its own pack tool), DLC launcher .bat files.

**Install = extract M2EX.7z into the game root, allowing overwrite.** Rollback: delete
files listed in the archive manifest + Steam Verify Integrity (see
`docs/game-root-manifest-pre-m2ex.txt` for the pre-install state).

## Answers to the three open questions

1. **Mod folders: YES.** M2EX's own DLC launchers use
   `M2EX.exe --features.mod=mods/americas` (verified in `Americas.bat` inside the
   archive). Our launcher uses `--features.mod=mods/complete_edition` and additionally
   passes the classic `@mods/complete_edition/complete_edition.cfg`; if M2EX rejects the
   `@cfg` switch, drop it and rely on `--features.mod` + preference cfg (verify in M0).

2. **Faction cap: lifted via CONFIG, not unconditionally.** `data/descr_ex.txt`
   (optional overrides file shipped with M2EX) contains:

   ```
   ; Maximum number of factions (default in M2: 31, RTW: 21)
   ; Increase to support more factions in mods
   max_factions 31
   ```

   → the cap stays 31 until raised. Our mod ships `data/descr_ex.txt` with
   `max_factions 50`. **Open question for M1:** whether M2EX reads `descr_ex.txt` from
   the mod's data scope; if the captest still refuses >31 factions, edit the GAME's
   `data/descr_ex.txt` instead (set `max_factions 50` there).

3. **file_first / trace log:** not documented in the repo; M2EX claims "compatible with
   all OG mods (excluding EOP mods)", which implies the classic cfg system. Verified in
   M0/M1 by checking that `logs/complete_edition.log.txt` appears and loose files load.

## Other M2EX facts relevant to us

- `data/descr_caps_ex.txt` = engine feature toggles (sprite format, EDB trade fleets,
  `model_battle_source text` — M2EX can parse `descr_model_battle.txt` directly instead
  of `battle_models.modeldb`!). Mods without the file get safe defaults. The
  `model_battle_source text` option may let us AVOID binary BMDB merging entirely in M5
  — investigate before writing bmdb_tool.py.
- Limits uncapped in code per release notes (08/06): cultures (hard 7), religions.
  Factions are config-gated via `max_factions` (see above).
- NOT compatible with M2TWEOP mods. Writes into the main medieval2 folder.
- Community/help: Discord https://discord.gg/X4zyNxUUDA; repo docs: `modding/*.md`,
  `scripting/` in github.com/Pannoniae/rex.
