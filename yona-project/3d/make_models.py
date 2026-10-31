"""Builds the 3D-printable STL files for the Jonah project.

Run: python3 make_models.py   (needs: pip install manifold3d trimesh numpy)
All units are millimetres. Every model sits flat on Z=0 and prints without supports
(except the diorama, which may want light supports under the fish's chin).
"""
import math
import os

import numpy as np
import trimesh
from manifold3d import CrossSection, FillRule, Manifold

HERE = os.path.dirname(os.path.abspath(__file__))


def save(m: Manifold, name: str):
    mesh = m.to_mesh()
    tm = trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts)
    tm.export(os.path.join(HERE, name))
    b = tm.bounds
    print(f"{name:28s} {b[1][0]-b[0][0]:6.1f} x {b[1][1]-b[0][1]:6.1f} x {b[1][2]-b[0][2]:6.1f} mm  watertight={tm.is_watertight}")
    return tm


def side_profile(points, width):
    """Extrude a polygon drawn in the X-Z plane to a solid `width` deep in Y (centred)."""
    cs = CrossSection([points], FillRule.NonZero)
    m = Manifold.extrude(cs, width)          # polygon in XY, extruded along +Z
    m = m.rotate([90, 0, 0])                # XY plane -> XZ plane, extrusion now along -Y
    return m.translate([0, width / 2, 0])


def hull_shape(length, width, height):
    """Boat hull: wide deck on top, narrow keel at the bottom, pointed bow."""
    pts = []
    L, W = length / 2, width / 2
    deck = [(-L, -W), (L * 0.6, -W), (L, 0), (L * 0.6, W), (-L, W)]
    keel = [(-L * 0.75, -W * 0.3), (L * 0.45, -W * 0.3), (L * 0.85, 0), (L * 0.45, W * 0.3), (-L * 0.75, W * 0.3)]
    parts = [Manifold.cube([0.01, 0.01, 0.01]).translate([x, y, height]) for x, y in deck]
    parts += [Manifold.cube([0.01, 0.01, 0.01]).translate([x, y, 0]) for x, y in keel]
    return Manifold.batch_hull(parts)


def ship(length):
    s = length / 50.0
    h = hull_shape(length, 18 * s, 11 * s)
    # carve a shallow deck so it looks like a boat, not a brick
    h = h - hull_shape(length * 0.8, 14 * s, 11 * s).translate([-length * 0.04, 0, 8 * s])
    mast = Manifold.cylinder(40 * s, 1.6 * s, 1.6 * s, 24).translate([-2 * s, 0, 2 * s])
    sail_pts = [(-1 * s, 12 * s), (-1 * s, 40 * s), (20 * s, 14 * s)]
    sail = side_profile(sail_pts, 1.6 * s)
    sail2 = side_profile([(-3 * s, 14 * s), (-3 * s, 36 * s), (-18 * s, 15 * s)], 1.6 * s)
    return h + mast + sail + sail2


def fish(length):
    s = length / 46.0
    body = Manifold.sphere(1, 48).scale([23 * s, 9 * s, 10 * s])
    # open mouth: cut a wedge out of the front
    mouth = side_profile([(10 * s, 0), (26 * s, 9 * s), (26 * s, -6 * s)], 30 * s)
    body = body - mouth
    tail = side_profile([(-19 * s, 0), (-33 * s, 11 * s), (-29 * s, 0), (-33 * s, -11 * s)], 3.5 * s)
    fin = side_profile([(-4 * s, 8 * s), (4 * s, 15 * s), (6 * s, 8 * s)], 2.5 * s)
    eye = Manifold.sphere(1.6 * s, 24)
    eyes = eye.translate([11 * s, 6.8 * s, 4 * s]) + eye.translate([11 * s, -6.8 * s, 4 * s])
    return body + tail + fin - eyes


def jonah(height):
    s = height / 14.0
    robe = Manifold.cylinder(9 * s, 3.4 * s, 2.2 * s, 32)
    head = Manifold.sphere(2.4 * s, 32).translate([0, 0, 11 * s])
    arm = Manifold.cylinder(7 * s, 1.0 * s, 1.0 * s, 16)
    arms = arm.rotate([30, 0, 0]).translate([0, 1.5 * s, 7.5 * s]) + arm.rotate([-30, 0, 0]).translate([0, -1.5 * s, 7.5 * s])
    return robe + head + arms


def wave_z(x, y, base_h=9, amp=4.0):
    return (base_h + amp * math.sin(x / 7.5 + 1.2 * math.sin(y / 16.0))
            + 0.45 * amp * math.sin(x / 3.4 - y / 9.0 + 0.7)
            + 0.3 * amp * math.cos(y / 6.0 + x / 11.0))


