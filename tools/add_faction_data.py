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
# The first roster source is also the "mate" whose descr_character/banner
# entries get cloned; extra sources only widen the unit roster (the maintainer: the
# Balkan kingdoms should field a hungarian/russian mix, ragusa venetian).
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
    # batch M3+M4
    "teutonic_order": ("hre",     ("dlc", "teutonic")),
    "lithuania":      ("poland",  ("dlc", "teutonic")),
    "novgorod":       ("russia",  ("dlc", "teutonic")),
    "antioch":        ("france",  ("dlc", "crusades")),
    "sweden":     ("denmark",   ("template", "Sweden", "Swedish", "Kingdom of Sweden")),
    "bohemia":    ("hre",       ("template", "Bohemia", "Bohemian", "Kingdom of Bohemia")),
    "aragon":     ("spain",     ("template", "Aragon", "Aragonese", "Kingdom of Aragon")),
    "genoa":      ("milan",     ("template", "Genoa", "Genoese", "Republic of Genoa")),
    "pisa":       ("milan",     ("template", "Pisa", "Pisan", "Republic of Pisa")),
    "georgia":    ("byzantium", ("template", "Georgia", "Georgian", "Kingdom of Georgia")),
    "armenia":    ("byzantium", ("template", "Armenia", "Armenian", "Kingdom of Cilician Armenia")),
    "kievan_rus": ("russia",    ("template", "Kievan Rus", "Kievan", "Principality of Kievan Rus")),
}

EXTRA_ROSTER = {
    "croatia": ["russia"],
    "serbia": ["hungary", "russia"],
    "bulgaria": ["hungary", "russia"],
    "wallachia": ["russia"],
    "teutonic_order": ["poland"],
    "lithuania": ["russia"],
    "novgorod": ["denmark"],
    "antioch": ["england"],
    "aragon": ["portugal"],
    "genoa": ["venice"],
    "pisa": ["venice"],
    "georgia": ["russia"],
    "armenia": ["turks"],
    "kievan_rus": ["poland"],
}

