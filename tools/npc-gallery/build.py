#!/usr/bin/env python3
"""Build the NPC candidate gallery model: tools/npc-gallery/build/NpcGallery.rbxmx.

Pulls every humanoid rig from the sibling repos under ../ (gsclassic skins + NPCs,
Phoenix zone enemies + bosses, DungeonFall catalog enemies + NPCs), re-poses each one
from its joints into a clean standing rest pose, welds its accessories on, and lays
them all out on a stepped stadium of labelled pedestals grouped by source and
tier/zone. `npc-gallery.project.json` at the repo root wraps the output in a place.

    python tools/npc-gallery/build.py
    rojo build npc-gallery.project.json -o npc-gallery.rbxl

Stdlib only. Every rig is copied verbatim (meshes, textures, SharedStrings) and only
CFrames, joints, anchoring and a few cosmetic Humanoid fields are rewritten, so a
model dragged out of the gallery is a usable character.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.rigs import *  # noqa: E402,F401,F403 — the rig toolkit shared with tools/giants

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SIBLINGS = os.path.abspath(os.path.join(REPO, ".."))
OUT_DIR = os.path.join(HERE, "build")
OUT_MODEL = os.path.join(OUT_DIR, "NpcGallery.rbxmx")
OUT_MANIFEST = os.path.join(OUT_DIR, "manifest.md")
OUT_JSON = os.path.join(OUT_DIR, "manifest.json")

GSCLASSIC = os.path.join(SIBLINGS, "gsclassic")
PHOENIX = os.path.join(SIBLINGS, "Phoenix")
DUNGEONFALL = os.path.join(SIBLINGS, "DungeonFall")

MAX_DISPLAY_HEIGHT, DISPLAY_HEIGHT = 14.0, 12.0


# ---------------------------------------------------------------------------- exhibits
@dataclass
class Exhibit:
    name: str
    model: ET.Element
    source: str  # gsclassic | Phoenix | DungeonFall
    kind: str  # Skin | NPC | Enemy | Boss
    source_path: str
    meta: dict = field(default_factory=dict)  # tier, zone, bundle, game name, ...
    notes: list = field(default_factory=list)
    solved: SolvedRig | None = None
    ground: float = 0.0
    lo: list = field(default_factory=list)
    hi: list = field(default_factory=list)

    @property
    def width(self):
        return self.hi[0] - self.lo[0]

    @property
    def depth(self):
        return self.hi[2] - self.lo[2]

    @property
    def height(self):
        return self.hi[1] - self.ground

    def meta_line(self):
        bits = [self.source, self.kind]
        if "tier" in self.meta:
            bits.append(f"Tier {self.meta['tier']}")
        if "zone" in self.meta:
            bits.append(f"Zone {self.meta['zone']} {self.meta.get('size', '')}".strip())
        if self.meta.get("game_name"):
            bits.append(f"\"{self.meta['game_name']}\"")
        if self.meta.get("bundle"):
            bits.append(f"bundle {self.meta['bundle']}")
        if self.meta.get("stored_height"):
            bits.append(f"stored h {self.meta['stored_height']} → shown ×{self.meta['display_scale']:.3g}")
        else:
            bits.append(f"h {self.height:.1f}")
        if self.meta.get("also_in"):
            bits.append(f"also in {self.meta['also_in']}")
        return " · ".join(str(b) for b in bits)


def prepare(ex: Exhibit, hrp_attach_y=None):
    if hrp_attach_y is not None:
        synthesize_r15(ex.model, hrp_attach_y)
    unplaced = weld_accessories(ex.model)
    if unplaced:
        ex.notes.append("accessories left at saved offset: " + ", ".join(unplaced))
    ex.solved = solve_rig(ex.model)
    if ex.solved.unreached:
        ex.notes.append("parts not on the joint graph: " + ", ".join(sorted(set(ex.solved.unreached))))
    ex.ground, ex.lo, ex.hi = rig_bounds(ex.model, ex.solved)
    # Giant Simulator bosses and captured giant players are stored at 20-240 studs; shrink
    # them to gallery size so they can be judged next to everything else. The stored
    # height stays on the label and in the attributes.
    if ex.height > MAX_DISPLAY_HEIGHT:
        factor = DISPLAY_HEIGHT / ex.height
        ex.meta["stored_height"] = round(ex.height, 1)
        ex.meta["display_scale"] = round(factor, 4)
        scale_rig(ex.model, factor)
        ex.solved = solve_rig(ex.model)
        ex.ground, ex.lo, ex.hi = rig_bounds(ex.model, ex.solved)
    hip = None
    if hrp_attach_y is not None:
        hrp = ex.solved.root
        hip = (ex.solved.local_cf[hrp.get("referent")][1] - prop_size(hrp)[1] / 2) - ex.ground
    quiet_humanoid(ex.model, hip)
    write_ref(ex.model, "PrimaryPart", ex.solved.root.get("referent"))


# ---------------------------------------------------------------------------- collectors
def load_skin_meta():
    src = open(os.path.join(GSCLASSIC, "src/ReplicatedStorage/Aero/Shared/Skins.luau"), encoding="utf-8").read()
    meta = {}
    for dn, bid, rest in re.findall(r'\{\s*Name = \w+,\s*DisplayName = "([^"]+)",\s*BundleId = (\d+),(.*?)\}', src, re.S):
        t = re.search(r"Tier = (\d+)", rest)
        meta[dn] = {"bundle": int(bid), "tier": int(t.group(1)) if t else None}
    return meta


def load_phoenix_names():
    src = open(os.path.join(PHOENIX, "src/shared/Enemies.lua"), encoding="utf-8").read()
    names = {}
    for zm in re.finditer(r"\[(\d+)\]\s*=\s*\{(.*?)\n\t\},", src, re.S):
        for size, nm in re.findall(r'\[(\w+)Enemy\]\s*=\s*\{\s*Name\s*=\s*"([^"]+)"', zm.group(2)):
            names[(int(zm.group(1)), size)] = nm
    return names


def collect_dungeonfall():
    """All DungeonFall catalog rigs keyed by body-mesh set, plus the 4 workspace NPCs."""
    rigs = {}
    for f in sorted(glob.glob(os.path.join(DUNGEONFALL, "assets/enemies/*.rbxmx"))):
        sf = SourceFile.load(f)
        for m in sf.top_items():
            if m.get("class") == "Model":
                rigs[mesh_set(m)] = (m, sf)
    npcs = []
    for f in sorted(glob.glob(os.path.join(DUNGEONFALL, "assets/workspace/NPC/*.rbxmx"))):
        sf = SourceFile.load(f)
        for m in sf.top_items():
            if m.get("class") == "Model":
                npcs.append((m, sf))
    return rigs, npcs



def rel(path):
    return os.path.relpath(path, SIBLINGS).replace("\\", "/")


def build_exhibits():
    wings = []  # (letter, title, rgb, [(row title, [Exhibit])])
    skin_meta = load_skin_meta()
    df_rigs, df_npcs = collect_dungeonfall()
    df_used = set()

    # --- A: gsclassic skins, by tier -------------------------------------------------
    sf = SourceFile.load(os.path.join(GSCLASSIC, "assets/ReplicatedStorage/Skins.rbxmx"))
    skins_folder = sf.find(["Skins"])
    by_tier: dict[int, list] = {}
    for m in skins_folder.findall("Item"):
        nm = name_of(m)
        meta = dict(skin_meta.get(nm, {}))
        ms = mesh_set(m)
        twin = df_rigs.get(ms)
        attach_y = -0.7
        if twin is not None:
            meta["also_in"] = "DungeonFall"
            df_used.add(ms)
            attach_y = hrp_attach_y_of(twin[0]) or attach_y
        ex = Exhibit(nm, import_subtree(m, sf), "gsclassic", "Skin", rel(sf.path) + " › Skins › " + nm, meta)
        prepare(ex, hrp_attach_y=attach_y)
        by_tier.setdefault(meta.get("tier") or 0, []).append(ex)
    rows = [(f"Tier {t}" if t else "Unranked (effect bundles)", sorted(v, key=lambda e: e.meta.get("bundle", 0)))
            for t, v in sorted(by_tier.items(), key=lambda kv: kv[0] or 99)]
    wings.append(("A", "gsclassic · Skins (catalog bundles, by crate tier)", (60, 120, 220), rows))

    # --- B: gsclassic NPC rigs --------------------------------------------------------
    npc_rows = []
    for path, names, kind in [
        ("assets/ReplicatedStorage/NPC.rbxmx", ["NPC", "Borock"], "Boss"),
        ("assets/ServerStorage/NPC.rbxmx", ["NPC", "DemonKing"], "Boss"),
        ("assets/ServerStorage/NPC.rbxmx", ["NPC", "FireMage"], "NPC"),
        ("assets/ServerStorage/NPC.rbxmx", ["NPC", "FireBrute"], "NPC"),
        ("bec.rbxmx", ["bec"], "NPC"),
        ("golem.rbxmx", ["golem"], "NPC"),
    ]:
        sf = SourceFile.load(os.path.join(GSCLASSIC, path))
        m = sf.find(names)
        if m is None:
            print("  ! missing", path, names)
            continue
        ex = Exhibit(names[-1], import_subtree(m, sf), "gsclassic", kind, rel(sf.path) + " › " + " › ".join(names))
        if names[-1] in ("bec", "golem"):
            ex.meta["note"] = "captured player rig"
        prepare(ex)
        npc_rows.append(ex)
    wings.append(("B", "gsclassic · NPC / boss rigs", (150, 80, 220), [("NPC rigs", npc_rows)]))

    # --- C: Phoenix zone enemies + bosses ----------------------------------------------
    names = load_phoenix_names()
    sf = SourceFile.load(os.path.join(PHOENIX, "assets/ReplicatedStorage/EnemyPrefabs.rbxmx"))
    zone_rows = []
    order = ["Small", "Medium", "Large", "Huge"]
    for zone in sf.find(["EnemyPrefabs"]).findall("Item"):
        z = int(name_of(zone))
        exs = []
        for m in sorted(zone.findall("Item"), key=lambda m: order.index(name_of(m).replace("Enemy", ""))):
            size = name_of(m).replace("Enemy", "")
            game_name = names.get((z, size), "")
            ex = Exhibit(f"Z{z} {size} · {game_name}" if game_name else f"Z{z} {size}", import_subtree(m, sf), "Phoenix", "Enemy",
                         rel(sf.path) + f" › EnemyPrefabs › {z} › {name_of(m)}", {"zone": z, "size": size, "game_name": game_name})
            prepare(ex)
            exs.append(ex)
        zone_rows.append((f"Zone {z}", exs))
    boss_exs = []
    for path, names_, kind in [
        ("assets/ReplicatedStorage/BossPrefabs.rbxmx", ["Bosses", "WhiteBoss"], "Boss"),
        ("assets/ReplicatedStorage/TitanPrefab.rbxmx", ["TitanPrefab"], "NPC"),
    ]:
        sf2 = SourceFile.load(os.path.join(PHOENIX, path))
        m = sf2.find(names_)
        if m is None:
            print("  ! missing", path, names_)
            continue
        ex = Exhibit(names_[-1], import_subtree(m, sf2), "Phoenix", kind, rel(sf2.path) + " › " + " › ".join(names_))
        prepare(ex)
        boss_exs.append(ex)
    zone_rows.append(("Bosses / prefabs", boss_exs))
    wings.append(("C", "Phoenix · zone enemies (Small → Huge per zone) + bosses", (235, 140, 40), zone_rows))

    # --- D: DungeonFall extras (not already shown in A) + NPCs --------------------------
    extras = []
    for ms, (m, sf3) in df_rigs.items():
        if ms in df_used:
            continue
        nm = name_of(m).strip()
        ex = Exhibit(nm, import_subtree(m, sf3), "DungeonFall", "Enemy", rel(sf3.path))
        prepare(ex)
        extras.append(ex)
    extras.sort(key=lambda e: e.name.lower())
    per_row = 16
    df_rows = [(f"Catalog {i // per_row + 1}", extras[i:i + per_row]) for i in range(0, len(extras), per_row)]
    npc_exs = []
    for m, sf4 in df_npcs:
        ex = Exhibit(name_of(m), import_subtree(m, sf4), "DungeonFall", "NPC", rel(sf4.path))
        prepare(ex)
        npc_exs.append(ex)
    df_rows.append(("NPCs", npc_exs))
    wings.append(("D", "DungeonFall · catalog enemies not already in A, + NPCs", (70, 180, 110), df_rows))
    return wings


# ---------------------------------------------------------------------------- scene
def billboard(parent, lines, width, height, offset_y, max_dist, sizes):
    bb = make_item("BillboardGui", "Label", parent)
    write_udim2(bb, "Size", width, 0, height, 0)
    write_vec3(bb, "StudsOffsetWorldSpace", (0.0, offset_y, 0.0))
    set_prop(bb, "float", "MaxDistance", float(max_dist))
    set_prop(bb, "float", "LightInfluence", 0.0)
    set_prop(bb, "bool", "AlwaysOnTop", False)
    set_prop(bb, "bool", "ResetOnSpawn", False)
    y = 0.0
    for i, (text, frac) in enumerate(zip(lines, sizes)):
        tl = make_item("TextLabel", f"Line{i + 1}", bb)
        write_udim2(tl, "Size", 1, 0, frac, 0)
        write_udim2(tl, "Position", 0, 0, y, 0)
        set_prop(tl, "float", "BackgroundTransparency", 1.0)
        set_prop(tl, "string", "Text", text)
        set_prop(tl, "bool", "TextScaled", True)
        set_prop(tl, "bool", "TextWrapped", True)
        write_color3(tl, "TextColor3", (1.0, 1.0, 1.0) if i == 0 else (0.85, 0.9, 1.0))
        write_color3(tl, "TextStrokeColor3", (0.0, 0.0, 0.0))
        set_prop(tl, "float", "TextStrokeTransparency", 0.0)
        set_prop(tl, "token", "TextXAlignment", 2)
        font = ET.SubElement(props_of(tl), "Font", {"name": "FontFace"})
        fam = ET.SubElement(font, "Family")
        ET.SubElement(fam, "url").text = "rbxasset://fonts/families/GothamSSm.json"
        ET.SubElement(font, "Weight").text = "700" if i == 0 else "500"
        ET.SubElement(font, "Style").text = "Normal"
        y += frac
    return bb


def block(parent, name, size, cf, rgb, material=272, transparency=0.0):
    p = make_item("Part", name, parent)
    write_vec3(p, "size", size)
    write_cf(p, "CFrame", cf)
    write_part_color(p, rgb)
    set_prop(p, "token", "Material", material)
    set_prop(p, "bool", "Anchored", True)
    set_prop(p, "float", "Transparency", transparency)
    set_prop(p, "token", "TopSurface", 0)
    set_prop(p, "token", "BottomSurface", 0)
    return p


def build_scene(wings):
    gallery = make_item("Folder", "NpcGallery")
    readme = make_item("StringValue", "README", gallery)
    stage = make_item("Folder", "Stage", gallery)

    # Layout: rows run left→right along +X and step back (+Z) and up (+Y) like stadium
    # seating, so the whole library reads from the front. Characters face -Z, i.e. toward
    # the spawn point in front of the first row.
    PAD_X, PAD_Z, MIN_CELL = 3.0, 4.0, 8.0
    z_cursor, y_cursor = 0.0, 0.0
    max_row_width = 0.0
    manifest = []
    row_index = 0
    for letter, title, rgb, rows in wings:
        wing_folder = make_item("Folder", f"{letter} · {title}", gallery)
        first_row_of_wing = True
        for row_title, exhibits in rows:
            if not exhibits:
                continue
            row_folder = make_item("Folder", row_title, wing_folder)
            cell_w = max([MIN_CELL] + [e.width + PAD_X for e in exhibits])
            cell_d = max([MIN_CELL] + [e.depth + PAD_Z for e in exhibits])
            row_h = max(e.height for e in exhibits)
            row_w = cell_w * len(exhibits)
            max_row_width = max(max_row_width, row_w)
            riser_h = y_cursor + 1.0
            block(stage, f"Riser {row_index:02d} · {letter} · {row_title}", (row_w + 6.0, riser_h, cell_d),
                  cf_translate(row_w / 2, riser_h / 2, z_cursor + cell_d / 2), (52, 54, 60), 800)
            top_y = riser_h
            # Row label on the left shoulder of the riser.
            marker = block(stage, f"RowLabel {row_index:02d}", (1.0, 1.0, 1.0),
                           cf_translate(-4.0, top_y + 0.5, z_cursor + cell_d / 2), rgb, 288)
            billboard(marker, [f"{letter} · {row_title}", f"{len(exhibits)} rigs"], 14, 3.5, 4.0, 400, [0.6, 0.4])
            if first_row_of_wing:
                banner = block(stage, f"WingBanner {letter}", (1.0, 1.0, 1.0),
                               cf_translate(row_w / 2, top_y + row_h + 10.0, z_cursor + cell_d / 2), rgb, 288, 1.0)
                billboard(banner, [f"{letter} — {title}", f"{sum(len(r[1]) for r in rows)} rigs"], 60, 8, 0.0, 1500, [0.65, 0.35])
                first_row_of_wing = False
            for i, ex in enumerate(exhibits):
                cx = cell_w * i + cell_w / 2
                cz = z_cursor + cell_d / 2
                exhibit = make_item("Model", ex.name, row_folder)
                pedestal = block(exhibit, "Pedestal", (cell_w - 1.5, 1.0, cell_d - 1.5),
                                 cf_translate(cx, top_y + 0.5, cz), rgb, 272)
                billboard(pedestal, [ex.name, ex.meta_line()], max(cell_w - 0.5, 9.0), 3.0,
                          ex.height + 0.5 + 2.2, 220, [0.55, 0.45])
                ground_y = top_y + 1.0
                # Centre the rig's footprint on the pedestal (weapons/wings make it off-centre).
                offx = -(ex.lo[0] + ex.hi[0]) / 2
                offz = -(ex.lo[2] + ex.hi[2]) / 2
                place_rig(ex.model, ex.solved, cf_translate(cx + offx, ground_y - ex.ground, cz + offz))
                set_attributes(ex.model, {
                    "Source": ex.source, "Kind": ex.kind, "SourcePath": ex.source_path,
                    "OriginalName": name_of(ex.model),
                    "Height": round(ex.height, 2), "Width": round(ex.width, 2),
                    **{k.title(): v for k, v in ex.meta.items() if v not in (None, "")},
                    **({"Notes": "; ".join(ex.notes)} if ex.notes else {}),
                })
                if name_of(ex.model) != ex.name:
                    set_prop(ex.model, "string", "Name", ex.name)
                exhibit.append(ex.model)
                write_ref(exhibit, "PrimaryPart", pedestal.get("referent"))
                manifest.append({
                    "wing": letter, "row": row_title, "name": ex.name, "source": ex.source, "kind": ex.kind,
                    "source_path": ex.source_path, "height": round(ex.height, 2), "width": round(ex.width, 2),
                    **ex.meta, "notes": ex.notes,
                    "position": [round(cx, 1), round(ground_y, 1), round(cz, 1)],
                })
            z_cursor += cell_d
            y_cursor += max(3.0, 0.45 * row_h)
            row_index += 1

    # Floor and spawn in front of the first row, looking at the stage.
    floor_w = max_row_width + 80
    block(stage, "Floor", (floor_w, 2.0, z_cursor + 120), cf_translate(max_row_width / 2, -1.0, z_cursor / 2 - 20), (110, 140, 90), 1280)
    spawn = make_item("SpawnLocation", "Spawn", stage)
    write_vec3(spawn, "size", (12.0, 1.0, 12.0))
    write_cf(spawn, "CFrame", cf_yaw180(max_row_width / 2, 0.5, -45.0))
    write_part_color(spawn, (200, 200, 200))
    set_prop(spawn, "bool", "Anchored", True)
    set_prop(spawn, "bool", "Neutral", True)
    set_prop(spawn, "int", "Duration", 0)
    set_prop(spawn, "token", "TopSurface", 0)
    set_prop(spawn, "token", "BottomSurface", 0)

    readme_text = (
        "NPC candidate gallery for Push a Giant — generated by tools/npc-gallery/build.py; do not edit by hand.\n\n"
        "Every rig here was copied from a sibling repo, re-posed from its joints into a rest pose, anchored, and set\n"
        "on a labelled pedestal. Wings run front to back: A gsclassic skins (by crate tier), B gsclassic NPC/boss rigs,\n"
        "C Phoenix zone enemies (Small→Huge per zone) + bosses, D DungeonFall catalog rigs not already in A, + NPCs.\n"
        "Each exhibit Model = Pedestal + the character Model; the character carries attributes (Source, SourcePath,\n"
        "Tier/Zone/Bundle, Height...) — select it and open the Attributes section of Properties. To take one, right-click\n"
        "the character Model → Save to File (or copy/paste into another place). The full list is in\n"
        "tools/npc-gallery/build/manifest.md.\n"
    )
    set_prop(readme, "string", "Value", readme_text)
    return gallery, manifest


def write_model(gallery):
    root = ET.Element("roblox", {"version": "4"})
    ET.SubElement(root, "Meta", {"name": "ExplicitAutoJoints"}).text = "true"
    root.append(gallery)
    ss = ET.SubElement(root, "SharedStrings")
    for key, val in SHARED_OUT.items():
        ET.SubElement(ss, "SharedString", {"md5": key}).text = val
    os.makedirs(OUT_DIR, exist_ok=True)
    ET.ElementTree(root).write(OUT_MODEL, encoding="utf-8", xml_declaration=False)


def write_manifest(wings, manifest):
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
    lines = ["# NPC gallery manifest", "", f"{len(manifest)} rigs. Generated by `tools/npc-gallery/build.py`.", ""]
    for letter, title, _, rows in wings:
        lines += [f"## {letter} — {title}", ""]
        for row_title, exhibits in rows:
            if not exhibits:
                continue
            lines += [f"### {row_title} ({len(exhibits)})", "", "| # | Name | Kind | Height | Meta | Source | Notes |", "|---|---|---|---|---|---|---|"]
            for i, ex in enumerate(exhibits, 1):
                meta = ", ".join(f"{k}={v}" for k, v in ex.meta.items() if v not in (None, "") and k != "also_in")
                if ex.meta.get("also_in"):
                    meta += f" (also in {ex.meta['also_in']})"
                lines.append(f"| {i} | {ex.name} | {ex.kind} | {ex.height:.1f} | {meta} | `{ex.source_path}` | {'; '.join(ex.notes)} |")
            lines.append("")
    with open(OUT_MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (GSCLASSIC, PHOENIX, DUNGEONFALL):
        if not os.path.isdir(p):
            sys.exit(f"missing sibling repo: {p}")
    print("collecting rigs...")
    wings = build_exhibits()
    gallery, manifest = build_scene(wings)
    print("writing", OUT_MODEL)
    write_model(gallery)
    write_manifest(wings, manifest)
    total = 0
    for letter, title, _, rows in wings:
        n = sum(len(r[1]) for r in rows)
        total += n
        print(f"  {letter}  {n:3d}  {title}")
        for row_title, exhibits in rows:
            print(f"        {len(exhibits):3d}  {row_title}")
    print(f"total {total} rigs; {len(SHARED_OUT)} shared strings; {os.path.getsize(OUT_MODEL) / 1e6:.1f} MB")
    noted = [m for m in manifest if m["notes"]]
    if noted:
        print(f"{len(noted)} rigs with notes (see manifest.md):")
        for m in noted:
            print("   -", m["name"], "|", "; ".join(m["notes"]))


if __name__ == "__main__":
    main()
