"""Play one game with the unbundled ranch agent and print a daily trace (crashes are not hidden)."""

from __future__ import annotations

import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kaggle_environments import make  # noqa: E402

from kag.ranch import RanchAgent  # noqa: E402
from scripts.pool_eval import ensure_git_opponents, load_agent  # noqa: E402


def main():
    opp = sys.argv[1] if len(sys.argv) > 1 else "starter"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    ensure_git_opponents()
    brain = RanchAgent()
    ops = Counter()

    sold = Counter()
    overflow = Counter()

    times = []

    def agent(obs, config=None):
        t0 = time.perf_counter()
        out = brain.act(obs, config)
        times.append(time.perf_counter() - t0)
        for a in [out["farmer"], *out["hands"]]:
            ops[a[0] if a[0] not in ("NORTH", "SOUTH", "EAST", "WEST") else "MOVE"] += 1
        for o in out["market"]:
            if o[0] == "SELL":
                sold[o[1]] += o[2]
            elif o[0] in ("BUY_ANIMAL", "BUY_SEED", "BUY_PRODUCT"):
                sold["buy_" + o[1]] += o[2]
            else:
                sold[o[0]] += 1
        if obs.hour == 23:
            pv = obs.private
            total = sum(pv["shed"].values()) + sum(sum(inv.values()) for inv in pv["inventories"])
            if total > 100:
                overflow[obs.day] = total - 100
        return out

    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    env.run([agent, load_agent(opp)])
    for day in range(0, 30, 2):
        st = env.steps[day * 24 + 23][0].observation
        me, op = st.farms[0], st.farms[1]
        animals = Counter()
        plants = Counter()
        for row in me["tiles"]:
            for t in row:
                if isinstance(t, dict) and "animal" in t:
                    animals[t["animal"]] += 1
                elif isinstance(t, dict) and t.get("kind") == "PLANT":
                    plants[t["crop"]] += 1
        prices = st.market["prices"]
        print(
            f"d{day:2d} me ${me['money']:>7,.0f} opp ${op['money']:>7,.0f} quads {len(me['unlocked_quadrants'])} "
            f"hands {len(me['hands'])} animals {dict(animals)} plants {dict(plants)} "
            f"egg {prices['EGG']} milk {prices['MILK']} fert {prices['FERTILIZER']} wheat {prices['WHEAT']}"
        )
    final = env.steps[-1]
    print("final", [s.reward for s in final], [s.status for s in final])
    print("ops", dict(ops.most_common()))
    print("orders (sell units / buys)", dict(sold.most_common()))
    print("night overflow by day (units lost)", dict(overflow))
    print(f"act time: max {max(times) * 1000:.1f} ms, mean {sum(times) / len(times) * 1000:.1f} ms")


if __name__ == "__main__":
    main()
