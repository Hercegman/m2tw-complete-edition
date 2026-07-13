#!/usr/bin/env python3
"""Extend the Grand Campaign faction-select screen with more symbol slots.

The vanilla ImpCam_choose_faction lpage in data/menu/mtw2.lnt has exactly 21
CFP_symbol48_N slots (17 in the main row at y=110, 4 corner slots at y=50) —
that's why only 21 factions ever show in the selector. The top row between
x=153 and x=872 is empty, which fits 12 more 59px slots at the vanilla 60px
pitch -> 33 total.

Reads the vanilla layout from research/base-extract, writes the extended one
to the mod. Re-runnable.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "research", "base-extract", "data", "menu", "mtw2.lnt")
DST = os.path.join(ROOT, "mod", "complete_edition", "data", "menu", "mtw2.lnt")

NEW_SLOTS = [(x, 50) for x in range(153, 813 + 1, 60)]  # 12 slots

TEMPLATE = """    <UI piece>CFP_symbol48_{n}
      <identifier>UIP_CAMPAIGN_FACTION_SELECT</identifier>
      <Parameters>
        <x>{x}</x>
        <y>{y}</y>
        <width>59</width>
        <height>59</height>
        <tool_tip_id>UI_FACTIONS_SELECT_FACTION_INFO</tool_tip_id>
        <locked>false</locked>
      </Parameters>
      <object_data></object_data>
      <object_id>empty_art</object_id>
      <edit_group_id>symbols</edit_group_id>
    </UI piece>
"""


def main():
    text = open(SRC, encoding="latin-1").read()
    i = text.find("<lpage>ImpCam_choose_faction")
    j = text.find("</lpage>", i)
    page = text[i:j]
    count = page.count("CFP_symbol48_")
    assert count == 21, f"expected 21 vanilla slots, found {count}"

    # insert new slots right after the last existing slot block
    m = None
    for m in re.finditer(r"    <UI piece>CFP_symbol48_\d+\n.*?</UI piece>\n", page, re.S):
        pass
    insert_at = i + m.end()
    new_blocks = "".join(
        TEMPLATE.format(n=22 + k, x=x, y=y) for k, (x, y) in enumerate(NEW_SLOTS))
    out = text[:insert_at] + new_blocks + text[insert_at:]

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w", encoding="latin-1", newline="") as f:
        f.write(out)
    total = 21 + len(NEW_SLOTS)
    print(f"mtw2.lnt: GC selector extended to {total} slots -> {DST}")


if __name__ == "__main__":
    main()