STRENGTHS = {
    "croatia":   ("Solid balanced roster of infantry and cavalry.", "Fields little in the way of gunpowder units.", "Croat Axemen"),
    "ragusa":    ("Strong navy and wealthy trade economy.", "Small land army with weak heavy cavalry.", "Ragusan Crossbowmen"),
    "serbia":    ("Excellent heavy cavalry in the Byzantine tradition.", "Lacks strong missile infantry.", "Serbian Knights"),
    "bulgaria":  ("Versatile army mixing steppe horsemen and solid infantry.", "Few elite late-period units.", "Bulgarian Brigands"),
    "wallachia": ("Fast light cavalry and deadly ambush tactics.", "Weak heavy infantry.", "Voivode Riders"),
    "sweden":    ("Sturdy northern infantry and strong crossbowmen.", "Limited heavy cavalry.", "Svenner"),
    "bohemia":   ("Well-armoured imperial-style infantry and knights.", "Few missile troops.", "Bohemian Knights"),
    "aragon":    ("Fine jinete-style cavalry and hardy spearmen.", "Weak archery.", "Almogavars"),
    "genoa":     ("The finest crossbowmen in Europe and a mighty navy.", "Small feudal cavalry arm.", "Genoese Crossbowmen"),
    "pisa":      ("Strong navy and disciplined communal militia.", "Little heavy cavalry.", "Pisan Militia"),
    "georgia":   ("Superb heavy cavalry in the Byzantine tradition.", "Sparse infantry roster.", "Georgian Cavalry"),
    "armenia":   ("Tough mountain infantry and versatile horse archers.", "Lacks late heavy knights.", "Armenian Archers"),
    "kievan_rus": ("Druzhina heavy cavalry and masses of spear levies.", "Slow to modernise.", "Druzhina"),
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
    "sweden": (
        ["Inge", "Filip", "Ragnvald", "Sverker", "Erik", "Knut", "Karl",
         "Magnus", "Birger", "Jedvard", "Halsten", "Blot-Sven"],
        ["Stenkil", "Sverkersson", "Eriksson", "Jedvardsson"],
        ["Helena", "Kristina", "Ingegerd", "Ulvhild"],
    ),
    "bohemia": (
        ["Vratislav", "Bretislav", "Sobeslav", "Jaromir", "Spytihnev",
         "Borivoj", "Oldrich", "Vaclav", "Ottokar", "Conrad", "Svatopluk"],
        ["Premyslid", "Vrsovec", "Slavnik"],
        ["Svatava", "Ludmila", "Bozena", "Judita"],
    ),
    "aragon": (
        ["Sancho Ramirez", "Pedro", "Alfonso", "Ramiro", "Garcia", "Fortun",
         "Jaime", "Fernando", "Berenguer", "Galindo"],
        ["Ramirez", "Aznarez", "Galindez", "Jimenez"],
        ["Felicia", "Urraca", "Sancha", "Petronila"],
    ),
    "genoa": (
        ["Guglielmo Embriaco", "Ansaldo", "Caffaro", "Oberto", "Lanfranco",
         "Simone", "Ottone", "Enrico", "Ugo", "Ingo", "Ido"],
        ["Embriaco", "Doria", "Spinola", "Grimaldi", "Fieschi"],
        ["Alda", "Giulietta", "Sibilla", "Adelasia"],
    ),
    "pisa": (
        ["Gerardo", "Ugo", "Lamberto", "Ildebrando", "Pietro", "Ranieri",
         "Daiberto", "Maruccio", "Sigerio", "Bulgarino"],
        ["Visconti", "Gherardesca", "Orlandi", "Sismondi"],
        ["Matilde", "Berta", "Gisla", "Contessa"],
    ),
    "georgia": (
        ["Giorgi", "Davit", "Ivane", "Zakaria", "Bagrat", "Demetre",
         "Vakhtang", "Levan", "Archil", "Sumbat"],
        ["Bagrationi", "Mkhargrdzeli", "Orbeliani"],
        ["Tamar", "Rusudan", "Mariam", "Ketevan"],
    ),
    "armenia": (
        ["Ruben", "Kostandin", "Toros", "Levon", "Mleh", "Hetum", "Oshin",
         "Smbat", "Vahram", "Gagik"],
        ["Rubenian", "Hetumian", "Pahlavuni"],
        ["Zabel", "Alits", "Rita", "Keran"],
    ),
    "kievan_rus": (
        ["Vsevolod", "Vladimir Monomakh", "Sviatopolk", "Oleg", "Iziaslav",
         "Yaroslav", "Mstislav", "Igor", "Sviatoslav", "Rostislav", "Yuri"],
        ["Monomakh", "Rurikovich", "Olgovich"],
        ["Gytha", "Anna", "Predslava", "Evpraksia"],
    ),
}

# DLC-sourced factions: which DLC's descr_names block to copy
DLC_NAME_BLOCKS = {
    "wales": "british_isles",
    "ireland": "british_isles",
    "norway": "british_isles",
    "jerusalem": "crusades",
    "teutonic_order": "teutonic",
    "lithuania": "teutonic",
    "novgorod": "teutonic",
    "antioch": "crusades",
}

# names our descr_strat uses that the DLC pools don't contain
EXTRA_NAMES = {
    "wales": ([], ["ap Cynan"]),
    "ireland": (["Muirchertach"], ["O Brien"]),
    "norway": ([], ["Kyrre"]),
    "jerusalem": (["Godefroy"], []),
    "teutonic_order": (["Heinrich", "Hermann", "Otto", "Konrad"], ["Walpot"]),
    "lithuania": (["Skirmantas", "Vykintas", "Daumantas", "Treniota"], []),
    "novgorod": (["Mstislav", "Dobrynya", "Sadko", "Gavrilo"], []),
    "antioch": (["Bohemond", "Tancred", "Raymond", "Guy"], []),
}

