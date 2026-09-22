"""Shared rig toolkit for the Roblox model importers under tools/.

Works directly on Studio's .rbxmx XML (stdlib ElementTree, no engine needed): copy
subtrees between files (fresh referents, SharedStrings carried over), rebuild R15 joints
and accessory welds from attachments, re-solve a rig's rest pose from its joint graph,
measure it, rescale it, and write it back. Used by tools/npc-gallery/build.py and
tools/giants/import_giants.py.
"""

from __future__ import annotations

import base64
import math
import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

BASEPART_CLASSES = {
    "Part", "MeshPart", "UnionOperation", "WedgePart", "CornerWedgePart",
    "TrussPart", "SpawnLocation", "Seat", "VehicleSeat", "NegateOperation",
}
JOINT_CLASSES = {"Motor6D", "Weld", "ManualWeld", "Motor", "Snap", "Glue"}
# Newer rigs (Borock, bec, golem) are jointed by attachment pairs instead of Part0/Part1.
ATTACHMENT_JOINT_CLASSES = {"AnimationConstraint", "RigidConstraint"}
STRIP_CLASSES = {"Script", "LocalScript", "ModuleScript", "Tool"}
STRIP_NAMES = {"PlayerNameplate", "HitCone"}

MAX_DISPLAY_HEIGHT, DISPLAY_HEIGHT = 14.0, 12.0

R15_PARTS = [
    "Head", "UpperTorso", "LowerTorso",
    "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot",
]
R6_PARTS = ["Head", "Torso", "Left Arm", "Right Arm", "Left Leg", "Right Leg"]
BODY_PARTS = set(R15_PARTS) | set(R6_PARTS)
FEET = {"LeftFoot", "RightFoot", "Left Leg", "Right Leg"}
# (joint name, Part0, Part1); the Motor6D lives in Part1, both parts carry <joint>RigAttachment.
R15_JOINTS = [
    ("Root", "HumanoidRootPart", "LowerTorso"),
    ("Waist", "LowerTorso", "UpperTorso"),
    ("Neck", "UpperTorso", "Head"),
    ("LeftShoulder", "UpperTorso", "LeftUpperArm"),
    ("LeftElbow", "LeftUpperArm", "LeftLowerArm"),
    ("LeftWrist", "LeftLowerArm", "LeftHand"),
    ("RightShoulder", "UpperTorso", "RightUpperArm"),
    ("RightElbow", "RightUpperArm", "RightLowerArm"),
    ("RightWrist", "RightLowerArm", "RightHand"),
    ("LeftHip", "LowerTorso", "LeftUpperLeg"),
    ("LeftKnee", "LeftUpperLeg", "LeftLowerLeg"),
    ("LeftAnkle", "LeftLowerLeg", "LeftFoot"),
    ("RightHip", "LowerTorso", "RightUpperLeg"),
    ("RightKnee", "RightUpperLeg", "RightLowerLeg"),
    ("RightAnkle", "RightLowerLeg", "RightFoot"),
]

# ---------------------------------------------------------------------------- CFrame math
# A CFrame is a 12-tuple (x, y, z, R00, R01, R02, R10, R11, R12, R20, R21, R22), row-major,
# exactly as the XML stores it.
IDENTITY = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def cf_mul(a, b):
    ax, ay, az = a[:3]
    A = a[3:]
    bx, by, bz = b[:3]
    B = b[3:]
    px = ax + A[0] * bx + A[1] * by + A[2] * bz
    py = ay + A[3] * bx + A[4] * by + A[5] * bz
    pz = az + A[6] * bx + A[7] * by + A[8] * bz
    R = [sum(A[i * 3 + k] * B[k * 3 + j] for k in range(3)) for i in range(3) for j in range(3)]
    return (px, py, pz, *R)


def cf_inv(a):
    x, y, z = a[:3]
    A = a[3:]
    Rt = [A[0], A[3], A[6], A[1], A[4], A[7], A[2], A[5], A[8]]
    px = -(Rt[0] * x + Rt[1] * y + Rt[2] * z)
    py = -(Rt[3] * x + Rt[4] * y + Rt[5] * z)
    pz = -(Rt[6] * x + Rt[7] * y + Rt[8] * z)
    return (px, py, pz, *Rt)


