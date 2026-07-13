# M2TW Complete Edition

One Grand Campaign with everything: all Kingdoms DLC factions merged into the vanilla
map, and every rebel settlement that had a real polity in 1080 replaced by that faction
(Croatia, Ragusa, Serbia, Bulgaria, Wallachia, Wales, Ireland, Norway, Jerusalem,
Teutonic Order, Lithuania, Novgorod, Antioch, Sweden, Bohemia, Aragon, Genoa, Georgia,
Cilician Armenia, Kievan Rus, …). Target: 44 registered factions.

Runs on the **M2EX/REX** engine extender (github.com/Pannoniae/rex), which removes the
31-faction hard cap (config-gated via `data/descr_ex.txt` → `max_factions`).
Successor to the `croatia-overhaul` project — its working 9-faction loose-file
conversion is the base here; croatia-overhaul stays untouched as reference.

## Layout

- `mod/complete_edition/` → deployed to `<game>/mods/complete_edition`
- `launcher/` → `complete_edition.bat` (M2EX) + `complete_edition.cfg` (trace log, file_first)
- `tools/` → pack codec/unpacker (LZO1X), validators, log parser
- `research/` → vanilla pack extract + pack format notes
- `docs/` → M2EX notes, faction map, handoff protocol, milestone plan

## Workflow

```
./deploy.sh --dry-run   # validators + preview
./deploy.sh             # validators gate the copy into the game folder
```

Builds are tested by the maintainer (never launched from tooling); the game trace log comes back
and is triaged with `tools/check_log.py`. See `docs/HANDOFF.md`.

Repo conventions: commit messages and dev-log entries in English.