STRAT = os.path.join(DATA, "world", "maps", "campaign", "imperial_campaign", "descr_strat.txt")
STRAT_FIXES = [
    ("character\tAnita Sorkocevic, named character, female, heir, age 22",
     "character\tJunije Sorkocevic, named character, male, heir, age 22"),
    ("character\tMilica, diplomat, female, age 25",
     "character\tTihomir, diplomat, male, age 25"),
    # invalid tiles reported by the engine; relocate onto the leaders' tiles
    ("character\tPetar, diplomat, male, age 28, x 156, y 116",
     "character\tPetar, diplomat, male, age 28, x 157, y 115"),
    ("character\tDurad Buncic, diplomat, male, age 35, x 155, y 120",
     "character\tDurad Buncic, diplomat, male, age 35, x 157, y 121"),
]

MENU_SYMBOL_DIRS = ["fe_symbols_80", "fe_faction_units", "fe_buttons_48", "fe_buttons_24"]


# M2TW data text files are windows-1252/latin-1, NOT utf-8. Reading them as
# utf-8 with errors="replace" destroys non-ASCII names (of_Boðsa -> of_Bo�sa)
# and the engine then can't match them against the names stringtable.
ENC = "latin-1"


def read(path):
    with open(path, encoding=ENC) as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding=ENC, newline="\n") as f:
        f.write(text)


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
                sources = [roster_src] + EXTRA_ROSTER.get(fac, [])
                if fac not in owners and any(s in owners for s in sources):
                    owners.append(fac)
                    added[fac] += 1
            line = m.group(1) + ", ".join(owners)
        out.append(line)
    write(path, "\n".join(out))
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


def strat_record_names():
    """Names used by character_record lines in each new faction's strat block —
    they must exist in that faction's pool or the record is dropped
    ('Couldn't find name Mara in the names database')."""
    strat = read(STRAT)
    facs = "|".join(FACTIONS)
    out = {f: ([], []) for f in FACTIONS}  # (male, female)
    current = None
    for line in strat.split("\n"):
        m = re.match(rf"^faction\s+({facs})\b", line)
        if m:
            current = m.group(1)
            continue
        if re.match(r"^faction\s", line):
            current = None
            continue
        m = re.match(r"^character_record\s+([A-Za-z' ]+?),\s*(male|female)", line.replace("\t", " ").strip())
        if m and current:
            name, gender = m.group(1).strip(), m.group(2)
            out[current][0 if gender == "male" else 1].append(name)
    return out


def step2_descr_names():
    record_names = strat_record_names()
    blocks = [read(os.path.join(VAN, "descr_names.txt")).rstrip() + "\n"]
    for fac in FACTIONS:
        if fac in DLC_NAME_BLOCKS:
            block = dlc_names_block(fac, DLC_NAME_BLOCKS[fac])
        else:
            block = gen_names_block(fac)
        # auto-append any strat character_record name missing from the pool
        males, females = record_names[fac]
        for name in males:
            first = name.split(" ")[0]
            if not re.search(rf"^\t\t{re.escape(first)}\s*$", block, re.M):
                block = block.replace("\tcharacters\n", f"\tcharacters\n\t\t{first}\n", 1)
        for name in females:
            first = name.split(" ")[0]
            if not re.search(rf"^\t\t{re.escape(first)}\s*$", block, re.M):
                if "\twomen\n" not in block:
                    block += "\n\twomen\n"
                block = block.replace("\twomen\n", f"\twomen\n\t\t{first}\n", 1)
        blocks.append(block)
    out = os.path.join(DATA, "descr_names.txt")
    write(out, "\n".join(blocks))
    print(f"descr_names.txt: vanilla + {len(FACTIONS)} new blocks (+ strat record names) -> {out}")


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
    for males, females in strat_record_names().values():
        extra_flat += [p for full in males + females for p in ([full.split(" ")[0]] +
                       ([" ".join(full.split(" ")[1:])] if " " in full else []))]
    for chars, surnames, women in list(NAMES.values()) + [(extra_flat, [], [])]:
        for n in chars + surnames + women:
            # stringtable keys and tokens use underscores for multi-word
            # names ("ap Cynan" in the pool -> key/token "ap_Cynan")
            key = n.replace(" ", "_")
            if key not in merged:
                merged[key] = n
                order.append(key)
            if key not in token_set:
                token_set.add(key)
                tokens.append(key)
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
    write(STRAT, text)
    print(f"descr_strat: {n}/{len(STRAT_FIXES)} gender fixes applied")


