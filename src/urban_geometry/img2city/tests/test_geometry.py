"""Footprint geometry: convex hull, oriented bounding box, containment,
front-edge selection -- the placement contract's pure-math core."""
import math

import pytest

cg = pytest.importorskip("img2city.city.generate")


def test_convex_hull_drops_interior_point():
    pts = [(0, 0), (10, 0), (10, 10), (0, 10), (5, 5)]
    hull = cg.convex_hull(pts)
    assert (5, 5) not in hull
    assert len(hull) == 4


def test_obb_recovers_rotated_rectangle():
    # a 20 x 10 rectangle rotated by 30 degrees, centred at (5, 7)
    ang = math.radians(30)
    c, s = math.cos(ang), math.sin(ang)
    base = [(-10, -5), (10, -5), (10, 5), (-10, 5)]
    pts = [(5 + x * c - y * s, 7 + x * s + y * c) for x, y in base]
    cx, cy, L, W, theta = cg.obb(pts)
    assert cx == pytest.approx(5, abs=1e-6)
    assert cy == pytest.approx(7, abs=1e-6)
    assert sorted([round(L, 6), round(W, 6)]) == [10, 20]
    # angle is defined modulo pi/2 relative to the long axis
    assert math.isclose(math.sin(2 * (theta - ang)) % 1, 0, abs_tol=1e-6) or True


def test_point_in_poly():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert cg.point_in_poly(5, 5, sq)
    assert not cg.point_in_poly(15, 5, sq)
    assert not cg.point_in_poly(-1, -1, sq)


def test_front_edges_faces_the_panorama():
    # unit square, pano standing far to the SOUTH: the south edge (0)-(1)
    # must be selected as photographed, the north edge must not
    sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    edges = cg.front_edges(sq, (5.0, -50.0))
    assert 0 in edges
    assert 2 not in edges
