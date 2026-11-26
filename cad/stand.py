"""Parametric enclosure + stand for the Waveshare 7.5" raw e-ink panel + Pi Zero 2 W.

Three supportless printed parts:
  frame      - front bezel; panel drops into a pocket from behind
  back_plate - closes the frame; two cradles locate the PiSugar + Pi stack and the driver HAT
  foot       - box over both bays; its underside is the desk contact. Printed rear wall down.

Build coords: X = width, Y = depth (0 = front face, + = back), Z = up the panel.
Run: .venv/bin/python cad/stand.py  ->  design/stl/*.stl, design/stand.step
"""
import math
from pathlib import Path

import cadquery as cq

# ── Panel (Waveshare drawing; thickness measured 1.12 on 2026-11-26) ──────
PANEL_W, PANEL_H, PANEL_T = 170.2, 111.2, 1.12
ACTIVE_W, ACTIVE_H = 163.2, 97.92
BORDER_BOTTOM = 8.9          # panel edge -> active area, FPC side (assumed)
FPC_W, FPC_X = 34.0, 8.0     # tail slot width / offset from centre (assumed)

# ── Design ────────────────────────────────────────────────────────────────
TILT = 18.0                  # degrees the screen leans back
FIT = 0.3                    # clearance per side around the panel
LIP_T = 1.2                  # bezel thickness in front of the glass
GAP = 2.2                    # behind panel: foam pad + FPC fold
PLATE_T = 2.4
LEDGE = 1.2                  # plate rests on this step around the pocket
WALL, CHIN = 2.5, 7.5        # frame walls; bottom wall is thicker
WIN_MARGIN = 0.5             # window opening beyond the active area

FOOT_WALL = 2.4
FOOT_TOP = 50.0                                # flat top, just above the port edge
PI_W, PI_H, PI_Z0 = 65.5, 30.0, 16.0           # board footprint (65.48 measured); port edge faces up

# Electronics behind the plate, side by side (measured 2026-11-26 unless marked est.):
#   Pi bay  (-x): PiSugar S battery taped to the plate -> PiSugar PCB -> Pi (with heatsink)
#                 -> 9 Dupont jumpers standing on the header. 36.1 mm battery face to jumper tops.
#   HAT bay (+x): driver HAT flat against the plate, wired to the Pi by the 9-wire cable.
#                 The FFC adapter (30.4 mm long) and folded FFC live in the space behind it.
# The PiSugar's screws use the Pi's four mounting holes, so both boards sit in cradles
# on the plate and are held by double-sided foam tape, not standoffs.
STACK_GAP = 1.0              # plate -> battery (foam tape)
STACK_H = 36.1               # battery face -> top of the jumper housings
WIRE_BEND = 6.0              # room behind the housings for the wires to turn
PISUGAR_T = 7.5              # battery + PiSugar PCB (est.)
PI_RISE = 16.5               # battery face -> underside of the Pi PCB (est. from the photo)
PCB_T = 1.6
PORT_ZONE = 25.0             # battery face -> past the Pi's USB shells; top notch spans this
HAT_W, HAT_H, HAT_T = 65.7, 30.5, 13.0   # 65.69 measured; thickness incl. 2x20 socket est.
CRADLE_H = 8.0
SIDE_GAP, MID_GAP = 7.1, 4.0 # board -> foot side wall (clears the screw bosses); Pi -> HAT

# Fasteners: plate hooks into the frame's top wall on two tabs and is held by two
# M2 screws through ears into the chin; the foot takes four M2 screws through the plate.
EAR_X, EAR_W, EAR_SCREW_Z = 60.0, 10.0, 5.0
TAB_X, TAB_W, TAB_T, TAB_L = 50.0, 12.0, 1.0, 1.1
BOSS_ZS, BOSS_LEN = (12.5, 44.0), 8.0
PILOT_R, CLEAR_R, HEAD_R, HEAD_H = 0.8, 1.2, 2.2, 1.2   # M2 self-tapping pan head