def step6_menu_symbols():
    """Faction-select screen art. File names per dir (verified in the DLC):
    fe_symbols_80/<f>.tga, fe_faction_units/<f>.tga,
    fe_buttons_48/symbol48_<f>[_roll|_select|_grey].tga,
    fe_buttons_24/symbol24_<f>[...].tga — the _grey/_select button states are
    what makes a faction clickable in the selector."""
    patterns = {
        "fe_symbols_80": ["{f}.tga"],
        "fe_faction_units": ["{f}.tga"],
        "fe_buttons_48": ["symbol48_{f}.tga", "symbol48_{f}_roll.tga",
                          "symbol48_{f}_select.tga", "symbol48_{f}_grey.tga"],
        "fe_buttons_24": ["symbol24_{f}.tga", "symbol24_{f}_roll.tga",
                          "symbol24_{f}_select.tga", "symbol24_{f}_grey.tga"],
    }
    dst_base = os.path.join(DATA, "menu", "symbols")
    copied, placeholder, missing = 0, 0, []
    for fac in FACTIONS:
        src_dlc = DLC_NAME_BLOCKS.get(fac)
        for d, pats in patterns.items():
            dst_dir = os.path.join(dst_base, d)
            os.makedirs(dst_dir, exist_ok=True)
            for pat in pats:
                dst = os.path.join(dst_dir, pat.format(f=fac))
                if src_dlc:
                    src = os.path.join(DLC[src_dlc], "menu", "symbols", d, pat.format(f=fac))
                    if os.path.exists(src):
                        shutil.copyfile(src, dst)
                        copied += 1
                        continue
                tpl = os.path.join(DLC["british_isles"], "menu", "symbols", d, pat.format(f="wales"))
                if os.path.exists(tpl):
                    shutil.copyfile(tpl, dst)
                    placeholder += 1
                else:
                    missing.append(f"{d}/{pat.format(f=fac)}")
    print(f"menu symbols: {copied} from DLC, {placeholder} wales-placeholders, "
          f"{len(missing)} missing templates {missing[:3]}")


ROSTER_MATE = {fac: spec[0] for fac, spec in FACTIONS.items()}


def step7_descr_character():
    """Clone each roster-mate's per-type entry in descr_character.txt for the
    new faction. Without this the engine cannot create ANY character of the
    faction -> every named character fails -> faction is instantly destroyed."""
    src = read(os.path.join(VAN, "descr_character.txt"))
    lines = src.split("\n")
    out = []
    i = 0
    added = {f: 0 for f in FACTIONS}
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = re.match(r"^faction\s+(\w+)\s*$", line)
        if m:
            mate = m.group(1)
            block = []
            j = i + 1
            while j < len(lines) and not re.match(r"^(faction|type)\b", lines[j]):
                block.append(lines[j])
                j += 1
            out.extend(block)
            for fac, fmate in ROSTER_MATE.items():
                if fmate == mate:
                    out.append(f"faction\t\t\t{fac}")
                    out.extend(block)
                    added[fac] += 1
            i = j
            continue
        i += 1
    assert all(v > 0 for v in added.values()), f"descr_character: uncloned factions {added}"
    write(os.path.join(DATA, "descr_character.txt"), "\n".join(out))
    print("descr_character type-entries cloned:", added)