def sea_base(length, depth, n=140, m=80):
    """Heightfield of a stormy sea with a flat bottom, centred on the origin."""
    xs = np.linspace(-length / 2, length / 2, n + 1)
    ys = np.linspace(-depth / 2, depth / 2, m + 1)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = np.vectorize(wave_z)(X, Y)
    top = np.stack([X, Y, Z], -1).reshape(-1, 3)
    bot = np.stack([X, Y, np.zeros_like(Z)], -1).reshape(-1, 3)
    verts = np.vstack([top, bot])
    off = len(top)
    idx = lambda i, j: i * (m + 1) + j
    faces = []
    for i in range(n):
        for j in range(m):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            faces += [[a, b, c], [a, c, d]]
            faces += [[off + a, off + c, off + b], [off + a, off + d, off + c]]
    def wall(seq):
        for k in range(len(seq) - 1):
            p, q = seq[k], seq[k + 1]
            faces.append([p, off + p, q]); faces.append([q, off + p, off + q])
    wall([idx(i, 0) for i in range(n + 1)])
    wall([idx(n, j) for j in range(m + 1)])
    wall([idx(i, m) for i in range(n, -1, -1)])
    wall([idx(0, j) for j in range(m, -1, -1)])
    tm = trimesh.Trimesh(verts, np.array(faces), process=True)
    if tm.volume < 0:
        tm.invert()
    from manifold3d import Mesh
    return Manifold(Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                         tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


# ---------------------------------------------------------------- diorama
def diorama():
    L, D = 140, 80
    base = sea_base(L, D)

    # ship, tilted by the storm, riding the waves on the left
    sx, sy = -36, 10
    sh = ship(58).rotate([12, -6, 0]).translate([sx, sy, wave_z(sx, sy) - 2.5])

    # the big fish rising from the sea on the right, mouth up toward Jonah
    fx, fy = 40, -8
    fh = fish(56).rotate([0, -38, 0]).translate([fx, fy, wave_z(fx, fy) + 6])

    # splash column carrying Jonah between the ship and the fish
    jx, jy = 10, -4
    jz0 = wave_z(jx, jy) - 2
    splash = Manifold.cylinder(16, 6, 2.6, 32).translate([jx, jy, jz0])
    for dx, dy, dz, r in [(-5, -2, 2, 3.4), (5, -3, 2, 3.0), (0, 4, 2, 2.8), (2, 0, 7, 3.2)]:
        splash = splash + Manifold.sphere(r, 24).translate([jx + dx, jy + dy, jz0 + dz])
    jo = jonah(18).rotate([0, 20, 0]).translate([jx, jy, jz0 + 14])

    model = base + sh + fh + splash + jo
    return model ^ Manifold.cube([400, 400, 200]).translate([-200, -200, 0])


# ---------------------------------------------------------------- game pieces
def crate(size=10):
    c = Manifold.cube([size, size, size])
    g = 0.8
    groove_x = Manifold.cube([size + 2, g, g]).translate([-1, -g / 2, -g / 2])
    for z in (size * 0.33, size * 0.66):
        for y in (0, size):
            c = c - groove_x.translate([0, y, z])
        for x in (0, size):
            c = c - groove_x.rotate([0, 0, 90]).translate([x, -1, z])
    return c


def oar(length=30):
    shaft = Manifold.cube([length * 0.7, 2.6, 2.6]).translate([0, -1.3, 0])
    blade = Manifold.sphere(1, 32).scale([length * 0.22, 4, 1.3]).translate([length * 0.75, 0, 1.3])
    grip = Manifold.cylinder(2.6, 1.8, 1.8, 16).rotate([0, 90, 0]).translate([-1.5, 0, 1.3])
    m = shaft + blade + grip
    return m ^ Manifold.cube([200, 200, 50]).translate([-100, -100, 0])


def cloud():
    parts = [Manifold.sphere(r, 32).translate([x, 0, z]) for x, z, r in
             [(0, 7, 7), (8, 6, 6), (-8, 5, 5.5), (3, 11, 5.5), (-4, 10, 4.5)]]
    m = parts[0]
    for p in parts[1:]:
        m = m + p
    m = m.scale([1, 0.65, 1])
    bolt = side_profile([(-1, 0), (3, 0), (1, 3), (4, 3), (-2, 9), (0, 4), (-3, 4)], 2.5).translate([0, 0, -1])
    m = m.translate([0, 0, 2]) + bolt
    return m ^ Manifold.cube([200, 200, 100]).translate([-100, -100, 0])


def ship_pawn():
    return ship(26).translate([0, 0, 1.5]) + Manifold.cylinder(1.5, 11, 11, 48)


def card_stand():
    """Holds the Jonah card (60 mm wide) upright."""
    base = Manifold.cube([66, 22, 5]).translate([-33, -11, 0])
    slot = Manifold.cube([64, 1.6, 10]).rotate([-10, 0, 0]).translate([-32, -0.8, 2.2])
    lip = Manifold.cube([66, 8, 10]).translate([-33, -4, 0])
    return (base + lip) - slot


if __name__ == "__main__":
    save(diorama(), "diorama_storm.stl")
    save(ship_pawn(), "piece_ship_marker.stl")
    save(cloud(), "piece_storm_marker.stl")
    save(crate(), "piece_cargo_crate.stl")
    save(oar(), "piece_oar.stl")
    save(card_stand(), "piece_jonah_card_stand.stl")
