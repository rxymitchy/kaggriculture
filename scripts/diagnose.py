from collections import Counter
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kaggle_environments import make

from main import agent


def snapshot(obs, farm_i=0):
    farm = obs["farms"][farm_i]
    priv = obs["private"]
    kinds = Counter()
    crops = Counter()
    animals = Counter()
    unwatered_critical = 0
    unfed_critical = 0
    for row in farm["tiles"]:
        for t in row:
            if t is None:
                kinds["empty"] += 1
            elif t == "LOCKED":
                kinds["locked"] += 1
            elif isinstance(t, dict):
                kinds[t.get("kind", "?")] += 1
                if t.get("kind") == "PLANT":
                    crops[t.get("crop")] += 1
                    if not t.get("watered_today") and t.get("consecutive_unwatered", 0) >= 1:
                        unwatered_critical += 1
                if t.get("animal"):
                    animals[t.get("animal")] += 1
                    if not t.get("fed_today") and t.get("consecutive_unfed", 0) >= 1:
                        unfed_critical += 1
    return {
        "money": farm["money"],
        "unlocked": farm["unlocked_quadrants"],
        "hands": len(farm["hands"]),
        "kinds": dict(kinds),
        "crops": dict(crops),
        "animals": dict(animals),
        "shed": {k: v for k, v in priv["shed"].items() if v},
        "seeds": {k: v for k, v in priv["seeds"].items() if v},
        "inv": priv["inventories"],
        "uw": unwatered_critical,
        "uf": unfed_critical,
    }


def main():
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1}, debug=False)
    env.run([agent, "pass"])
    for day in [0, 1, 2, 3, 5, 8, 12, 20, 29]:
        step = min(day * 24, len(env.steps) - 1)
        obs = env.steps[step][0]["observation"]
        snap = snapshot(obs)
        print(
            f"day={day} money={snap['money']:.0f} unlock={snap['unlocked']} hands={snap['hands']} "
            f"crops={snap['crops']} animals={snap['animals']} shed={snap['shed']} seeds={snap['seeds']} "
            f"uw={snap['uw']} uf={snap['uf']} inv={snap['inv']}"
        )
    print("final", env.steps[-1][0]["reward"], env.steps[-1][1]["reward"])
    # first 30 actions
    print("first farmer actions:")
    for i in range(min(30, len(env.steps) - 1)):
        act = env.steps[i + 1][0].get("action") or env.steps[i][0].get("action")
    # actions are stored on the step after they're taken; inspect env.steps[i][0]['action']
    for i in range(min(40, len(env.steps))):
        a = env.steps[i][0].get("action")
        if a:
            print(i, a.get("farmer"), "mkt", a.get("market"), "hands", a.get("hands"))


if __name__ == "__main__":
    main()
