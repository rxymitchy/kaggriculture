"""Unit tests for mechanics mirrored from installed kaggriculture 1.32.7."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from kag.constants import (
    CROPS,
    MARKET_I0,
    PRICE_FLOOR,
    fib,
    hire_cost,
    market_price,
    shed_access_tiles,
    watering_window,
)
from kag.economy import expected_one_time_yield, expected_ongoing_yield
from kag.movement import bfs_next_step, manhattan
from kag.state import parse_state


class TestMarket(unittest.TestCase):
    def test_price_at_i0_is_base(self):
        self.assertEqual(market_price("WHEAT", MARKET_I0), 25)
        self.assertEqual(market_price("MELON", MARKET_I0), 250)
        self.assertEqual(market_price("EGG", MARKET_I0), 50)

    def test_floor(self):
        self.assertGreaterEqual(market_price("MELON", MARKET_I0 + 5000), PRICE_FLOOR)

    def test_matches_installed_env(self):
        from kaggle_environments.envs.kaggriculture.kaggriculture import market_price as env_price

        for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"):
            for inv in (8000, 10000, 10100, 10300, 11000):
                self.assertEqual(market_price(item, inv), env_price(item, inv), (item, inv))

    def test_table_points(self):
        # Spec table P(I0-T), P(I0+T) — allow ±1 for rounding.
        self.assertAlmostEqual(market_price("WHEAT", MARKET_I0 - 400), 45, delta=1)
        self.assertAlmostEqual(market_price("WHEAT", MARKET_I0 + 400), 20, delta=1)


class TestHireLand(unittest.TestCase):
    def test_fib(self):
        self.assertEqual([fib(i) for i in range(8)], [1, 1, 2, 3, 5, 8, 13, 21])

    def test_hire_cost(self):
        self.assertEqual(hire_cost(0), 1)
        self.assertEqual(hire_cost(4), 5)

    def test_shed_tiles(self):
        self.assertEqual(shed_access_tiles(10), [(4, 4), (5, 4), (4, 5), (5, 5)])


class TestCropWindows(unittest.TestCase):
    def test_wheat_window(self):
        self.assertEqual(watering_window("WHEAT"), (2, 4))

    def test_melon_window_uses_code_max_yield_day_12(self):
        self.assertEqual(CROPS["MELON"]["max_yield_day"], 12)
        self.assertEqual(watering_window("MELON"), (6, 12))

    def test_melon_unfertilized_caps_at_age_10(self):
        units, days = expected_one_time_yield("MELON", 30, fertilized=False)
        self.assertEqual(units, 6)
        self.assertEqual(days, 10)

    def test_wheat_unfertilized_cap_4(self):
        units, days = expected_one_time_yield("WHEAT", 30, False)
        self.assertEqual(units, 4)

    def test_strawberry_four_yields(self):
        units, days = expected_ongoing_yield("STRAWBERRY", 30, False)
        self.assertEqual(units, 4)

    def test_late_melon_skipped(self):
        units, _ = expected_one_time_yield("MELON", 8, False)
        self.assertEqual(units, 0)


class TestMovement(unittest.TestCase):
    def test_east(self):
        self.assertEqual(bfs_next_step((0, 0), (3, 0), 10), "EAST")

    def test_south(self):
        self.assertEqual(bfs_next_step((4, 4), (4, 7), 10), "SOUTH")

    def test_here(self):
        self.assertIsNone(bfs_next_step((1, 1), (1, 1), 10))

    def test_manhattan(self):
        self.assertEqual(manhattan((4, 4), (5, 4)), 1)


class TestParse(unittest.TestCase):
    def test_parse_minimal(self):
        obs = {
            "player": 0,
            "step": 5,
            "day": 0,
            "hour": 5,
            "farms": [
                {
                    "money": 3000,
                    "tiles": [[None] * 10 for _ in range(10)],
                    "farmer": [4, 4],
                    "hands": [[5, 4]],
                    "unlocked_quadrants": ["NW"],
                    "hires_today": 1,
                },
                {
                    "money": 2900,
                    "tiles": [[None] * 10 for _ in range(10)],
                    "farmer": [4, 4],
                    "hands": [],
                    "unlocked_quadrants": ["NW"],
                    "hires_today": 0,
                },
            ],
            "market": {"inventory": {"WHEAT": 10000}, "prices": {"WHEAT": 25}},
            "town": {"unlocked_shops": ["BAKERY", "BAKERY"]},
            "private": {
                "shed": {"WHEAT": 3},
                "seeds": {"WHEAT": 2},
                "inventories": [{}, {}],
            },
        }
        st = parse_state(obs)
        self.assertEqual(st.player, 0)
        self.assertEqual(st.money, 3000)
        self.assertEqual(st.seed_count("WHEAT"), 2)
        self.assertEqual(st.shops, ["BAKERY", "BAKERY"])
        self.assertEqual(len(st.workers), 2)


if __name__ == "__main__":
    unittest.main()