def cf_translate(x, y, z):
    return (x, y, z, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def cf_yaw180(x, y, z):
    """Translation plus a 180° turn about Y: faces +Z instead of Roblox's default -Z."""
    return (x, y, z, -1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, -1.0)


def obb_aabb(cf, size):
    """Axis-aligned bounds of an oriented box: (min xyz, max xyz)."""
    R = cf[3:]
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    ex = [abs(R[i * 3]) * hx + abs(R[i * 3 + 1]) * hy + abs(R[i * 3 + 2]) * hz for i in range(3)]
    return [cf[i] - ex[i] for i in range(3)], [cf[i] + ex[i] for i in range(3)]


# ---------------------------------------------------------------------------- XML helpers
_referent_counter = 0


def new_ref():
    global _referent_counter
    _referent_counter += 1
    return f"G{_referent_counter:06d}"


def name_of(item):
    p = item.find("Properties")
    n = p.find("string[@name='Name']") if p is not None else None
    return n.text if n is not None and n.text is not None else ""


def get_prop(item, pname):
    p = item.find("Properties")
    return None if p is None else p.find(f"*[@name='{pname}']")


def props_of(item):
    p = item.find("Properties")
    if p is None:
        p = ET.SubElement(item, "Properties")
    return p


def remove_prop(item, pname):
    p = item.find("Properties")
    e = get_prop(item, pname)
    if p is not None and e is not None:
        p.remove(e)


def set_prop(item, tag, pname, value=None, children=None):
    """Replace or add property <tag name=pname>. `children` is an ordered list of
    (childtag, text) pairs for composite types (Vector3, CoordinateFrame, UDim2, ...)."""
    remove_prop(item, pname)
    e = ET.SubElement(props_of(item), tag, {"name": pname})
    if children is not None:
        for ctag, ctext in children:
            c = ET.SubElement(e, ctag)
            c.text = fmt(ctext)
    elif value is not None:
        e.text = fmt(value)
    return e


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(float(v)) if math.isfinite(v) else "0"
    return str(v)


def read_vec3(e):
    return tuple(float(e.find(a).text) for a in "XYZ")


def read_cf(e):
    if e is None:
        return IDENTITY
    return tuple(float(e.find(t).text) for t in ("X", "Y", "Z", "R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22"))


def prop_cf(item, pname):
    return read_cf(get_prop(item, pname))


def prop_size(item):
    e = get_prop(item, "size")
    if e is None:
        e = get_prop(item, "Size")
    return read_vec3(e) if e is not None else (1.0, 1.0, 1.0)


def write_cf(item, pname, cf):
    tags = ("X", "Y", "Z", "R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22")
    set_prop(item, "CoordinateFrame", pname, children=list(zip(tags, cf)))


def write_vec3(item, pname, v):
    set_prop(item, "Vector3", pname, children=list(zip("XYZ", v)))


def write_color3(item, pname, rgb):
    set_prop(item, "Color3", pname, children=list(zip("RGB", rgb)))


def write_part_color(item, rgb255):
    r, g, b = rgb255
    set_prop(item, "Color3uint8", "Color3uint8", (0xFF << 24) | (r << 16) | (g << 8) | b)


def write_udim2(item, pname, xs, xo, ys, yo):
    set_prop(item, "UDim2", pname, children=[("XS", xs), ("XO", xo), ("YS", ys), ("YO", yo)])


def write_ref(item, pname, target_ref):
    set_prop(item, "Ref", pname, target_ref if target_ref else "null")


def make_item(cls, name, parent=None):
    it = ET.Element("Item", {"class": cls, "referent": new_ref()})
    set_prop(it, "string", "Name", name)
    if parent is not None:
        parent.append(it)
    return it


def encode_attributes(attrs: dict) -> str:
    """Roblox binary attribute blob (the AttributesSerialize property), base64."""
    out = struct.pack("<I", len(attrs))
    for k, v in attrs.items():
        kb = k.encode("utf-8")
        out += struct.pack("<I", len(kb)) + kb
        if isinstance(v, bool):
            out += b"\x03" + (b"\x01" if v else b"\x00")
        elif isinstance(v, (int, float)):
            out += b"\x06" + struct.pack("<d", float(v))
        else:
            vb = str(v).encode("utf-8")
            out += b"\x02" + struct.pack("<I", len(vb)) + vb
    return base64.b64encode(out).decode("ascii")


def set_attributes(item, attrs: dict):
    set_prop(item, "BinaryString", "AttributesSerialize", encode_attributes(attrs))


# ---------------------------------------------------------------------------- source files
class SourceFile:
    """A parsed .rbxmx plus its SharedStrings table, so copied items keep their mesh data."""

    cache: dict[str, "SourceFile"] = {}

    def __init__(self, path):
        self.path = path
        self.root = ET.parse(path).getroot()
        self.shared = {}
        ss = self.root.find("SharedStrings")
        if ss is not None:
            for s in ss.findall("SharedString"):
                self.shared[s.get("md5")] = s.text or ""

    @classmethod
    def load(cls, path):
        if path not in cls.cache:
            cls.cache[path] = cls(path)
        return cls.cache[path]

    def top_items(self):
        return self.root.findall("Item")

    def find(self, path_names):
        """Walk Item names from the root: find(['Skins', 'Kara Lye'])."""
        items = self.top_items()
        node = None
        for n in path_names:
            node = next((i for i in items if name_of(i) == n), None)
            if node is None:
                return None
            items = node.findall("Item")
        return node


SHARED_OUT: dict[str, str] = {}


def import_subtree(item, src: SourceFile):
    """Deep-copy an Item out of a source file: fresh referents, Refs rewritten (external
    ones nulled), scripts/nameplates stripped, SharedStrings carried over."""
    clone = ET.fromstring(ET.tostring(item))
    mapping = {}
    for it in clone.iter("Item"):
        old = it.get("referent")
        mapping[old] = new_ref()
        it.set("referent", mapping[old])
    for ref in clone.iter("Ref"):
        ref.text = mapping.get((ref.text or "").strip(), "null")
    for s in clone.iter("SharedString"):
        key = (s.text or "").strip()
        if key and key in src.shared:
            SHARED_OUT[key] = src.shared[key]
    strip_junk(clone)
    return clone


def strip_junk(item):
    for child in list(item.findall("Item")):
        if child.get("class") in STRIP_CLASSES or name_of(child) in STRIP_NAMES:
            item.remove(child)
        else:
            strip_junk(child)


# ---------------------------------------------------------------------------- rig work
def baseparts(model):
    return [it for it in model.iter("Item") if it.get("class") in BASEPART_CLASSES]


def child_attachments(part):
    return {name_of(a): a for a in part.findall("Item") if a.get("class") == "Attachment"}


_parent_maps: dict[int, dict] = {}


def parent_of(model, item):
    """Parent Item of `item` within `model` (ElementTree has no parent links)."""
    pm = _parent_maps.get(id(model))
    if pm is None or item not in pm:
        pm = {c: p for p in model.iter("Item") for c in p.findall("Item")}
        _parent_maps[id(model)] = pm
    return pm.get(item)


def attachment_pair(joint, model):
    refs = {it.get("referent"): it for it in model.iter("Item")}
    a0 = refs.get((get_prop(joint, "Attachment0").text or "").strip()) if get_prop(joint, "Attachment0") is not None else None
    a1 = refs.get((get_prop(joint, "Attachment1").text or "").strip()) if get_prop(joint, "Attachment1") is not None else None
    return a0, a1


def joint_ends(joint, model):
    """(Part0 referent, Part1 referent) for any joint-like instance, or None. Ends that
    resolve outside the model come back as 'null'."""
    cls = joint.get("class")
    if cls in JOINT_CLASSES or cls == "WeldConstraint":
        e0, e1 = get_prop(joint, "Part0"), get_prop(joint, "Part1")
        return ((e0.text or "null").strip() if e0 is not None else "null",
                (e1.text or "null").strip() if e1 is not None else "null")
    if cls in ATTACHMENT_JOINT_CLASSES:
        a0, a1 = attachment_pair(joint, model)
        p0 = parent_of(model, a0) if a0 is not None else None
        p1 = parent_of(model, a1) if a1 is not None else None
        return (p0.get("referent") if p0 is not None else "null",
                p1.get("referent") if p1 is not None else "null")
    return None


def has_wrap_layer(part):
    """True for a layered-clothing handle: a BasePart with a WrapLayer child."""
    return any(c.get("class") == "WrapLayer" for c in part.findall("Item"))


def inside_accessory(model, part):
    node = parent_of(model, part)
    while node is not None:
        if node.get("class") in ("Accessory", "Hat"):
            return True
        node = parent_of(model, node)
    return False


def synthesize_r15(model, hrp_attach_y):
    """gsclassic skins are loose R15 body parts (Motor6Ds with Part0 = nil, no root, no
    Humanoid). Give them a HumanoidRootPart, a Humanoid and fully wired joints so the
    generic solver — and, later, the game — can treat them like any other rig."""
    parts = {name_of(p): p for p in model.findall("Item") if p.get("class") in BASEPART_CLASSES}
    if "HumanoidRootPart" not in parts:
        hrp = make_item("Part", "HumanoidRootPart", model)
        write_vec3(hrp, "size", (2.0, 2.0, 1.0))
        set_prop(hrp, "float", "Transparency", 1.0)
        set_prop(hrp, "bool", "CanCollide", True)
        write_cf(hrp, "CFrame", IDENTITY)
        att = make_item("Attachment", "RootRigAttachment", hrp)
        write_cf(att, "CFrame", cf_translate(0.0, hrp_attach_y, 0.0))
        parts["HumanoidRootPart"] = hrp
    for joint, n0, n1 in R15_JOINTS:
        p0, p1 = parts.get(n0), parts.get(n1)
        if p0 is None or p1 is None:
            continue
        a0 = child_attachments(p0).get(joint + "RigAttachment")
        a1 = child_attachments(p1).get(joint + "RigAttachment")
        if a0 is None or a1 is None:
            continue
        motor = next((m for m in p1.findall("Item") if m.get("class") == "Motor6D" and name_of(m) == joint), None)
        if motor is None:
            motor = make_item("Motor6D", joint, p1)
        write_ref(motor, "Part0", p0.get("referent"))
        write_ref(motor, "Part1", p1.get("referent"))
        write_cf(motor, "C0", prop_cf(a0, "CFrame"))
        write_cf(motor, "C1", prop_cf(a1, "CFrame"))
    if not any(c.get("class") == "Humanoid" for c in model.findall("Item")):
        hum = make_item("Humanoid", "Humanoid", model)
        set_prop(hum, "token", "RigType", 1)  # R15
        set_prop(hum, "float", "MaxHealth", 100.0)
        set_prop(hum, "float", "Health", 100.0)


def weld_accessories(model):
    """Every Accessory whose Handle has no joint gets an AccessoryWeld built from the
    attachment pair (Handle.<X>Attachment <-> body part.<X>Attachment), exactly as the
    engine does at runtime. Returns the names of accessories that could not be placed."""
    parts = baseparts(model)
    part_refs = {p.get("referent") for p in parts}
    jointed = set()
    for j in list(model.iter("Item")):
        ends = joint_ends(j, model)
        if ends is None:
            continue
        r0, r1 = ends
        if r0 in part_refs and r1 in part_refs:
            jointed.update((r0, r1))
        elif j.get("class") in JOINT_CLASSES:
            # A stale AccessoryWeld whose other end was the character this skin was
            # captured from; drop it so a fresh one can be built from the attachments.
            parent_of(model, j).remove(j)
    body_atts = {}
    for p in parts:
        if inside_accessory(model, p):
            continue
        for an, a in child_attachments(p).items():
            body_atts.setdefault(an, (p, a))
    unplaced = []
    for acc in model.iter("Item"):
        if acc.get("class") not in ("Accessory", "Hat"):
            continue
        handle = next((c for c in acc.findall("Item") if c.get("class") in BASEPART_CLASSES and name_of(c) == "Handle"), None)
        if handle is None:
            handle = next((c for c in acc.findall("Item") if c.get("class") in BASEPART_CLASSES), None)
        if handle is None or handle.get("referent") in jointed:
            continue
        pair = None
        for an, a in child_attachments(handle).items():
            if an in body_atts:
                pair = (a, *body_atts[an])
                break
        if pair is None:
            unplaced.append(name_of(acc))
            continue
        h_att, body_part, b_att = pair
        weld = make_item("Weld", "AccessoryWeld", handle)
        write_ref(weld, "Part0", handle.get("referent"))
        write_ref(weld, "Part1", body_part.get("referent"))
        write_cf(weld, "C0", prop_cf(h_att, "CFrame"))
        write_cf(weld, "C1", prop_cf(b_att, "CFrame"))
        set_prop(weld, "bool", "Enabled", True)
    return unplaced


@dataclass
class SolvedRig:
    local_cf: dict  # part referent -> CFrame relative to the root part
    root: ET.Element
    unreached: list = field(default_factory=list)


def solve_rig(model) -> SolvedRig:
    """Re-derive every part's CFrame from the joint graph (C0 * C1^-1 per Motor6D/Weld,
    rig attachments preferred for Motor6Ds). Saved rigs sit mid-animation; this puts
    them all in the same rest pose, root at the origin facing -Z."""
    parts = {p.get("referent"): p for p in baseparts(model)}
    by_name = {}
    for p in parts.values():
        by_name.setdefault(name_of(p), p)
    root = next((by_name[n] for n in ("HumanoidRootPart", "LowerTorso", "Torso") if n in by_name), None)
    if root is None:
        root = max(parts.values(), key=lambda p: math.prod(prop_size(p)))
    adj: dict[str, list] = {r: [] for r in parts}
    for j in model.iter("Item"):
        cls = j.get("class")
        ends = joint_ends(j, model)
        if ends is None:
            continue
        r0, r1 = ends
        if r0 not in parts or r1 not in parts or r0 == r1:
            continue
        if cls == "WeldConstraint":
            T = cf_mul(cf_inv(prop_cf(parts[r0], "CFrame")), prop_cf(parts[r1], "CFrame"))
        elif cls in ATTACHMENT_JOINT_CLASSES:
            a0, a1 = attachment_pair(j, model)
            T = cf_mul(prop_cf(a0, "CFrame"), cf_inv(prop_cf(a1, "CFrame")))
        else:
            c0, c1 = prop_cf(j, "C0"), prop_cf(j, "C1")
            if cls == "Motor6D":
                an = name_of(j) + "RigAttachment"
                a0 = child_attachments(parts[r0]).get(an)
                a1 = child_attachments(parts[r1]).get(an)
                if a0 is not None and a1 is not None:
                    c0, c1 = prop_cf(a0, "CFrame"), prop_cf(a1, "CFrame")
            T = cf_mul(c0, cf_inv(c1))  # Part1 = Part0 * T
        adj[r0].append((r1, T))
        adj[r1].append((r0, cf_inv(T)))
    local = {root.get("referent"): IDENTITY}
    queue = [root.get("referent")]
    while queue:
        cur = queue.pop(0)
        for nxt, T in adj[cur]:
            if nxt not in local:
                local[nxt] = cf_mul(local[cur], T)
                queue.append(nxt)
    unreached = []
    root_stored = prop_cf(root, "CFrame")
    for r, p in parts.items():
        if r not in local:
            # Keep whatever offset from the root the file had (accessories with no matching
            # attachment, stray decoration parts).
            local[r] = cf_mul(cf_inv(root_stored), prop_cf(p, "CFrame"))
            unreached.append(name_of(p))
    return SolvedRig(local, root, unreached)


def rig_bounds(model, solved: SolvedRig):
    """(ground_y, aabb_min, aabb_max) in rig-local space. Ground comes from the feet so
    a low-hanging cape or tail does not lift the character off its pedestal."""
    parts = baseparts(model)
    lo, hi = [1e9] * 3, [-1e9] * 3
    foot_lo, body_lo = 1e9, 1e9
    for p in parts:
        n = name_of(p)
        if n == "HumanoidRootPart":
            continue
        a, b = obb_aabb(solved.local_cf[p.get("referent")], prop_size(p))
        for i in range(3):
            lo[i] = min(lo[i], a[i])
            hi[i] = max(hi[i], b[i])
        if n in FEET:
            foot_lo = min(foot_lo, a[1])
        if n in BODY_PARTS:
            body_lo = min(body_lo, a[1])
    ground = foot_lo if foot_lo < 1e8 else (body_lo if body_lo < 1e8 else lo[1])
    return ground, lo, hi


def place_rig(model, solved: SolvedRig, world_cf, anchored=True):
    for p in baseparts(model):
        write_cf(p, "CFrame", cf_mul(world_cf, solved.local_cf[p.get("referent")]))
        set_prop(p, "bool", "Anchored", anchored)
        remove_prop(p, "Velocity")
        remove_prop(p, "RotVelocity")


def scale_vec_prop(item, pname, s):
    e = get_prop(item, pname)
    if e is not None:
        write_vec3(item, pname, tuple(v * s for v in read_vec3(e)))


def scale_cf_prop(item, pname, s):
    e = get_prop(item, pname)
    if e is not None:
        cf = read_cf(e)
        write_cf(item, pname, (cf[0] * s, cf[1] * s, cf[2] * s, *cf[3:]))


HUMANOID_SIZE_SCALES = {"BodyWidthScale", "BodyHeightScale", "BodyDepthScale", "HeadScale"}


def scale_rig(model, s):
    """Uniformly rescale a rig in place, mirroring what Model:ScaleTo does: part sizes,
    attachment and joint offsets, legacy mesh scale/offset, HipHeight, and the Humanoid's
    width/height/depth/head scale values. OriginalSize/OriginalPosition, BodyTypeScale and
    BodyProportionScale are left alone (verified against ScaleTo in-engine); layered
    clothing needs that bookkeeping intact to fit. Shape is preserved exactly.

    Layered-clothing handles (WrapLayer) are the one exception: the engine keeps them at
    the garment mesh's native size at every body scale (ScaleTo moves them but never
    resizes them; the garment is fitted to the body's cages, not sized with it). Shrinking
    one makes the engine draw the garment at Size / InitialSize and the fit collapses into
    floating plates -- measured in tools/giants/checks/wraplayer-probe.luau."""
    for it in model.iter("Item"):
        cls = it.get("class")
        if cls in BASEPART_CLASSES:
            if not has_wrap_layer(it):
                scale_vec_prop(it, "size", s)
            scale_cf_prop(it, "CFrame", s)
            scale_cf_prop(it, "PivotOffset", s)
            scale_vec_prop(it, "JointOffset", s)  # R15 mesh joint offset, in studs
            # InitialSize is the mesh's native size and must NOT scale: the engine renders
            # the mesh at Size / InitialSize, so halving it doubled every head.
        elif cls == "Attachment":
            scale_cf_prop(it, "CFrame", s)
        elif cls in JOINT_CLASSES:
            scale_cf_prop(it, "C0", s)
            scale_cf_prop(it, "C1", s)
        elif cls in ("SpecialMesh", "FileMesh", "BlockMesh", "CylinderMesh"):
            scale_vec_prop(it, "Scale", s)
            scale_vec_prop(it, "Offset", s)
        elif cls == "Humanoid":
            e = get_prop(it, "HipHeight")
            if e is not None:
                set_prop(it, "float", "HipHeight", float(e.text) * s)
            for v in it.findall("Item"):
                if v.get("class") == "NumberValue" and name_of(v) in HUMANOID_SIZE_SCALES:
                    ev = get_prop(v, "Value")
                    if ev is not None:
                        set_prop(v, "double", "Value", float(ev.text) * s)


def quiet_humanoid(model, hip_height=None):
    for h in model.findall("Item"):
        if h.get("class") != "Humanoid":
            continue
        set_prop(h, "token", "DisplayDistanceType", 2)  # None: no floating name over the label
        set_prop(h, "token", "HealthDisplayType", 2)  # AlwaysOff
        if hip_height is not None:
            set_prop(h, "float", "HipHeight", hip_height)



# ---------------------------------------------------------------------------- inspection
def mesh_set(model):
    ids = set()
    for p in model.findall("Item"):
        if p.get("class") != "MeshPart":
            continue
        for tag in ("MeshContent", "MeshId", "MeshID"):
            e = get_prop(p, tag)
            if e is None:
                continue
            txt = " ".join((c.text or "") for c in e) + (e.text or "")
            m = re.search(r"(\d{5,})", txt)
            if m:
                ids.add(m.group(1))
    return frozenset(ids)


def hrp_attach_y_of(model):
    for p in model.findall("Item"):
        if name_of(p) == "HumanoidRootPart":
            a = child_attachments(p).get("RootRigAttachment")
            if a is not None:
                return prop_cf(a, "CFrame")[1]
    return None

