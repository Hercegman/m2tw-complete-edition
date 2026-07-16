#!/usr/bin/env python3
"""Give every new faction proper battle-model textures via M2EX's text route.

Why: battle_models.modeldb lists per-unit faction textures; a faction with no
entry gets the generic `peasants` placeholder model (the "knife-men" bug).
Instead of editing the binary modeldb, M2EX can parse a full plain-text
`descr_model_battle.txt` when the mod ships `descr_caps_ex.txt` with
`model_battle_source text`. M2EX ships a complete 701-unit dump of the base
modeldb; we append per-faction `texture` / `texture_attachments` lines cloned
from a donor faction (paths and sprites stay the donor's — the same mechanism
vanilla uses for normans -> england textures).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "mod", "complete_edition", "data")
SRC_DMB = os.path.join(ROOT, "research", "m2ex-extract", "descr_model_battle.txt")
EDU = os.path.join(DATA, "export_descr_unit.txt")

# donor priority per new faction; first donor with a texture line in the
# model's entry wins
DONORS = {
    "croatia": ["hungary", "russia", "poland", "slave"],
    "wallachia": ["hungary", "russia", "poland", "slave"],
    "serbia": ["byzantium", "hungary", "russia", "slave"],
    "bulgaria": ["byzantium", "hungary", "russia", "slave"],
    "ragusa": ["venice", "sicily", "slave"],
    "wales": ["england", "scotland", "slave"],
    "ireland": ["scotland", "england", "slave"],
    "norway": ["denmark", "england", "slave"],
    "jerusalem": ["france", "england", "slave"],
}


def edu_model_factions():
    """battle model (lowercased) -> set of new factions owning a unit that
    uses it. Covers `soldier`, `officer` and `armour_ug_models` — all of
    which resolve through the model database (mounts go via descr_mount)."""
    text = open(EDU, encoding="latin-1").read()
    need = {}
    models = set()
    for line in text.split("\n"):
        m = re.match(r"^soldier\s+([\w-]+)\s*,", line)
        if m:
            models.add(m.group(1).lower())
            continue
        m = re.match(r"^officer\s+([\w-]+)\s*$", line.strip())
        if m:
            models.add(m.group(1).lower())
            continue
        m = re.match(r"^armour_ug_models\s+(.*)$", line)
        if m:
            models.update(x.strip().lower() for x in m.group(1).split(",") if x.strip())
            continue
        m = re.match(r"^ownership\s+(.*)$", line)
        if m and models:
            owners = {o.strip().lower() for o in m.group(1).split(",")}
            newbies = owners & set(DONORS)
            if newbies:
                for mdl in models:
                    need.setdefault(mdl, set()).update(newbies)
            models = set()
    return need


def main():
    need = edu_model_factions()
    src = open(SRC_DMB, encoding="latin-1").read()
    lines = src.split("\n")

    out = []
    cur_type = None
    tex_lines = {}      # faction -> line, for current entry
    att_lines = {}
    added = 0
    skipped = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^type\s+([\w-]+)\s*$", line)
        if m:
            cur_type = m.group(1).lower()
            tex_lines, att_lines = {}, {}
            out.append(line)
            i += 1
            continue
        m = re.match(r"^texture\s+(\w+)\s*,", line)
        if m:
            tex_lines.setdefault("__first__", line)
            tex_lines[m.group(1).lower()] = line
            # texture block ends when the next line is not a texture line —
            # insert clones right after the last texture line so ordering
            # stays grouped
            if i + 1 >= n or not re.match(r"^texture\s+\w+\s*,", lines[i + 1]):
                out.append(line)
                for fac in sorted(need.get(cur_type, ())):
                    if fac in tex_lines:
                        continue
                    donor = next((d for d in DONORS[fac] if d in tex_lines), None)
                    if donor is None:
                        # any real texture beats the knife-peasant fallback
                        donor = "__first__"
                        skipped.append((cur_type, fac))
                    out.append(re.sub(r"^(texture\s+)\w+", rf"\g<1>{fac}",
                                      tex_lines[donor], count=1))
                    added += 1
                i += 1
                continue
        m = re.match(r"^texture_attachments\s+(\w+)\s*,", line)
        if m:
            att_lines.setdefault("__first__", line)
            att_lines[m.group(1).lower()] = line
            if i + 1 >= n or not re.match(r"^texture_attachments\s+\w+\s*,", lines[i + 1]):
                out.append(line)
                for fac in sorted(need.get(cur_type, ())):
                    if fac in att_lines:
                        continue
                    donor = next((d for d in DONORS[fac] if d in att_lines), "__first__")
                    out.append(re.sub(r"^(texture_attachments\s+)\w+", rf"\g<1>{fac}",
                                      att_lines[donor], count=1))
                i += 1
                continue
        out.append(line)
        i += 1

    with open(os.path.join(DATA, "descr_model_battle.txt"), "w",
              encoding="latin-1", newline="\n") as f:
        f.write("\n".join(out))

    caps = os.path.join(DATA, "descr_caps_ex.txt")
    with open(caps, "w", encoding="latin-1", newline="\n") as f:
        f.write("; Complete Edition - M2EX engine toggles.\n"
                "; model_battle_source text: parse descr_model_battle.txt directly\n"
                ";   instead of the binary battle_models.modeldb (which has no\n"
                ";   entries for our factions).\n"
                "; sprite_format stays on the default binary sd: the mod ships\n"
                ";   patched ui/strategy.sd + ui/shared.sd with the new factions'\n"
                ";   crest sprites (the xml route broke the registry in mod scope).\n"
                "model_battle_source  text\n")

    # coverage check: every needed EDU soldier model must exist in the dump
    missing_models = [mdl for mdl in need
                      if not re.search(rf"^type\s+{re.escape(mdl)}\s*$", src, re.M | re.I)]
    print(f"descr_model_battle: {added} texture lines added across "
          f"{len(need)} models; {len(skipped)} used first-line fallback {skipped[:5]}")
    if missing_models:
        print(f"  WARNING: {len(missing_models)} EDU soldier models absent from "
              f"the base dump: {missing_models[:10]}")
    return 1 if missing_models else 0


if __name__ == "__main__":
    sys.exit(main())
