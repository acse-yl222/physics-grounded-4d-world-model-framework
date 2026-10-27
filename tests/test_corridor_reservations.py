"""Prevent admission while a long vehicle's rear still occupies a short-link junction."""

import unittest
from types import SimpleNamespace

from traffic.corridor_reservations import junction_occupants


class ReservationTests(unittest.TestCase):
    def test_bus_rear_on_short_outgoing_link_blocks_previous_junction(self):
        keys = SimpleNamespace(VAR_LANE_ID="lane", VAR_ROAD_ID="edge", VAR_LANEPOSITION="pos")
        states = {
            "bus": {"lane": "out_0", "edge": "out", "pos": 6.5},
            "car": {"lane": ":other_0_0", "edge": ":other_0", "pos": 2},
        }
        occupied = junction_occupants(
            states, {"bus": 10.5, "car": 4.5}, {"out": "previous"}, {":other_0_0": "other"}, keys
        )
        self.assertEqual(occupied, {"previous": {"bus"}, "other": {"car"}})
        states["bus"]["pos"] = 20
        self.assertNotIn(
            "previous",
            junction_occupants(
                states,
                {"bus": 10.5, "car": 4.5},
                {"out": "previous"},
                {":other_0_0": "other"},
                keys,
            ),
        )

    def test_short_links_share_one_conflict_area(self):
        import xml.etree.ElementTree as ET

        from traffic.corridor_reservations import junction_groups

        root = ET.fromstring(
            '<net><edge id="a" from="J1" to="J2"><lane length="7"/></edge><edge id="b" from="J2" to="J3"><lane length="150"/></edge></net>'
        )
        groups = junction_groups(root)
        self.assertEqual(groups["J1"], groups["J2"])
        self.assertNotEqual(groups["J2"], groups["J3"])
