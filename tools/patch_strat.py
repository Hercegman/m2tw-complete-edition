"""
Patch descr_strat.txt for Croatia Overhaul mod:
1. Remove Ragusa from Venice faction
2. Remove Zagreb from slave faction
3. Remove Sofia from slave faction
4. Add Croatia, Bosnia, Serbia faction blocks before slave
"""

import re

strat_path = r"C:\Program Files (x86)\Steam\steamapps\common\Medieval II Total War\mods\croatia_overhaul\data\world\maps\campaign\imperial_campaign\descr_strat.txt"

with open(strat_path, 'r', encoding='utf-8') as f:
    content = f.read()

original_len = len(content)

# ============================================================
# 1. REMOVE RAGUSA CASTLE from Venice faction
# ============================================================
# Find and remove the Ragusa settlement castle block within Venice
ragusa_block = """
settlement castle
{
\tlevel large_town
\tregion Ragusa_Province

\tyear_founded 0
\tpopulation 1500
\tplan_set default_set
\tfaction_creator venice
\tbuilding
\t{
\t\ttype core_castle_building castle
\t}
\tbuilding
\t{
\t\ttype equestrian stables
\t}
\tbuilding
\t{
\t\ttype castle_port c_port
\t}
\tbuilding
\t{
\t\ttype castle_barracks mustering_hall
\t}
\tbuilding
\t{
\t\ttype hinterland_castle_roads c_roads
\t}
}"""

if ragusa_block in content:
    content = content.replace(ragusa_block, '', 1)
    print("OK: Removed Ragusa from Venice")
else:
    print("WARN: Ragusa block not found in Venice - check manually!")
    # Try to find it
    idx = content.find('Ragusa_Province')
    if idx != -1:
        print(f"  Ragusa_Province found at pos {idx}: {content[idx-50:idx+200]!r}")

# ============================================================
# 2. REMOVE ZAGREB VILLAGE from slave faction
# ============================================================
zagreb_block = """
settlement
{
\tlevel village
\tregion Zagreb_Province

\tyear_founded 0
\tpopulation 800
\tplan_set default_set
\tfaction_creator spain
}"""

if zagreb_block in content:
    content = content.replace(zagreb_block, '', 1)
    print("OK: Removed Zagreb from slave")
else:
    print("WARN: Zagreb block not found in slave!")
    idx = content.find('Zagreb_Province')
    if idx != -1:
        print(f"  Zagreb_Province found at pos {idx}: {content[idx-50:idx+200]!r}")

# ============================================================
# 3. REMOVE SOFIA CASTLE from slave faction
# ============================================================
sofia_block = """
settlement castle
{
\tlevel town
\tregion Sofia_Province

\tyear_founded 0
\tpopulation 2200
\tplan_set default_set
\tfaction_creator russia
\tbuilding
\t{
\t\ttype core_castle_building wooden_castle
\t}
}"""

if sofia_block in content:
    content = content.replace(sofia_block, '', 1)
    print("OK: Removed Sofia from slave")
else:
    print("WARN: Sofia block not found in slave!")
    idx = content.find('Sofia_Province')
    if idx != -1:
        print(f"  Sofia_Province found at pos {idx}: {content[idx-50:idx+200]!r}")

# ============================================================
# 4. ADD CROATIA, BOSNIA, SERBIA faction blocks before slave
# ============================================================