def step8_banners_xml():
    """descr_banners_new.xml: give every new faction its own <Texture> entry in
    each <Banner> block. DLC factions point at their real DLC banner textures
    (copied into the mod); the Balkan five reuse their mate's texture for now
    (unique entry, placeholder art until M5)."""
    xml = read(os.path.join(VAN, "descr_banners_new.xml"))
    tex_dst = os.path.join(DATA, "banners", "textures")
    os.makedirs(tex_dst, exist_ok=True)
    tex_copied = 0
    for fac, dlc in DLC_NAME_BLOCKS.items():
        src_dir = os.path.join(DLC[dlc], "banners", "textures")
        if not os.path.isdir(src_dir):
            continue
        for fn in os.listdir(src_dir):
            if f"_{fac}" in fn.lower():
                shutil.copyfile(os.path.join(src_dir, fn), os.path.join(tex_dst, fn))
                tex_copied += 1

    def cap(f):
        return f.capitalize()

    added = 0

    def extend_textures(m):
        nonlocal added
        block = m.group(0)
        new_lines = []
        for fac, mate in ROSTER_MATE.items():
            if re.search(rf'Faction="{cap(fac)}"', block):
                continue
            mate_line = re.search(rf'^([ \t]*)(<Texture Faction="{cap(mate)}"[^>]*/>)\s*$',
                                  block, re.M)
            if not mate_line:
                continue
            indent, line = mate_line.group(1), mate_line.group(2)
            new = line.replace(f'Faction="{cap(mate)}"', f'Faction="{cap(fac)}"')
            # every new faction ships its own texture files (DLC copies for
            # the Kingdoms four, generated heraldry for the Balkan five)
            new = re.sub(r'DiffuseMap="banners\\textures\\[Ff]action_banner_\w+\.texture"',
                         f'DiffuseMap="banners\\\\textures\\\\faction_banner_{fac}.texture"', new)
            new = re.sub(r'TranslucencyMap="banners\\textures\\[Ff]action_banner_\w+_trans\.texture"',
                         f'TranslucencyMap="banners\\\\textures\\\\faction_banner_{fac}_trans.texture"', new)
            new_lines.append(indent + new)
            added += 1
        if not new_lines:
            return block
        return block.replace("</Textures>", "\n".join(new_lines) + "\n         </Textures>")

    xml = re.sub(r"<Textures>.*?</Textures>", extend_textures, xml, flags=re.S)
    write(os.path.join(DATA, "descr_banners_new.xml"), xml)
    print(f"banners xml: {added} texture entries added, {tex_copied} DLC textures copied")


def step10_edb():
    """export_descr_buildings: without recruit_pool/building entries the new
    factions cannot recruit or build ANYTHING. Append each new faction next to
    its roster sources in every `factions { ... }` list — but a recruit_pool
    line is only extended when the faction actually owns that unit in the
    final EDU (otherwise the engine spams 'unit does not match up to the
    ownership' asserts, as GR Ballista did for serbia)."""
    # unit -> owners from the already-generated EDU
    edu = read(os.path.join(DATA, "export_descr_unit.txt"))
    unit_owners = {}
    unit = None
    for line in edu.split("\n"):
        m = re.match(r"^type\s+(.*?)\s*$", line)
        if m:
            unit = m.group(1)
        m = re.match(r"^ownership\s+(.*?)\s*$", line)
        if m and unit:
            unit_owners[unit.lower()] = {o.strip().lower() for o in m.group(1).split(",")}

    src = read(os.path.join(VAN, "export_descr_buildings.txt"))
    added = {f: 0 for f in FACTIONS}
    out_lines = []
    for line in src.split("\n"):
        m = re.match(r'^(\s*)recruit_pool\s+"([^"]+)"', line)
        pool_unit = m.group(2).lower() if m else None

        def extend(mm):
            names = [n.strip() for n in mm.group(1).split(",") if n.strip()]
            lower = {n.lower() for n in names}
            for fac, (mate, _) in FACTIONS.items():
                sources = [mate] + EXTRA_ROSTER.get(fac, [])
                if fac in lower or not any(s in lower for s in sources):
                    continue
                if pool_unit is not None and fac not in unit_owners.get(pool_unit, ()):
                    continue
                names.append(fac.capitalize())
                added[fac] += 1
            return "factions { " + ", ".join(names) + ", }"

        out_lines.append(re.sub(r"factions\s*\{([^}]*)\}", extend, line))
    write(os.path.join(DATA, "export_descr_buildings.txt"), "\n".join(out_lines))
    print("EDB faction-list additions:", added)
    assert all(v > 0 for v in added.values()), "some faction got no EDB entries"


