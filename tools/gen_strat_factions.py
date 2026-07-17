#!/usr/bin/env python3
"""Batch M3+M4: create descr_strat + descr_sm_factions entries for the 12
new factions (teutonic_order, lithuania, novgorod, antioch, sweden, bohemia,
aragon, genoa, pisa, georgia, armenia, kievan_rus).

Per faction: move its settlement block out of the current owner's section
(slave / russia / milan), build a faction section with leader+heir+agents
(coordinates are placeholders — fix_strat_positions puts everyone on real
tiles afterwards), armies cloned from a strat mate, and a minimal family.
Russia is re-seated: loses Novgorod (to the novgorod faction), gains Moscow
(from slave). Also extends the playable list and registers the factions in
descr_sm_factions (DLC blocks for the Kingdoms four, generated blocks for
the rest). Idempotent: skips factions whose sections already exist.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
STRAT = os.path.join(DATA, "world", "maps", "campaign", "imperial_campaign", "descr_strat.txt")
SMF = os.path.join(DATA, "descr_sm_factions.txt")
DLC = {
    "teutonic": os.path.join(ROOT, "research", "dlc-extract", "teutonic", "mods", "teutonic", "data"),
    "crusades": os.path.join(ROOT, "research", "dlc-extract", "crusades", "mods", "crusades", "data"),
}

# fac: (settlement region, current owner section, strat mate for armies,
#       leader, heir, diplomat, spy, wife, ai_label, denari, purse)
SPEC = {
    "teutonic_order": ("Thorn_Province", "slave", "hre",
                       "Heinrich Walpot", "Hermann", "Otto", "Konrad", "Adelheid",
                       "catholic", 6000, 2500),
    "lithuania": ("Vilnius_Province", "slave", "poland",
                  "Skirmantas", "Vykintas", "Daumantas", "Treniota", "Birute",
                  "default", 5000, 2000),
    "novgorod": ("Novgorod_Province", "russia", "russia",
                 "Mstislav", "Dobrynya", "Sadko", "Gavrilo", "Efrosinia",
                 "orthodox", 5000, 2000),
    "antioch": ("Antioch_Province", "slave", "france",
                "Bohemond", "Tancred", "Raymond", "Guy", "Alberada",
                "catholic", 7000, 3000),
    "sweden": ("Stockholm_Province", "slave", "denmark",
               "Inge", "Filip", "Ragnvald", "Sverker", "Helena",
               "catholic", 5000, 2000),
    "bohemia": ("Prague_Province", "slave", "hre",
                "Vratislav", "Bretislav", "Sobeslav", "Jaromir", "Svatava",
                "catholic", 5000, 2000),
    "aragon": ("Zaragoza_Province", "slave", "spain",
               "Sancho Ramirez", "Pedro", "Alfonso", "Ramiro", "Felicia",
               "catholic", 5000, 2000),
    "genoa": ("Genoa_Province", "milan", "milan",
              "Guglielmo Embriaco", "Ansaldo", "Caffaro", "Oberto", "Alda",
              "catholic", 6000, 2500),
    "pisa": ("Florence_Province", "slave", "milan",
             "Gerardo", "Ugo", "Lamberto", "Ildebrando", "Matilde",
             "catholic", 6000, 2500),
    "georgia": ("Tbilisi_Province", "slave", "byzantium",
                "Giorgi", "Davit", "Ivane", "Zakaria", "Tamar",
                "orthodox", 5000, 2000),
    "armenia": ("Adana_Province", "slave", "byzantium",
                "Ruben", "Kostandin", "Toros", "Levon", "Zabel",
                "orthodox", 5000, 2000),
    "kievan_rus": ("Kiev_Province", "slave", "russia",
                   "Vsevolod", "Vladimir Monomakh", "Sviatopolk", "Oleg", "Gytha",
                   "orthodox", 5000, 2000),
}
ORDER = ["teutonic_order", "lithuania", "novgorod", "antioch", "sweden",
         "bohemia", "aragon", "genoa", "pisa", "georgia", "armenia", "kievan_rus"]

DLC_SMF = {"teutonic_order": "teutonic", "lithuania": "teutonic",
           "novgorod": "teutonic", "antioch": "crusades"}

# generated descr_sm_factions blocks: (culture, religion, (r,g,b) primary, (r,g,b) secondary)
GEN_SMF = {
    "sweden": ("northern_european", "catholic", (15, 90, 190), (240, 200, 40)),
    "bohemia": ("northern_european", "catholic", (205, 30, 40), (240, 240, 240)),
    "aragon": ("southern_european", "catholic", (235, 185, 25), (180, 20, 25)),
    "genoa": ("southern_european", "catholic", (205, 25, 30), (245, 245, 245)),
    "pisa": ("southern_european", "catholic", (150, 20, 30), (240, 240, 240)),
    "georgia": ("greek", "orthodox", (225, 225, 225), (190, 25, 25)),
    "armenia": ("greek", "orthodox", (215, 95, 30), (30, 60, 140)),
    "kievan_rus": ("eastern_european", "orthodox", (35, 115, 205), (230, 180, 45)),
}


def read(p):
    return open(p, encoding="latin-1").read()


def write(p, t):
    with open(p, "w", encoding="latin-1", newline="\n") as f:
        f.write(t)


def extract_settlement(strat, region, owner):
    """cut the settlement block for `region` out of `owner`'s section."""
    o_start = strat.index(f"\nfaction\t{owner}")
    o_end = strat.find("\nfaction\t", o_start + 1)
    section = strat[o_start:o_end]
    block = None
    for m in re.finditer(r"^settlement[^\n]*\n\{.*?^\}\n", section, re.M | re.S):
        if f"region {region}" in m.group(0):
            block = m.group(0)
            break
    assert block, f"{region} not found in {owner} section"
    new_section = section.replace(block, "", 1)
    return strat[:o_start] + new_section + strat[o_end:], block