tan_t = math.tan(math.radians(TILT))
pocket_w, pocket_h = PANEL_W + 2 * FIT, PANEL_H + 2 * FIT
cav_w, cav_h = pocket_w + 2 * LEDGE, pocket_h + 2 * LEDGE
OUT_W, OUT_H = cav_w + 2 * WALL, cav_h + WALL + CHIN
D_POCKET = LIP_T + PANEL_T + 0.4
D_PLATE0 = D_POCKET + GAP
DEPTH = D_PLATE0 + PLATE_T
cav_z0 = CHIN
pocket_z0 = cav_z0 + LEDGE
panel_z0 = pocket_z0 + FIT
active_z0 = panel_z0 + BORDER_BOTTOM
Y_PS = DEPTH + STACK_GAP
Y_PI = Y_PS + PI_RISE
STACK_TOP = Y_PS + STACK_H
FOOT_D = round(STACK_TOP + WIRE_BEND + FOOT_WALL, 1)   # depth of rear wall / rear desk contact
FOOT_W = round(2 * FOOT_WALL + 2 * SIDE_GAP + PI_W + MID_GAP + HAT_W + 0.6)
BOSS_X = FOOT_W / 2 - FOOT_WALL - 3.0
PI_X = -FOOT_W / 2 + FOOT_WALL + SIDE_GAP + PI_W / 2
HAT_X = PI_X + PI_W / 2 + MID_GAP + HAT_W / 2


def box(xc, w, y0, y1, z0, z1):
    return cq.Workplane("XY").box(w, y1 - y0, z1 - z0, centered=(True, False, False)).translate((xc, y0, z0))


def cyl(x, z, y0, y1, r):
    """Cylinder along the depth axis."""
    return cq.Workplane("XZ").circle(r).extrude(-(y1 - y0)).translate((x, y0, z))


def prism(pts, width):
    """Extrude a (depth, up) profile across X, centred."""
    return cq.Workplane("YZ").polyline(pts).close().extrude(width).translate((-width / 2, 0, 0))


def make_frame():
    f = box(0, OUT_W, 0, DEPTH, 0, OUT_H).edges("|Y").fillet(4.0)
    f = f.cut(box(0, ACTIVE_W + 2 * WIN_MARGIN, -1, LIP_T + 0.01,
                  active_z0 - WIN_MARGIN, active_z0 + ACTIVE_H + WIN_MARGIN))
    f = f.cut(box(0, pocket_w, LIP_T, D_POCKET + 0.01, pocket_z0, pocket_z0 + pocket_h))
    f = f.cut(box(0, cav_w, D_POCKET, DEPTH + 1, cav_z0, cav_z0 + cav_h))
    # relief so the FPC tail can fold 180° behind the panel
    f = f.cut(box(FPC_X, FPC_W, LIP_T, DEPTH + 1, cav_z0 - 2.0, pocket_z0 + 0.01))
    cav_top = cav_z0 + cav_h
    for sx in (-1, 1):
        f = f.cut(box(sx * EAR_X, EAR_W + 0.6, D_PLATE0, DEPTH + 1, 2.2, cav_z0 + 0.01))    # ear recess
        f = f.cut(cyl(sx * EAR_X, EAR_SCREW_Z, 1.6, D_PLATE0 + 0.01, PILOT_R))
        f = f.cut(box(sx * TAB_X, TAB_W + 0.6, D_PLATE0 - 0.2, D_PLATE0 + TAB_T + 0.3,
                      cav_top - 0.01, cav_top + 1.5))                                      # tab pocket
    # bottom edge sits flat on the desk at TILT
    f = f.cut(prism([(0, 0), (DEPTH + 2, (DEPTH + 2) * tan_t), (DEPTH + 2, -1), (0, -1)], OUT_W + 2))
    return f