new_factions = """

faction\tcroatia, balanced smith
ai_label\t catholic
denari\t5000
denari_kings_purse\t2500
settlement
{
\tlevel town
\tregion Zagreb_Province

\tyear_founded 0
\tpopulation 2200
\tplan_set default_set
\tfaction_creator croatia
\tbuilding
\t{
\t\ttype core_building wooden_pallisade
\t}
\tbuilding
\t{
\t\ttype barracks town_watch
\t}
\tbuilding
\t{
\t\ttype hinterland_roads roads
\t}
}

character\tDmitar Zvonimir, named character, male, leader, age 45, x 157, y 115
traits Factionleader 1 , GoodCommander 2 , NaturalMilitarySkill 2 , BattleChivalry 3 , PublicFaith 2 , ReligionStarter 1
ancillaries apothecary
army
unit\t\tEE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tMagyar Cavalry\t\t\t\texp 0 armour 0 weapon_lvl 0

character\tStjepan, named character, male, heir, age 22, x 159, y 114
traits Factionheir 1 , LoyaltyStarter 1 , BattleChivalry 2 , GoodCommander 1 , ReligionStarter 1
army
unit\t\tEE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0

character\tPetar, diplomat, male, age 28, x 156, y 116
traits GoodDiplomat 2

character\tMiroslav, spy, male, age 24, x 160, y 113
traits GoodSpy 2

character_record\t\tHelena, \tfemale, age 42, alive, never_a_leader

relative \tDmitar Zvonimir, \tHelena,\t\tStjepan,\tend


faction\tbosnia, balanced smith
ai_label\t catholic
denari\t4500
denari_kings_purse\t2000
settlement castle
{
\tlevel large_town
\tregion Ragusa_Province

\tyear_founded 0
\tpopulation 1500
\tplan_set default_set
\tfaction_creator bosnia
\tbuilding
\t{
\t\ttype core_castle_building castle
\t}
\tbuilding
\t{
\t\ttype castle_port c_port
\t}
\tbuilding
\t{
\t\ttype castle_barracks mustering_hall
\t}
}

character\tKulina Ban, named character, male, leader, age 40, x 157, y 121
traits Factionleader 1 , GoodCommander 1 , NaturalMilitarySkill 1 , PoliticsSkill 2 , GoodAdministrator 1 , ReligionStarter 1
ancillaries apothecary
army
unit\t\tEE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0

character\tNinoslav, named character, male, heir, age 20, x 158, y 122
traits Factionheir 1 , LoyaltyStarter 1 , BattleChivalry 1 , ReligionStarter 1
army
unit\t\tEE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0

character_record\t\tMara, \tfemale, age 38, alive, never_a_leader

relative \tKulina Ban, \tMara,\t\tNinoslav,\tend


faction\tserbia, balanced smith
ai_label\t orthodox
denari\t4500
denari_kings_purse\t2000
settlement castle
{
\tlevel town
\tregion Sofia_Province

\tyear_founded 0
\tpopulation 2200
\tplan_set default_set
\tfaction_creator serbia
\tbuilding
\t{
\t\ttype core_castle_building wooden_castle
\t}
\tbuilding
\t{
\t\ttype castle_barracks mustering_hall
\t}
}

character\tVukan, named character, male, leader, age 42, x 185, y 130
traits Factionleader 1 , GoodCommander 2 , NaturalMilitarySkill 2 , BattleChivalry 2 , PublicFaith 2 , ReligionStarter 1
ancillaries apothecary
army
unit\t\tEE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tMagyar Cavalry\t\t\t\texp 0 armour 0 weapon_lvl 0

character\tNemanja, named character, male, heir, age 20, x 186, y 131
traits Factionheir 1 , LoyaltyStarter 1 , BattleChivalry 2 , NaturalMilitarySkill 1 , ReligionStarter 1
army
unit\t\tEE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tEE Spear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0
unit\t\tBosnian Archers\t\t\t\texp 0 armour 0 weapon_lvl 0

character\tMilica, diplomat, female, age 25, x 183, y 129
traits GoodDiplomat 1

character_record\t\tMileva, \tfemale, age 40, alive, never_a_leader

relative \tVukan, \tMileva,\t\tNemanja,\tend

"""

# Insert before slave faction
slave_marker = "\nfaction\tslave, balanced smith\n"
if slave_marker in content:
    content = content.replace(slave_marker, new_factions + slave_marker, 1)
    print("OK: Added Croatia, Bosnia, Serbia faction blocks")
else:
    print("WARN: Could not find slave faction marker!")
    # Try to find it
    idx = content.find('slave, balanced smith')
    if idx != -1:
        print(f"  Found 'slave, balanced smith' at pos {idx}")
        print(f"  Context: {content[idx-5:idx+50]!r}")

# Write modified file
with open(strat_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nFile size: {original_len} -> {len(content)} bytes (+{len(content)-original_len})")
print("Done!")