def mate_armies(strat, mate):
    """the mate leader's and heir's army blocks (unit lines only)."""
    m_start = strat.index(f"\nfaction\t{mate}")
    m_end = strat.find("\nfaction\t", m_start + 1)
    section = strat[m_start:m_end]
    armies = re.findall(r"^army\n((?:^unit[^\n]*\n)+)", section, re.M)
    lead = armies[0] if armies else ""
    heir = armies[1] if len(armies) > 1 else lead
    return lead, heir


def faction_section(fac, settlement_block, lead_army, heir_army):
    region, owner, mate, leader, heir, diplo, spy, wife, ai, denari, purse = SPEC[fac]
    settlement_block = re.sub(r"faction_creator\s+\w+", f"faction_creator {fac}",
                              settlement_block)
    lf, hf = leader.split(" ")[0], heir.split(" ")[0]
    return f"""faction\t{fac}, balanced smith
ai_label\t {ai}
denari\t{denari}
denari_kings_purse\t{purse}
{settlement_block}
character\t{leader}, named character, male, leader, age 42, x 0, y 0
traits Factionleader 1 , GoodCommander 1 , ReligionStarter 1
army
{lead_army}
character\t{heir}, named character, male, heir, age 20, x 0, y 0
traits Factionheir 1 , LoyaltyStarter 1
army
{heir_army}
character\t{diplo}, diplomat, male, age 30, x 0, y 0
traits GoodDiplomat 1

character\t{spy}, spy, male, age 25, x 0, y 0
traits GoodSpy 1

character_record\t\t{wife}, \tfemale, age 38, alive, never_a_leader

relative \t{leader}, \t{wife},\t\t{heir},\tend

"""


