# Faction map — Complete Edition roster & settlement assignments

Start date 1080 (vanilla Grand Campaign). Design rule: every vanilla rebel settlement
that had a real polity in 1080 becomes that faction; later polities spawn by event.
Target: 44 registered factions (42 campaign + normans/saxons battle-only).

## Roster overview

| Batch | Factions | Status |
|---|---|---|
| base | 21 vanilla campaign + slave + normans/saxons (battle-only) | ✅ in repo (33 registered with the 9 below) |
| base | croatia, ragusa, serbia, bulgaria, wallachia, wales, ireland, norway, jerusalem | ✅ working (inherited from croatia-overhaul) |
| 1 (M3) | teutonic_order, lithuania, novgorod, antioch + russia re-seat | planned |
| 2 (M4) | sweden, bohemia, aragon, genoa, georgia, armenia, kievan_rus | planned |
| later | Americas factions (map extension), bosnia (assets already present) | deferred |

## Batch 1+2 settlement assignments (names verified against vanilla descr_strat)

| Faction | Start settlement | Transfer | Rationale / notes |
|---|---|---|---|
| sweden | Stockholm_Province | slave→ | Helsinki stays rebel. Stockholm anachronistic for 1080 but it is the map's Sweden slot. |
| novgorod | Novgorod_Province | **russia→** | Requires the Russia re-seat below. Faction assets ported from Teutonic DLC `novgorod`. |
| russia (re-seat) | Moscow_Province | slave→ | Vanilla Russia holds only Novgorod. Moving Russia to Moscow frees Novgorod and gives a Muscovy flavour. Alternative: Ryazan (Moscow founded 1147) — the maintainer decides at M3. |
| kievan_rus | Kiev_Province | slave→ | Optionally +Smolensk later for balance. |
| georgia | Tbilisi_Province | slave→ | Greek culture, Orthodox. |
| armenia | Adana_Province | slave→ | Cilician Armenia. Yerevan is Turk-owned — untouched. |
| aragon | Zaragoza_Province | slave→ | Valencia stays rebel (El Cid flavour). 1080 Zaragoza was a Muslim taifa — gameplay wins. |
| genoa | Genoa_Province | **milan→** | Milan keeps Milan only (historically correct for 1080). |
| bohemia | Prague_Province | slave→ | |
| lithuania | Vilnius_Province | slave→ | Pagan; religion setup ported from Teutonic DLC. |
| teutonic_order | spawn ~1226 near Riga_Province (target Thorn_Province) | event | `spawned_on_event` like mongols/timurids. Fallback if scripting fights us: start at Thorn on turn 1. |
| antioch | Antioch_Province | slave→ | On-map from 1080 (18-year anachronism, grandfathered like Jerusalem). |

## Anachronism policy

Every polity that existed in 1080 starts on-map. Later polities (Teutonic Order)
spawn via event. Jerusalem and Antioch are grandfathered as on-map gameplay anchors
(the working base already ships Jerusalem this way).

## Unit rosters (initial, EDU ownership only — no new models before M5)

| Faction | Roster source |
|---|---|
| sweden | denmark + norway |
| bohemia | hre + poland picks |
| aragon | spain + portugal |
| genoa | milan (incl. Genoese crossbows) + venice picks |
| georgia, armenia | byzantium subset |
| kievan_rus, novgorod | russia (novgorod uniques from Teutonic DLC in M5) |
| teutonic_order, lithuania | Teutonic DLC rosters (ported in M3/M5) |
| antioch | jerusalem roster interim; Crusades DLC antioch uniques in M5 |
