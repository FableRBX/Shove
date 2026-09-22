"""Unit tests for the rig toolkit (stdlib unittest):  python -m unittest discover -s tools/lib

The XML fixtures are tiny hand-built rigs; the assertions encode engine behaviour that was
measured in Studio (tools/giants/checks/*.luau), so a change here must come with a probe.
"""

import unittest
import xml.etree.ElementTree as ET

import rigs
from rigs import get_prop, make_item, read_vec3, scale_rig, set_prop, write_cf, write_vec3


def mesh_part(parent, name, size, initial_size=None, wrap_layer=False):
    part = make_item("MeshPart", name, parent)
    write_vec3(part, "size", size)
    write_vec3(part, "InitialSize", initial_size or size)
    write_cf(part, "CFrame", rigs.cf_translate(1.0, 2.0, 3.0))
    if wrap_layer:
        make_item("WrapLayer", "HandleWrapLayer", part)
    return part


def size_of(part):
    return read_vec3(get_prop(part, "size"))


def initial_size_of(part):
    return read_vec3(get_prop(part, "InitialSize"))


class ScaleRigTest(unittest.TestCase):
    def setUp(self):
        rigs._parent_maps.clear()
        self.model = make_item("Model", "Rig")
        self.head = mesh_part(self.model, "Head", (2.4, 2.4, 2.4), initial_size=(1.2, 1.2, 1.2))
        self.rigid = make_item("Accessory", "Hat", self.model)
        self.hat_handle = mesh_part(self.rigid, "Handle", (2.0, 1.0, 2.0), initial_size=(1.0, 0.5, 1.0))
        self.garment = make_item("Accessory", "Jacket", self.model)
        # Layered clothing handles are stored at their mesh's native size whatever the body scale.
        self.garment_handle = mesh_part(self.garment, "Handle", (4.67, 2.45, 1.66), wrap_layer=True)
        att = make_item("Attachment", "BodyFrontAttachment", self.garment_handle)
        write_cf(att, "CFrame", rigs.cf_translate(0.0, 0.6, -1.0))

    def test_body_parts_scale_size_but_not_initial_size(self):
        scale_rig(self.model, 0.5)
        self.assertEqual(size_of(self.head), (1.2, 1.2, 1.2))
        self.assertEqual(initial_size_of(self.head), (1.2, 1.2, 1.2))

    def test_rigid_accessory_handles_scale(self):
        scale_rig(self.model, 0.5)
        self.assertEqual(size_of(self.hat_handle), (1.0, 0.5, 1.0))

    def test_layered_clothing_handle_keeps_native_size(self):
        # Measured: Model:ScaleTo(1) on a 2x rig leaves a WrapLayer handle's Size untouched
        # (the garment is fitted to the body's cages, not sized with it); shrinking it makes
        # the engine render the garment at Size / InitialSize and the fit falls apart.
        scale_rig(self.model, 0.5)
        self.assertEqual(size_of(self.garment_handle), (4.67, 2.45, 1.66))
        self.assertEqual(initial_size_of(self.garment_handle), (4.67, 2.45, 1.66))

    def test_layered_clothing_handle_position_and_attachments_still_scale(self):
        # ...but the handle still moves with the body: ScaleTo halved its CFrame and the
        # position of its attachment.
        scale_rig(self.model, 0.5)
        cf = rigs.prop_cf(self.garment_handle, "CFrame")
        self.assertEqual(cf[:3], (0.5, 1.0, 1.5))
        att = next(a for a in self.garment_handle.findall("Item") if a.get("class") == "Attachment")
        self.assertEqual(rigs.prop_cf(att, "CFrame")[:3], (0.0, 0.3, -0.5))


if __name__ == "__main__":
    unittest.main()