def dlc_smf_block(fac):
    text = read(os.path.join(DLC[DLC_SMF[fac]], "descr_sm_factions.txt"))
    m = re.search(rf"^(faction\s+{fac}\b.*?)(?=^faction\s)", text, re.M | re.S)
    assert m, fac
    block = m.group(1)
    # strat symbols/logos are re-pointed later by gen_heraldry/gen_standards/
    # gen_logos; loading logo path must be the shared convention
    block = re.sub(r"^loading_logo\s+\S+",
                   f"loading_logo\t\t\tloading_screen/symbols/symbol128_{fac}.tga",
                   block, count=1, flags=re.M)
    return block.rstrip() + "\n\n"


def gen_smf_block(fac):
    culture, religion, prim, sec = GEN_SMF[fac]
    return (f"faction\t\t\t\t\t\t{fac}\n"
            f"culture\t\t\t\t\t\t{culture}\n"
            f"religion\t\t\t\t\t{religion}\n"
            f"symbol\t\t\t\t\t\tmodels_strat/symbol_{fac}.cas\n"
            f"rebel_symbol\t\t\t\tmodels_strat/symbol_rebels.CAS\n"
            f"primary_colour\t\t\t\tred {prim[0]}, green {prim[1]}, blue {prim[2]}\n"
            f"secondary_colour\t\t\tred {sec[0]}, green {sec[1]}, blue {sec[2]}\n"
            f"loading_logo\t\t\t\tloading_screen/symbols/symbol128_{fac}.tga\n"
            f"standard_index\t\t\t\t20\n"
            f"logo_index\t\t\t\t\tFACTION_LOGO_{fac.upper()}\n"
            f"small_logo_index\t\t\tSMALL_FACTION_LOGO_{fac.upper()}\n"
            f"triumph_value\t\t\t\t5\n"
            f"custom_battle_availability\tyes\n"
            f"can_sap\t\t\t\t\t\tyes\n"
            f"prefers_naval_invasions\t\tno\n"
            f"can_have_princess\t\t\t\tyes\n"
            f"has_family_tree\t\t\t\t\tyes\n\n")


def main():
    strat = read(STRAT)
    smf = read(SMF)
    added = []
    for fac in ORDER:
        if re.search(rf"^faction\t{fac}\b", strat, re.M):
            continue
        region, owner, mate, *_ = SPEC[fac]
        strat, block = extract_settlement(strat, region, owner)
        lead_army, heir_army = mate_armies(strat, mate)
        section = faction_section(fac, block.rstrip() + "\n", lead_army, heir_army)
        # insert before the slave section
        idx = strat.index("\nfaction\tslave")
        strat = strat[:idx + 1] + section + strat[idx + 1:]
        added.append(fac)

    # russia re-seat: gains Moscow from slave (Novgorod already moved above)
    if "region Moscow_Province" not in strat.split("faction\trussia")[1].split("\nfaction\t")[0]:
        strat, moscow = extract_settlement(strat, "Moscow_Province", "slave")
        moscow = re.sub(r"faction_creator\s+\w+", "faction_creator russia", moscow)
        r_start = strat.index("\nfaction\trussia")
        insert_at = strat.index("\ncharacter", r_start)
        strat = strat[:insert_at + 1] + moscow.rstrip() + "\n\n" + strat[insert_at + 1:]

    # playable list
    for fac in ORDER:
        if not re.search(rf"^playable\n(?:\t\w+\n)*\t{fac}\n", strat, re.M):
            strat = re.sub(r"^(playable\n)", rf"\g<1>\t{fac}\n", strat, count=1, flags=re.M)

    write(STRAT, strat)

    for fac in ORDER:
        if re.search(rf"^faction\s+{fac}\b", smf, re.M):
            continue
        block = dlc_smf_block(fac) if fac in DLC_SMF else gen_smf_block(fac)
        idx = smf.index("faction\t\t\t\t\t\tslave")
        smf = smf[:idx] + block + smf[idx:]
    write(SMF, smf)

    n = len(re.findall(r"^faction\s", smf, re.M))
    print(f"strat factions: added {added or 'none (already present)'}; "
          f"sm_factions now {n} blocks")


if __name__ == "__main__":
    sys.exit(main() or 0)
