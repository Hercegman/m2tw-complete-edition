#!/usr/bin/env python3
"""Build all per-faction data the base 9 factions were missing.

Reusable for later batches: extend FACTIONS/DLC_FACTIONS specs and re-run.
Idempotent: regenerates outputs from vanilla/DLC sources each run.

Does, in order:
  1. EDU: appends new factions to `ownership` lines of every unit owned by
     their roster-source faction (bodyguards included -> fixes the
     "no general unit for faction(X)" asserts).
  2. descr_names.txt: vanilla + DLC blocks (wales/ireland/norway/jerusalem)
     + generated Balkan blocks (strat character names guaranteed present).
  3. text/names.txt.strings.bin: vanilla + all DLC name tables + new names.
  4. text/expanded.txt.strings.bin: vanilla + DLC faction key sets +
     generated key sets for the Balkan factions (WALES template).
  5. descr_strat: replaces engine-invalid female heir/diplomat entries.
  6. data/menu/symbols/fe_*: copies DLC faction art; wales.tga placeholder
     for factions with no source art (replaced in the polish milestone).
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import strings_bin

DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
VAN = os.path.join(ROOT, "research", "vanilla-extract", "data")
TSRC = os.path.join(ROOT, "research", "text-src")
DLC = {
    "british_isles": os.path.join(ROOT, "research", "dlc-extract", "british_isles", "mods", "british_isles", "data"),
    "crusades": os.path.join(ROOT, "research", "dlc-extract", "crusades", "mods", "crusades", "data"),
    "teutonic": os.path.join(ROOT, "research", "dlc-extract", "teutonic", "mods", "teutonic", "data"),
}

# faction -> (EDU roster source faction, expanded source: ("dlc", pack) or ("template", short, adjective, display))
FACTIONS = {
    "croatia":   ("hungary",   ("template", "Croatia", "Croatian", "Kingdom of Croatia")),
    "ragusa":    ("venice",    ("template", "Ragusa", "Ragusan", "Republic of Ragusa")),
    "serbia":    ("byzantium", ("template", "Serbia", "Serbian", "Kingdom of Serbia")),
    "bulgaria":  ("byzantium", ("template", "Bulgaria", "Bulgarian", "Tsardom of Bulgaria")),
    "wallachia": ("hungary",   ("template", "Wallachia", "Wallachian", "Principality of Wallachia")),
    "wales":     ("england",   ("dlc", "british_isles")),
    "ireland":   ("scotland",  ("dlc", "british_isles")),
    "norway":    ("denmark",   ("dlc", "british_isles")),
    "jerusalem": ("france",    ("dlc", "crusades")),
}

STRENGTHS = {
    "croatia":   ("Solid balanced roster of infantry and cavalry.", "Fields little in the way of gunpowder units.", "Croat Axemen"),
    "ragusa":    ("Strong navy and wealthy trade economy.", "Small land army with weak heavy cavalry.", "Ragusan Crossbowmen"),
    "serbia":    ("Excellent heavy cavalry in the Byzantine tradition.", "Lacks strong missile infantry.", "Serbian Knights"),
    "bulgaria":  ("Versatile army mixing steppe horsemen and solid infantry.", "Few elite late-period units.", "Bulgarian Brigands"),
    "wallachia": ("Fast light cavalry and deadly ambush tactics.", "Weak heavy infantry.", "Voivode Riders"),
}

# descr_names pools for the generated factions; strat names MUST appear here.
NAMES = {
    "croatia": (
        ["Dmitar", "Stjepan", "Petar", "Miroslav", "Kresimir", "Tomislav",
         "Branimir", "Domagoj", "Trpimir", "Borna", "Ljudevit", "Drzislav",
         "Gojslav", "Zdeslav", "Vladimir", "Hrvoje", "Berislav", "Sedeh"],
        ["Zvonimir", "Trpimirovic", "Svacic", "Kacic", "Subic", "Frankopan",
         "Babonic", "Gusic", "Kurjakovic"],
        ["Helena", "Jelena", "Marija", "Dobrila", "Vekenega", "Lepa"],
    ),
    "ragusa": (
        ["Paskoje", "Durad", "Marin", "Luka", "Junije", "Nikola", "Ivan",
         "Frano", "Vlaho", "Savin", "Orsat", "Marojica", "Damjan", "Matko"],
        ["Sorkocevic", "Buncic", "Caboga", "Gundulic", "Getaldic", "Drzic",
         "Mencetic", "Bunic", "Gradic", "Zamanja"],
        ["Anita", "Nikoleta", "Marija", "Cvijeta", "Desa", "Franica"],
    ),
    "serbia": (
        ["Vukan", "Nemanja", "Stefan", "Uros", "Dragutin", "Milutin",
         "Lazar", "Dusan", "Rastko", "Miroslav", "Tihomir", "Stracimir",
         "Grdesa", "Zavida", "Vlastimir"],
        ["Nemanjic", "Vojislavljevic", "Vukanovic", "Lazarevic", "Brankovic",
         "Mrnjavcevic"],
        ["Milica", "Jelena", "Simonida", "Teodora", "Jevrosima"],
    ),
    "bulgaria": (
        ["Konstantin", "Petar", "Boris", "Simeon", "Samuil", "Gavril",
         "Ivan", "Kaloyan", "Asen", "Todor", "Georgi", "Sveta", "Presian",
         "Aleksandar"],
        ["Bodin", "Deljan", "Asen", "Terter", "Shishman", "Komitopul"],
        ["Maria", "Tamara", "Irina", "Kera", "Desislava"],
    ),
    "wallachia": (
        ["Seneslav", "Litovoi", "Radu", "Mircea", "Vlad", "Dan", "Basarab",
         "Nicolae", "Tihomir", "Barbat", "Ivanco", "Bogdan", "Petru"],
        ["Basarab", "Danesti", "Draculesti", "Craiovescu", "Musat"],
        ["Ana", "Ilinca", "Ruxandra", "Stanca", "Voica"],
    ),
}

# DLC-sourced factions: which DLC's descr_names block to copy
DLC_NAME_BLOCKS = {
    "wales": "british_isles",
    "ireland": "british_isles",
    "norway": "british_isles",
    "jerusalem": "crusades",
}

# names our descr_strat uses that the DLC pools don't contain
EXTRA_NAMES = {
    "wales": ([], ["ap Cynan"]),
    "ireland": (["Muirchertach"], ["O Brien"]),
    "norway": ([], ["Kyrre"]),
    "jerusalem": (["Godefroy"], []),
}

STRAT = os.path.join(DATA, "world", "maps", "campaign", "imperial_campaign", "descr_strat.txt")
STRAT_FIXES = [
    ("character\tAnita Sorkocevic, named character, female, heir, age 22",
     "character\tJunije Sorkocevic, named character, male, heir, age 22"),
    ("character\tMilica, diplomat, female, age 25",
     "character\tTihomir, diplomat, male, age 25"),
]

MENU_SYMBOL_DIRS = ["fe_symbols_80", "fe_faction_units", "fe_buttons_48", "fe_buttons_24"]


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def step1_edu():
    path = os.path.join(DATA, "export_descr_unit.txt")
    src = os.path.join(VAN, "export_descr_unit.txt")
    lines = read(src).split("\n")  # always regenerate from vanilla
    out = []
    added = {f: 0 for f in FACTIONS}
    for line in lines:
        m = re.match(r"^(ownership\s+)(.*?)(\s*)$", line)
        if m:
            owners = [o.strip() for o in m.group(2).split(",") if o.strip()]
            for fac, (roster_src, _) in FACTIONS.items():
                if roster_src in owners and fac not in owners:
                    owners.append(fac)
                    added[fac] += 1
            line = m.group(1) + ", ".join(owners)
        out.append(line)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("EDU ownership additions:", added)
    assert all(v > 0 for v in added.values()), "some faction got no units"


def dlc_names_block(faction, dlc):
    text = read(os.path.join(DLC[dlc], "descr_names.txt"))
    m = re.search(rf"^faction: {faction}\s*\n(.*?)(?=^faction: |\Z)", text, re.M | re.S)
    assert m, f"no {faction} block in {dlc} descr_names"
    block = f"faction: {faction}\n" + m.group(1).rstrip() + "\n"
    extra_chars, extra_surnames = EXTRA_NAMES.get(faction, ([], []))
    if extra_chars:
        block = block.replace("\tcharacters\n",
                              "\tcharacters\n" + "".join(f"\t\t{n}\n" for n in extra_chars), 1)
    if extra_surnames:
        if re.search(r"^\tsurnames", block, re.M):
            block = re.sub(r"^(\tsurnames\s*\n)",
                           r"\1" + "".join(f"\t\t{n}\n" for n in extra_surnames),
                           block, count=1, flags=re.M)
        else:
            block += "\n\tsurnames\n" + "".join(f"\t\t{n}\n" for n in extra_surnames)
    return block


def gen_names_block(faction):
    chars, surnames, women = NAMES[faction]
    b = [f"faction: {faction}", "", "\tcharacters"]
    b += [f"\t\t{n}" for n in chars]
    b += ["", "\tsurnames"] + [f"\t\t{n}" for n in surnames]
    b += ["", "\twomen"] + [f"\t\t{n}" for n in women]
    return "\n".join(b) + "\n"


def step2_descr_names():
    blocks = [read(os.path.join(VAN, "descr_names.txt")).rstrip() + "\n"]
    for fac in FACTIONS:
        if fac in DLC_NAME_BLOCKS:
            blocks.append(dlc_names_block(fac, DLC_NAME_BLOCKS[fac]))
        else:
            blocks.append(gen_names_block(fac))
    out = os.path.join(DATA, "descr_names.txt")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(blocks))
    print(f"descr_names.txt: vanilla + {len(FACTIONS)} new blocks -> {out}")


def step3_names_bin():
    entries, tokens = strings_bin.read_names_bin(os.path.join(TSRC, "names_vanilla.strings.bin"))
    merged = dict(entries)
    order = [k for k, _ in entries]
    token_set = set(tokens)
    for dlc in DLC.values():
        d_entries, d_tokens = strings_bin.read_names_bin(os.path.join(dlc, "text", "names.txt.strings.bin"))
        for k, v in d_entries:
            if k not in merged:
                merged[k] = v
                order.append(k)
        for t in d_tokens:
            if t not in token_set:
                token_set.add(t)
                tokens.append(t)
    extra_flat = [n for c, s in EXTRA_NAMES.values() for n in c + s]
    for chars, surnames, women in list(NAMES.values()) + [(extra_flat, [], [])]:
        for n in chars + surnames + women:
            if n not in merged:
                merged[n] = n
                order.append(n)
            if n not in token_set:
                token_set.add(n)
                tokens.append(n)
    outdir = os.path.join(DATA, "text")
    os.makedirs(outdir, exist_ok=True)
    strings_bin.write_names_bin(os.path.join(outdir, "names.txt.strings.bin"),
                                [(k, merged[k]) for k in order], tokens)
    print(f"names.txt.strings.bin: {len(order)} entries, {len(tokens)} tokens")


def faction_keys(decoded_entries, token):
    return [(k, v) for k, v in decoded_entries if token in k]


def step4_expanded_bin():
    vanilla = strings_bin.read_bin(os.path.join(TSRC, "expanded_vanilla.strings.bin"))
    dlc_expanded = {
        name: strings_bin.read_bin(os.path.join(path, "text", "expanded.txt.strings.bin"))
        for name, path in DLC.items()
    }
    merged = dict(vanilla)
    order = [k for k, _ in vanilla]

    def add(k, v):
        if k not in merged:
            order.append(k)
        merged[k] = v

    wales_tpl = faction_keys(dlc_expanded["british_isles"], "WALES")
    assert wales_tpl, "no WALES keys found"

    for fac, (_, spec) in FACTIONS.items():
        token = fac.upper()
        if spec[0] == "dlc":
            for k, v in faction_keys(dlc_expanded[spec[1]], token):
                add(k, v)
        else:
            _, short, adj, display = spec
            for k, v in wales_tpl:
                nk = k.replace("WALES", token)
                nv = v.replace("Welsh", adj).replace("Wales", short)
                add(nk, nv)
            strength, weakness, unit = STRENGTHS[fac]
            add(token, short)
            add(f"{token}_STRENGTH", strength)
            add(f"{token}_WEAKNESS", weakness)
            add(f"{token}_UNIT", unit)
            add(f"EMT_VICTORY_{token}", f"The {adj}s are Victorious")

    out = os.path.join(DATA, "text", "expanded.txt.strings.bin")
    strings_bin.write_bin(out, [(k, merged[k]) for k in order])
    print(f"expanded.txt.strings.bin: {len(order)} entries "
          f"({len(order) - len(vanilla)} new)")


def step5_strat_fixes():
    text = read(STRAT)
    n = 0
    for old, new in STRAT_FIXES:
        if old in text:
            text = text.replace(old, new)
            n += 1
    with open(STRAT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"descr_strat: {n}/{len(STRAT_FIXES)} gender fixes applied")


def step6_menu_symbols():
    dst_base = os.path.join(DATA, "menu", "symbols")
    copied, placeholder = 0, 0
    for fac in FACTIONS:
        src_dlc = DLC_NAME_BLOCKS.get(fac)
        for d in MENU_SYMBOL_DIRS:
            dst_dir = os.path.join(dst_base, d)
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, f"{fac}.tga")
            if src_dlc:
                src = os.path.join(DLC[src_dlc], "menu", "symbols", d, f"{fac}.tga")
                if os.path.exists(src):
                    shutil.copyfile(src, dst)
                    copied += 1
                    continue
            tpl = os.path.join(DLC["british_isles"], "menu", "symbols", d, "wales.tga")
            if os.path.exists(tpl) and not os.path.exists(dst):
                shutil.copyfile(tpl, dst)
                placeholder += 1
    print(f"menu symbols: {copied} copied from DLC, {placeholder} wales-placeholders")


def main():
    step1_edu()
    step2_descr_names()
    step3_names_bin()
    step4_expanded_bin()
    step5_strat_fixes()
    step6_menu_symbols()
    # the loose expanded.txt is superseded by the compiled bin
    loose = os.path.join(DATA, "text", "expanded.txt")
    if os.path.exists(loose):
        os.makedirs(TSRC, exist_ok=True)
        shutil.move(loose, os.path.join(TSRC, "expanded_new_factions_source.txt"))
        print("moved loose text/expanded.txt out of the mod (bin is authoritative)")


if __name__ == "__main__":
    main()
