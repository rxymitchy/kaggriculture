import unittest

from kaggle_environments.envs.kaggriculture import kaggriculture as envmod
from kaggle_environments import make

from kag.constants import CROPS
from main import agent


class TestEnvParity(unittest.TestCase):
    def test_melon_max_yield_day_is_12_in_installed_env(self):
        self.assertEqual(envmod.CROPS["MELON"]["max_yield_day"], 12)
        self.assertEqual(CROPS["MELON"]["max_yield_day"], 12)

    def test_shop_names_underscored(self):
        self.assertIn("PIZZA_SHOP", envmod.SHOPS)
        self.assertIn("FARMERS_MARKET", envmod.SHOPS)

    def test_act_timeout_is_one_second(self):
        spec = envmod.specification
        self.assertEqual(spec["configuration"]["actTimeout"], 1)

    def test_agent_completes_short_episode(self):
        e = make("kaggriculture", configuration={"episodeSteps": 48, "seed": 7}, debug=True)
        e.run([agent, "pass"])
        final = e.steps[-1]
        self.assertEqual(final[0]["status"], "DONE")
        self.assertGreaterEqual(final[0]["reward"], 0)


class TestPlantWaterSurvival(unittest.TestCase):
    def test_new_plant_starts_unwatered_one(self):
        plant = envmod._new_plant("WHEAT", 0, 24)
        self.assertEqual(plant["consecutive_unwatered"], 1)
        self.assertEqual(plant["yield_units"], 1)

    def test_new_animal_starts_unfed_zero(self):
        a = envmod._new_animal("GOOSE", 0)
        self.assertEqual(a["consecutive_unfed"], 0)
        self.assertNotIn("animal", envmod._new_animal.__doc__ or "")
        self.assertEqual(a["animal"], "GOOSE")


if __name__ == "__main__":
    unittest.main()