def make_plate():
    p = box(0, cav_w - 0.4, D_PLATE0, DEPTH, cav_z0 + 0.2, cav_z0 + cav_h - 0.2)
    p = p.cut(box(FPC_X, FPC_W, D_PLATE0 - 1, DEPTH + 1, 9.5, 12.5))      # FPC pass-through
    top = cav_z0 + cav_h - 0.2
    for sx in (-1, 1):
        ear = box(sx * EAR_X, EAR_W, D_PLATE0, DEPTH, 2.8, cav_z0 + 0.3)
        p = p.union(ear).cut(cyl(sx * EAR_X, EAR_SCREW_Z, D_PLATE0 - 1, DEPTH + 1, CLEAR_R))
        p = p.union(box(sx * TAB_X, TAB_W, D_PLATE0, D_PLATE0 + TAB_T, top - 0.5, top + TAB_L))
        for bz in BOSS_ZS:  # foot screws go in from the panel side, heads counterbored
            p = p.cut(cyl(sx * BOSS_X, bz, D_PLATE0 - 1, DEPTH + 1, CLEAR_R))
            p = p.cut(cyl(sx * BOSS_X, bz, D_PLATE0 - 1, D_PLATE0 + HEAD_H, HEAD_R))
    # cradles: a shelf under each board takes its weight, stubs stop it sliding sideways
    for xc, w in ((PI_X, PI_W), (HAT_X, HAT_W)):
        p = p.union(box(xc, 60, DEPTH, DEPTH + CRADLE_H, PI_Z0 - 2.4, PI_Z0 - 0.3))
        for sx in (-1, 1):
            p = p.union(box(xc + sx * (w / 2 + 1.4), 2.0, DEPTH, DEPTH + CRADLE_H, PI_Z0 + 8, PI_Z0 + 20))
    return p


FOOT_PROFILE = [(DEPTH, 6.5), (6.5 / tan_t, 6.5), (FOOT_D, FOOT_D * tan_t), (FOOT_D, FOOT_TOP), (DEPTH, FOOT_TOP)]


def make_foot():
    outer = prism(FOOT_PROFILE, FOOT_W)
    inner_w = FOOT_W - 2 * FOOT_WALL
    inner = (cq.Workplane("YZ").polyline(FOOT_PROFILE).close().offset2D(-FOOT_WALL)
             .extrude(inner_w).translate((-inner_w / 2, 0, 0)))
    foot = outer.cut(inner).cut(inner.translate((0, -FOOT_WALL - 0.5, 0)))  # open to the plate
    for sx in (-1, 1):
        for bz in BOSS_ZS:  # full-depth columns so they print from the rear wall with no overhang
            boss = box(sx * BOSS_X, 6.0, DEPTH, FOOT_D - 1, bz - 3, bz + 3).intersect(outer)
            foot = foot.union(boss).cut(cyl(sx * BOSS_X, bz, DEPTH - 1, DEPTH + BOSS_LEN, PILOT_R))
    # Port edge of the PiSugar and the Pi faces up: one notch in the top wall, open to the
    # plate side, spans the whole board width so any USB / switch position on that edge is reachable.
    foot = foot.cut(box(PI_X, PI_W + 1.0, DEPTH - 1, Y_PS + PORT_ZONE, PI_Z0 + PI_H - 0.01, FOOT_TOP + 1))
    # microSD window in the side wall (card is on the Pi's short edge; Pi height is an estimate, so it is tall)
    foot = foot.cut(box(-FOOT_W / 2, 10, Y_PI - 4.0, Y_PI + 7.0, PI_Z0 + 6, PI_Z0 + 24))
    # the foot covers the plate's ear screws: floor notches leave room for their heads and a driver
    for sx in (-1, 1):
        foot = foot.cut(box(sx * EAR_X, EAR_W + 2.0, DEPTH - 1, 26.0, 0, 6.5 + FOOT_WALL + 0.1))
    return foot


def coupon(shape):
    """Small test pieces: chin corner (pocket depth, FPC relief, ear screw) and a tab corner."""
    chin = box((OUT_W / 2 + 1 - 12) / 2, OUT_W / 2 + 1 + 12, -5, 50, -1, 28)
    tab = box((OUT_W / 2 + 1 + 38) / 2, OUT_W / 2 + 1 - 38, -5, 50, OUT_H - 22, OUT_H + 1)
    return shape.intersect(chin.union(tab))


