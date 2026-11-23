"""Headless Blender render of the stand proposal.
Run: blender -b --python cad/render_blender.py
"""
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
STL = ROOT / "design" / "stl"
OUT = ROOT / "design"
TILT = math.radians(18)
LIP_T, AZ0, AZ1, AX = 1.2, 17.90, 115.82, 81.6

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, rgb, rough=0.6, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def load(name, material):
    bpy.ops.wm.stl_import(filepath=str(STL / f"assembled_{name}.stl"))
    o = bpy.context.selected_objects[0]
    o.name = name
    o.data.materials.append(material)
    return o


shell = mat("shell", (0.035, 0.037, 0.04), 0.55)
objs = {
    "frame": load("frame", shell),
    "back_plate": load("back_plate", shell),
    "foot": load("foot", shell),
    "panel": load("ref_panel", mat("panel", (0.78, 0.78, 0.76), 0.4)),
    "elec": load("ref_electronics", mat("pcb", (0.02, 0.25, 0.08), 0.5)),
}


def tilt(x, depth, up):
    return (x, depth * math.cos(TILT) + up * math.sin(TILT), -depth * math.sin(TILT) + up * math.cos(TILT))


# Screen: a textured quad just in front of the panel glass, showing the UI mockup
d = LIP_T - 0.05
verts = [tilt(-AX, d, AZ0), tilt(AX, d, AZ0), tilt(AX, d, AZ1), tilt(-AX, d, AZ1)]
mesh = bpy.data.meshes.new("screen")
mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
uv = mesh.uv_layers.new()
for i, co in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
    uv.data[i].uv = co
screen = bpy.data.objects.new("screen", mesh)
scene.collection.objects.link(screen)
sm = bpy.data.materials.new("ui")
sm.use_nodes = True
nt = sm.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(str(OUT / "ui_mockup.png"))
tex.interpolation = "Closest"
ramp = nt.nodes.new("ShaderNodeMapRange")  # e-ink black/white are really dark grey / light grey
ramp.inputs["To Min"].default_value = 0.03
ramp.inputs["To Max"].default_value = 0.62
nt.links.new(tex.outputs["Color"], ramp.inputs["Value"])
bsdf = nt.nodes["Principled BSDF"]
nt.links.new(ramp.outputs["Result"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.5
mesh.materials.append(sm)

# Desk
bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
bpy.context.object.data.materials.append(mat("desk", (0.72, 0.70, 0.66), 0.8))

# Light: soft key from front-left, plus world fill
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.9, 0.92, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
scene.world = world
for loc, energy, size in [((-300, -400, 450), 2.2e6, 300), ((350, 300, 300), 1.2e6, 300)]:
    ld = bpy.data.lights.new("key", "AREA")
    ld.energy, ld.size = energy, size
    lo = bpy.data.objects.new("key", ld)
    lo.location = loc
    lo.rotation_euler = (Vector((0, 20, 50)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(lo)

cam_d = bpy.data.cameras.new("cam")
cam_d.lens, cam_d.clip_end = 70, 5000
cam = bpy.data.objects.new("cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1100, 800
scene.view_settings.view_transform = "Standard"


def shot(name, loc, target, hide=()):
    for k, o in objs.items():
        o.hide_render = k in hide
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"stand_{name}.png")
    bpy.ops.render.render(write_still=True)


shot("front", (-190, -400, 150), (0, 25, 52))
shot("rear", (260, 360, 170), (0, 25, 50))
shot("rear_open", (260, 360, 170), (0, 25, 50), hide=("foot",))
shot("side", (520, 30, 60), (0, 30, 56))
