"""Print the ranch planner's view at chosen steps of one game (debug aid)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kaggle_environments import make  # noqa: E402

from kag.constants import ANIMALS  # noqa: E402
from kag.ranch import Outlook, RanchAgent  # noqa: E402
from kag.state import parse_state  # noqa: E402
from scripts.pool_eval import ensure_git_opponents, load_agent  # noqa: E402


def main():
    opp = sys.argv[1] if len(sys.argv) > 1 else "v5"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    steps = {int(s) for s in (sys.argv[3] if len(sys.argv) > 3 else "245,341,437").split(",")}
    ensure_git_opponents()
    brain = RanchAgent()

    def agent(obs, config=None):
        out = brain.act(obs, config)
        if obs.step in steps:
            st = parse_state(obs, config)
            ol = Outlook(st, brain.cfg)
            plan = brain._plan_tiles(st, ol)
            vals = {a: round(ol.animal_value(a, brain.cfg)) for a in ANIMALS}
            print(f"step {obs.step} day {st.day} money {st.money:.0f} empty {len(st.me.empty)} weeds {len(st.me.weeds)} "
                  f"plants {len(st.me.plants)} animals {len(st.me.animals)} seeds {dict(st.seeds)}")
            print("  values", vals, "wanted", len(plan["wanted"]), "zone", len(plan["animal_zone"]),
                  "crop_tiles", len(plan["crop_tiles"]), "builds", len(plan["builds"]))
            print("  prices", {k: st.market_prices[k] for k in ("EGG", "MILK", "WOOL", "FERTILIZER", "WHEAT", "CARROT")},
                  "fcst", {k: round(ol.price(k)) for k in ("EGG", "MILK", "WOOL", "FERTILIZER")}, "wheat_fc", round(ol.wheat_price()))
            print("  market", out["market"])
            jobs = brain._jobs(st, ol, plan)
            print("  plant jobs", [(j.pos, j.action) for j in jobs if j.action[0] == "PLANT"][:6])
            print("  crop tiles", plan["crop_tiles"][:8])
            print("  actions", out["farmer"], out["hands"], [w.pos for w in st.workers])
        return out

    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    env.run([agent, load_agent(opp)])


if __name__ == "__main__":
    main()