def make_dummies():
    """Non-printed reference bodies for fit checks and renders."""
    panel = box(0, PANEL_W, LIP_T, LIP_T + PANEL_T, panel_z0, panel_z0 + PANEL_H)
    pisugar = box(PI_X, PI_W, Y_PS, Y_PS + PISUGAR_T, PI_Z0, PI_Z0 + PI_H)
    pi = box(PI_X, PI_W, Y_PI, Y_PI + PCB_T, PI_Z0, PI_Z0 + PI_H)
    sink = box(PI_X, 40, Y_PI + PCB_T, Y_PI + PCB_T + 6, PI_Z0 + 8, PI_Z0 + PI_H - 2)
    jumpers = box(PI_X, 51, Y_PI + PCB_T, STACK_TOP, PI_Z0 + 1, PI_Z0 + 6)
    hat = box(HAT_X, HAT_W, DEPTH + 0.5, DEPTH + 0.5 + HAT_T, PI_Z0, PI_Z0 + HAT_H)
    return panel, pisugar.union(pi).union(sink).union(jumpers).union(hat)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "design"
    (out / "stl").mkdir(parents=True, exist_ok=True)
    frame, plate, foot = make_frame(), make_plate(), make_foot()
    panel, elec = make_dummies()

    # Interference checks: printed parts vs each other and vs the hardware
    pairs = {"frame∩plate": (frame, plate), "plate∩foot": (plate, foot), "frame∩foot": (frame, foot),
             "frame∩panel": (frame, panel), "foot∩electronics": (foot, elec), "plate∩electronics": (plate, elec)}
    for name, (a, b) in pairs.items():
        v = a.intersect(b).val().Volume()
        print(f"{name:20s} {v:8.2f} mm³ {'OK' if v < 0.5 else 'CLASH'}")

    stand = lambda s: s.rotate((0, 0, 0), (1, 0, 0), -TILT)          # as it sits on the desk
    for name, shape in [("frame", frame), ("back_plate", plate), ("foot", foot),
                        ("ref_panel", panel), ("ref_electronics", elec)]:
        cq.exporters.export(stand(shape), str(out / "stl" / f"assembled_{name}.stl"), tolerance=0.02)
    # print orientation: frame and plate front face down; foot rear wall down (open side up)
    bed = lambda s, y0: s.translate((0, -y0, 0)).rotate((0, 0, 0), (1, 0, 0), 90)
    cq.exporters.export(foot.rotate((0, 0, 0), (1, 0, 0), -90).translate((0, 0, FOOT_D)),
                        str(out / "stl" / "print_foot.stl"), tolerance=0.02)
    for name, shape, y0 in [("frame", frame, 0), ("back_plate", plate, D_PLATE0),
                            ("coupon_frame", coupon(frame), 0), ("coupon_plate", coupon(plate), D_PLATE0)]:
        cq.exporters.export(bed(shape, y0), str(out / "stl" / f"print_{name}.stl"), tolerance=0.02)
    assy = cq.Assembly()
    for name, shape in [("frame", frame), ("back_plate", plate), ("foot", foot), ("panel", panel), ("electronics", elec)]:
        assy.add(stand(shape), name=name)
    assy.save(str(out / "stand.step"))

    bb = stand(frame.union(plate).union(foot)).val().BoundingBox()
    print(f"frame outer {OUT_W:.1f} x {OUT_H:.1f} x {DEPTH:.1f} mm; "
          f"on desk: {bb.xlen:.0f} W x {bb.ylen:.0f} D x {bb.zlen:.0f} H mm, min z {bb.zmin:.2f}")
    print(f"bezel: sides {(OUT_W - ACTIVE_W) / 2 - WIN_MARGIN:.1f}, top "
          f"{OUT_H - active_z0 - ACTIVE_H - WIN_MARGIN:.1f}, chin {active_z0 - WIN_MARGIN:.1f} mm")
    print(f"foot {FOOT_W:.0f} W x {FOOT_D:.1f} deep; jumper tops at depth {STACK_TOP:.1f}, inner rear wall at "
          f"{FOOT_D - FOOT_WALL:.1f} -> {FOOT_D - FOOT_WALL - STACK_TOP:.1f} mm for the wires to turn")
    print(f"active window corners (x, depth, up): ±{ACTIVE_W / 2}, {LIP_T}, {active_z0:.2f}..{active_z0 + ACTIVE_H:.2f}")