def step11_faction_symbols():
    """ui/faction_symbols/<f>.tga (54x54 crest used by campaign UI): real DLC
    art for the Kingdoms four; the Balkan five get theirs from gen_heraldry."""
    dst_dir = os.path.join(DATA, "ui", "faction_symbols")
    os.makedirs(dst_dir, exist_ok=True)
    n = 0
    for fac, dlc in DLC_NAME_BLOCKS.items():
        src = os.path.join(DLC[dlc], "ui", "faction_symbols", f"{fac}.tga")
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(dst_dir, f"{fac}.tga"))
            n += 1
    print(f"ui/faction_symbols: {n} DLC crests copied")


def step9_strat_symbols():
    """models_strat symbol .cas per faction: real DLC art for the DLC four,
    a clone of the mate's symbol for the Balkan five (distinct file so M5 can
    swap in real heraldry), and descr_sm_factions updated to point at them."""
    dst = os.path.join(DATA, "models_strat")
    os.makedirs(dst, exist_ok=True)
    base_ms = os.path.join(ROOT, "research", "base-extract", "data", "models_strat")
    copied = []
    for fac, mate in ROSTER_MATE.items():
        out = os.path.join(dst, f"symbol_{fac}.cas")
        if fac in DLC_NAME_BLOCKS:
            src = os.path.join(DLC[DLC_NAME_BLOCKS[fac]], "models_strat", f"symbol_{fac}.cas")
        else:
            # template factions get their .cas from gen_heraldry (CAS_DONOR
            # with a patched texture path); nothing to copy here
            continue
        assert os.path.exists(src), f"missing symbol source {src}"
        shutil.copyfile(src, out)
        copied.append(fac)
        # DLC symbol textures (referenced inside the .cas)
        if fac in DLC_NAME_BLOCKS:
            tex_src = os.path.join(DLC[DLC_NAME_BLOCKS[fac]], "models_strat", "textures")
            if os.path.isdir(tex_src):
                tex_dst = os.path.join(dst, "textures")
                os.makedirs(tex_dst, exist_ok=True)
                for fn in os.listdir(tex_src):
                    if f"_{fac}" in fn.lower() and "symbol" in fn.lower():
                        shutil.copyfile(os.path.join(tex_src, fn), os.path.join(tex_dst, fn))
    smf_path = os.path.join(DATA, "descr_sm_factions.txt")
    smf = read(smf_path)
    for fac in FACTIONS:
        smf = re.sub(
            rf"(^faction\s+{fac}\b.*?^symbol\s+)models_strat/\S+",
            rf"\g<1>models_strat/symbol_{fac}.cas",
            smf, count=1, flags=re.M | re.S)
    # NOTE: logo_index/small_logo_index stay on the mates' enums — M2EX.exe
    # strings contain no FACTION_LOGO_WALES/CROATIA/... (checked), so custom
    # per-faction logos need an M2EX feature; tracked for the polish milestone.
    write(smf_path, smf)
    print(f"strat symbols: {copied} -> own .cas, sm_factions updated")


def main():
    step1_edu()
    step2_descr_names()
    step3_names_bin()
    step4_expanded_bin()
    step5_strat_fixes()
    step6_menu_symbols()
    step7_descr_character()
    step8_banners_xml()
    step9_strat_symbols()
    step10_edb()
    step11_faction_symbols()
    # the loose expanded.txt is superseded by the compiled bin
    loose = os.path.join(DATA, "text", "expanded.txt")
    if os.path.exists(loose):
        os.makedirs(TSRC, exist_ok=True)
        shutil.move(loose, os.path.join(TSRC, "expanded_new_factions_source.txt"))
        print("moved loose text/expanded.txt out of the mod (bin is authoritative)")


if __name__ == "__main__":
    main()
