#!/usr/bin/env python3
"""Import the chosen giant rigs from the sibling repos into assets/ServerStorage/Giants/.

    python tools/giants/import_giants.py

Each entry in ROSTER names a source rig (Phoenix zone enemy or DungeonFall character),
copies it out of the sibling repo, normalises it into one consistent R15 character, and
writes `assets/ServerStorage/Giants/<Id>.rbxm` (binary, via lune) plus
`docs/giants-roster.md`. Rojo maps that folder to ServerStorage.Giants.

What "normalised" means, so every giant animates and behaves the same way:
- R15 rig: the 15 body parts + HumanoidRootPart, all 15 Motor6Ds rebuilt from the rig
  attachments (Part0/Part1/C0/C1), Humanoid with a fresh Animator, PrimaryPart = HRP.
- Accessories welded to their attachment pairs (AccessoryWeld), weapon trails disabled.
- Base scale 1x: the rig is shrunk exactly as `Model:ScaleTo` would (sizes, offsets,
  HipHeight and the Humanoid's width/height/depth/head scale values, which end at 1). At
  runtime the game sizes a giant with `Model:ScaleTo(k)` (layered clothing only keeps
  fitting when the model's ScaleFactor carries the size) and, because the Animator then
  applies the scale a second time, divides every Motor6D.Transform translation by the
  model's scale on RunService.Stepped — see `scaleGiant` in preview.luau, the reference
  implementation. The source scale is kept in the `SourceScale` attribute. The engine's avatar-scaling bookkeeping (OriginalSize,
  OriginalPosition, AvatarPartScaleType, BodyTypeScale, BodyProportionScale) is kept:
  layered clothing does not fit without it. Layered-clothing (WrapLayer) handles keep
  their mesh's native size, exactly as ScaleTo leaves them; the garment is fitted to the
  body's cages rather than sized with the body.
- Rest pose re-solved from the joints, HRP at the origin, feet on y = 0, unanchored,
  HipHeight recomputed from the geometry.
- Stripped: scripts, animation-editor leftovers (AnimSaves), HumanoidDescription,
  character sounds.
- Attributes on the model: DisplayName, Source, SourcePath, SourceScale, SourceSize,
  Zone, Height (body height in studs at 1x), RosterIndex (progression order).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.rigs import *  # noqa: E402,F401,F403

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SIBLINGS = os.path.abspath(os.path.join(REPO, ".."))
PHOENIX = os.path.join(SIBLINGS, "Phoenix")
DUNGEONFALL = os.path.join(SIBLINGS, "DungeonFall")
STAGE_DIR = os.path.join(HERE, "build")  # intermediate .rbxmx, gitignored
OUT_DIR = os.path.join(REPO, "assets", "ServerStorage", "Giants")
ROSTER_DOC = os.path.join(REPO, "docs", "giants-roster.md")

PREVIEW_SOURCE_IDS = {"Baron", "DesertGeneral", "CyberLord", "IceKing", "WinterAssassin", "SandMage", "Noob"}  # stood behind their prefabs in the preview



def phoenix(zone: int, size: str):
    return {"repo": "Phoenix", "zone": zone, "size": size}


def dungeonfall(subdir: str, filename: str):
    return {"repo": "DungeonFall", "path": f"assets/{subdir}/{filename}"}


# (Id, display name, source). Order = rough progression order; Ids become the model
# names under ServerStorage.Giants. Phoenix display names are checked against the
# source game's Enemies.lua so a zone/size typo cannot import the wrong rig.
ROSTER = [
    ("Noob", "Noob", phoenix(1, "Small")),
    ("Goblin", "Goblin", phoenix(1, "Medium")),
    ("Viking", "Viking", phoenix(1, "Large")),
    ("Baron", "Baron", phoenix(1, "Huge")),
    ("Peasant", "Peasant", phoenix(2, "Small")),
    ("SunGladiator", "Sun Gladiator", phoenix(2, "Medium")),
    ("SandMage", "Sand Mage", phoenix(2, "Large")),
    ("DesertGeneral", "Desert General", phoenix(2, "Huge")),
    ("WinterAssassin", "Winter Assassin", phoenix(3, "Small")),
    ("FrostMage", "Frost Mage", phoenix(3, "Medium")),
    ("IceKing", "Ice King", phoenix(3, "Large")),
    ("ForestTroll", "Forest Troll", phoenix(4, "Medium")),
    ("LeafNinja", "Leaf Ninja", phoenix(4, "Large")),
    ("DemonNinja", "Demon Ninja", phoenix(5, "Small")),
    ("ChaosMage", "Chaos Mage", phoenix(5, "Medium")),
    ("ChaosSummoner", "Chaos Summoner", phoenix(5, "Large")),
    ("FireTroll", "Fire Troll", phoenix(6, "Small")),
    ("RedOrc", "Red Orc", phoenix(6, "Medium")),
    ("DoomBoss", "Doom Boss", phoenix(6, "Huge")),
    ("CyberLord", "Cyber Lord", phoenix(7, "Huge")),
    ("FeatherweightChamp", "Brawk Tyson: Featherweight Champ", dungeonfall("enemies", "Brawk Tyson Featherweight Champ.rbxmx")),
    ("BuffNoob", "Buffnoob", dungeonfall("enemies", "Buffnoob.rbxmx")),
    ("Commander", "Commander", dungeonfall("workspace/NPC", "Commander.rbxmx")),
    ("Knight", "Knight", dungeonfall("workspace/NPC", "Knight.rbxmx")),
    ("Mage", "Mage", dungeonfall("workspace/NPC", "Mage.rbxmx")),
    ("Archer", "Archer", dungeonfall("workspace/NPC", "Archer.rbxmx")),
]


# ---------------------------------------------------------------------------- sources
def load_phoenix_names():
    src = open(os.path.join(PHOENIX, "src/shared/Enemies.lua"), encoding="utf-8").read()
    names = {}
    for zm in re.finditer(r"\[(\d+)\]\s*=\s*\{(.*?)\n\t\},", src, re.S):
        for size, nm in re.findall(r'\[(\w+)Enemy\]\s*=\s*\{\s*Name\s*=\s*"([^"]+)"', zm.group(2)):
            names[(int(zm.group(1)), size)] = nm
    return names


def locate(source, phoenix_names):
    """(source Item, SourceFile, repo-relative path string, extra meta)."""
    if source["repo"] == "Phoenix":
        path = os.path.join(PHOENIX, "assets/ReplicatedStorage/EnemyPrefabs.rbxmx")
        sf = SourceFile.load(path)
        item = sf.find(["EnemyPrefabs", str(source["zone"]), f"Enemy{source['size']}"])
        game_name = phoenix_names.get((source["zone"], source["size"]))
        return item, sf, f"Phoenix/assets/ReplicatedStorage/EnemyPrefabs.rbxmx › {source['zone']} › Enemy{source['size']}", {
            "Zone": source["zone"], "SourceSize": source["size"], "game_name": game_name,
        }
    path = os.path.join(DUNGEONFALL, source["path"])
    sf = SourceFile.load(path)
    item = next((m for m in sf.top_items() if m.get("class") == "Model"), None)
    return item, sf, "DungeonFall/" + source["path"], {}


# ---------------------------------------------------------------------------- normalise
def remove_matching(model, predicate):
    """Delete every descendant Item for which predicate(item, parent) is true."""
    for parent in list(model.iter("Item")):
        for child in list(parent.findall("Item")):
            if predicate(child, parent):
                parent.remove(child)


def humanoid_of(model):
    return next((c for c in model.findall("Item") if c.get("class") == "Humanoid"), None)


def source_scale(model) -> float:
    hum = humanoid_of(model)
    if hum is None:
        return 1.0
    for v in hum.findall("Item"):
        if v.get("class") == "NumberValue" and name_of(v) == "BodyHeightScale":
            e = get_prop(v, "Value")
            return float(e.text) if e is not None else 1.0
    return 1.0


def normalise(model, giant_id: str) -> dict:
    """Turn a copied source rig into a Push a Giant prefab in place; returns stats."""
    parts = {name_of(p): p for p in model.findall("Item") if p.get("class") in BASEPART_CLASSES}
    missing = [n for n in R15_PARTS + ["HumanoidRootPart"] if n not in parts]
    if missing:
        raise SystemExit(f"{giant_id}: source rig is missing {missing}")
    scale = source_scale(model)

    # Leftovers from the source games: editor animation saves, character sounds, the
    # stale HumanoidDescription. The avatar-scaling bookkeeping (OriginalSize,
    # OriginalPosition, AvatarPartScaleType, the Humanoid's Body*Scale values) stays:
    # stripping it breaks layered-clothing fitting (found by bisecting in-engine).
    remove_matching(model, lambda c, p: c.get("class") == "Model" and not any(x.get("class") in BASEPART_CLASSES for x in c.iter("Item")))
    remove_matching(model, lambda c, p: c.get("class") in ("Sound", "HumanoidDescription"))
    remove_matching(model, lambda c, p: c.get("class") == "Motor6D" and p.get("referent") in {x.get("referent") for x in parts.values()} and name_of(c) not in {j for j, _, _ in R15_JOINTS})
    for trail in model.iter("Item"):
        if trail.get("class") == "Trail":
            set_prop(trail, "bool", "Enabled", False)

    synthesize_r15(model, hrp_attach_y=None)  # HRP exists: rewires the 15 joints only
    unplaced = weld_accessories(model)
    if unplaced:
        raise SystemExit(f"{giant_id}: could not weld accessories {unplaced}")
    if abs(scale - 1.0) > 1e-6:
        scale_rig(model, 1.0 / scale)

    solved = solve_rig(model)
    if solved.unreached:
        raise SystemExit(f"{giant_id}: parts not on the joint graph: {solved.unreached}")
    ground, lo, hi = rig_bounds(model, solved)
    place_rig(model, solved, cf_translate(0.0, -ground, 0.0), anchored=False)

    hrp = parts["HumanoidRootPart"]
    hip_height = -prop_size(hrp)[1] / 2 - ground
    hum = humanoid_of(model)
    for c in list(hum.findall("Item")):
        if c.get("class") != "NumberValue":  # keep the Body*Scale values
            hum.remove(c)
    make_item("Animator", "Animator", hum)
    set_prop(hum, "token", "RigType", 1)  # R15
    set_prop(hum, "float", "HipHeight", hip_height)
    set_prop(hum, "token", "DisplayDistanceType", 2)  # None: the arena sign names the giant
    set_prop(hum, "token", "HealthDisplayType", 2)  # AlwaysOff
    remove_prop(hum, "NameOcclusion")

    body_top = max(obb_aabb(solved.local_cf[p.get("referent")], prop_size(p))[1][1] for n, p in parts.items() if n in R15_PARTS)
    # Accessory handles the way Humanoid:AddAccessory leaves them: no collision, no mass
    # (a heavy handle would shift the assembly's centre of mass and can even become its
    # physics root).
    for acc in model.findall("Item"):
        if acc.get("class") == "Accessory":
            for handle in acc.findall("Item"):
                if handle.get("class") in BASEPART_CLASSES:
                    set_prop(handle, "bool", "CanCollide", False)
                    set_prop(handle, "bool", "Massless", True)

    set_prop(model, "string", "Name", giant_id)
    write_ref(model, "PrimaryPart", hrp.get("referent"))
    remove_prop(model, "WorldPivotData")
    remove_prop(hrp, "PivotOffset")  # pivot = HRP centre; Phoenix had parked it at the feet
    # Phoenix sized its enemies with Model:ScaleTo, which persists as the model's scale
    # factor. The geometry is back at 1x, so the factor must be too, or ScaleTo(k) on the
    # prefab would be relative to the old size.
    remove_prop(model, "ScaleFactor")
    return {
        "source_scale": scale, "hip_height": hip_height, "height": body_top - ground,
        "accessories": sum(1 for c in model.findall("Item") if c.get("class") == "Accessory"),
        "full_height": hi[1] - ground,
    }


def validate(model, giant_id: str):
    parts = {name_of(p): p for p in model.findall("Item") if p.get("class") in BASEPART_CLASSES}
    refs = {it.get("referent") for it in model.iter("Item")}
    problems = []
    joints = {}
    for p in parts.values():
        for m in p.findall("Item"):
            if m.get("class") == "Motor6D":
                joints[name_of(m)] = m
    for joint, n0, n1 in R15_JOINTS:
        m = joints.get(joint)
        if m is None:
            problems.append(f"missing Motor6D {joint}")
            continue
        p0, p1 = get_prop(m, "Part0"), get_prop(m, "Part1")
        if p0 is None or p0.text != parts[n0].get("referent") or p1 is None or p1.text != parts[n1].get("referent"):
            problems.append(f"Motor6D {joint} not wired {n0}->{n1}")
    hum = humanoid_of(model)
    if hum is None or not any(c.get("class") == "Animator" for c in hum.findall("Item")):
        problems.append("no Humanoid/Animator")
    for it in model.iter("Item"):
        cls = it.get("class")
        if cls in ("Script", "LocalScript", "ModuleScript", "Sound", "HumanoidDescription"):
            problems.append(f"leftover {cls} {name_of(it)}")
        if cls in BASEPART_CLASSES:
            a = get_prop(it, "Anchored")
            if a is not None and a.text == "true":
                problems.append(f"{name_of(it)} anchored")
        if cls in ("Weld", "Motor6D"):
            for pn in ("Part0", "Part1"):
                e = get_prop(it, pn)
                if e is None or e.text not in refs:
                    problems.append(f"{cls} {name_of(it)} has dangling {pn}")
        if cls == "Accessory":
            handle = next((c for c in it.findall("Item") if c.get("class") in BASEPART_CLASSES), None)
            if handle is None or not any(w.get("class") == "Weld" for w in handle.findall("Item")):
                problems.append(f"accessory {name_of(it)} not welded")
            if handle is not None and has_wrap_layer(handle):
                # The engine draws a garment at Size / InitialSize; anything but 1 breaks the fit.
                init = get_prop(handle, "InitialSize")
                if init is None or any(abs(a - b) > 1e-4 for a, b in zip(prop_size(handle), read_vec3(init))):
                    problems.append(f"layered clothing handle of {name_of(it)} is not at its mesh size")
    sf = get_prop(model, "ScaleFactor")
    if sf is not None and abs(float(sf.text) - 1.0) > 1e-6:
        problems.append(f"model ScaleFactor {sf.text}")
    pp = get_prop(model, "PrimaryPart")
    if pp is None or pp.text != parts["HumanoidRootPart"].get("referent"):
        problems.append("PrimaryPart is not the HumanoidRootPart")
    if problems:
        raise SystemExit(f"{giant_id}: " + "; ".join(problems))


# ---------------------------------------------------------------------------- output
def write_stage(model, giant_id: str):
    root = ET.Element("roblox", {"version": "4"})
    ET.SubElement(root, "Meta", {"name": "ExplicitAutoJoints"}).text = "true"
    root.append(model)
    ss = ET.SubElement(root, "SharedStrings")
    used = {(s.text or "").strip() for s in model.iter("SharedString")}
    for key in used:
        if key in SHARED_OUT:
            ET.SubElement(ss, "SharedString", {"md5": key}).text = SHARED_OUT[key]
    path = os.path.join(STAGE_DIR, giant_id + ".rbxmx")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=False)
    return path


def write_sources_for_preview(phoenix_names):
    """Untouched copies of a few source rigs (only referents fixed, scripts stripped), so
    the preview can stand them behind the normalised prefabs as the engine's reference
    rendering (and so the in-engine probes in checks/ have a source to measure). Not part
    of the game."""
    folder = make_item("Folder", "GiantSources")
    for giant_id, display, source in ROSTER:
        if giant_id not in PREVIEW_SOURCE_IDS:
            continue
        item, sf, _, _ = locate(source, phoenix_names)
        model = import_subtree(item, sf)
        set_prop(model, "string", "Name", giant_id)
        folder.append(model)
    root = ET.Element("roblox", {"version": "4"})
    root.append(folder)
    ss = ET.SubElement(root, "SharedStrings")
    for key in {(s.text or "").strip() for s in folder.iter("SharedString")}:
        if key in SHARED_OUT:
            ET.SubElement(ss, "SharedString", {"md5": key}).text = SHARED_OUT[key]
    ET.ElementTree(root).write(os.path.join(STAGE_DIR, "GiantSources.rbxmx"), encoding="utf-8", xml_declaration=False)


def convert_to_binary():
    """XML → .rbxm with lune (rbx_dom); also re-validates the rig from the binary side."""
    cmd = ["lune", "run", os.path.join(HERE, "convert.luau"), STAGE_DIR, OUT_DIR]
    res = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    sys.stdout.write(res.stdout)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        raise SystemExit("lune conversion failed")


def write_roster(rows):
    lines = [
        "# Giant roster",
        "",
        "Prefabs under `assets/ServerStorage/Giants/` (→ `ServerStorage.Giants.<Id>`), generated by",
        "`tools/giants/import_giants.py` from the sibling repos; edit the roster there, not here.",
        "All rigs are normalised R15 characters at base scale 1× with feet on y = 0; the game sizes",
        "them with `Model:ScaleTo()` plus the per-frame Animator fix-up in `tools/giants/preview.luau`",
        "(`scaleGiant`). *Height* is the body height in studs at 1×; *Source scale* is the size the",
        "rig had in its source game (what the gallery showed).",
        "",
        "| Id | Display name | Height | Source scale | Accessories | Source |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| `{r['id']}` | {r['display']} | {r['height']:.1f} | {r['source_scale']:g}× | {r['accessories']} | `{r['source_path']}` |")
    lines.append("")
    with open(ROSTER_DOC, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    # The doc is linted by `npm run lint` (prettier --check .), so let prettier own its layout.
    npx = shutil.which("npx")
    if npx:
        subprocess.run([npx, "prettier", "--write", ROSTER_DOC], cwd=REPO, check=False, capture_output=True)
    else:
        print("  ! npx not found; run `npm run format` to tidy docs/giants-roster.md")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ids = [r[0] for r in ROSTER]
    assert len(ids) == len(set(ids)), "duplicate ids in ROSTER"
    phoenix_names = load_phoenix_names()
    if os.path.isdir(STAGE_DIR):
        shutil.rmtree(STAGE_DIR)
    os.makedirs(STAGE_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)
    for stale in os.listdir(OUT_DIR):
        if stale.endswith(".rbxm") and stale[:-5] not in ids:
            os.remove(os.path.join(OUT_DIR, stale))
            print(f"  removed {stale} (no longer in roster)")
    rows = []
    for index, (giant_id, display, source) in enumerate(ROSTER, 1):
        item, sf, source_path, meta = locate(source, phoenix_names)
        if item is None:
            raise SystemExit(f"{giant_id}: source not found ({source})")
        if meta.get("game_name") and meta["game_name"] != display:
            raise SystemExit(f"{giant_id}: Phoenix zone {meta['Zone']} {meta['SourceSize']} is '{meta['game_name']}', not '{display}'")
        model = import_subtree(item, sf)
        stats = normalise(model, giant_id)
        set_attributes(model, {
            "DisplayName": display, "Source": source["repo"], "SourcePath": source_path,
            "SourceScale": round(stats["source_scale"], 4), "Height": round(stats["height"], 2),
            "RosterIndex": index,
            **{k: v for k, v in meta.items() if k in ("Zone", "SourceSize")},
        })
        validate(model, giant_id)
        write_stage(model, giant_id)
        rows.append({"id": giant_id, "display": display, "source_path": source_path, **stats})
        print(f"  {giant_id:20} h={stats['height']:4.1f} hip={stats['hip_height']:4.2f} scale={stats['source_scale']:<6g} acc={stats['accessories']}")
    write_sources_for_preview(phoenix_names)
    convert_to_binary()
    write_roster(rows)
    print(f"{len(rows)} giants → {os.path.relpath(OUT_DIR, REPO)}; roster at {os.path.relpath(ROSTER_DOC, REPO)}")


if __name__ == "__main__":
    main()
