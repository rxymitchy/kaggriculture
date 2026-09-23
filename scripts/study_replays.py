"""Summarize how each player played in Kaggriculture replay JSON."""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict

PATHS = [
    r"c:\Users\Administrator\Downloads\112268530.json",
    r"c:\Users\Administrator\Downloads\112275602.json",
    r"c:\Users\Administrator\Downloads\112282976.json",
]


def tile_kind(t):
    if t is None:
        return "empty"
    if t == "LOCKED":
        return "locked"
    if not isinstance(t, dict):
        return str(t)
    if t.get("kind") == "PLANT":
        return "plant:" + str(t.get("crop"))
    if t.get("animal"):
        return "animal:" + str(t.get("animal"))
    return t.get("kind", "?")


def farm_snapshot(farm):
    crops = Counter()
    animals = Counter()
    kinds = Counter()
    for row in farm["tiles"]:
        for t in row:
            k = tile_kind(t)
            kinds[k.split(":")[0] if k != "locked" else "locked"] += 1
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                crops[t.get("crop")] += 1
            if isinstance(t, dict) and t.get("animal"):
                animals[t.get("animal")] += 1
    return {
        "money": farm["money"],
        "unlocked": list(farm.get("unlocked_quadrants", [])),
        "hands": len(farm.get("hands", [])),
        "hires": farm.get("hires_today", 0),
        "crops": dict(crops),
        "animals": dict(animals),
        "empty": kinds.get("empty", 0),
        "weeds": kinds.get("WEED", 0),
        "locked": kinds.get("locked", 0),
        "coop": kinds.get("COOP", 0),
        "pasture": kinds.get("PASTURE", 0),
    }


def analyze(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    names = data.get("info", {}).get("TeamNames") or [a.get("Name") for a in data.get("info", {}).get("Agents", [])]
    rewards = data["rewards"]
    winner = 0 if rewards[0] > rewards[1] else (1 if rewards[1] > rewards[0] else None)
    steps = data["steps"]

    daily = []
    action_ops = [Counter(), Counter()]
    market_ops = [Counter(), Counter()]
    market_items = [defaultdict(lambda: Counter()), defaultdict(lambda: Counter())]
    hire_by_day = [Counter(), Counter()]
    land_days = [[], []]
    firsts = [{}, {}]

    for si, step in enumerate(steps):
        obs = step[0]["observation"]
        day = obs.get("day", si // 24)
        hour = obs.get("hour", si % 24)
        if hour == 0 or si == 0 or si == len(steps) - 1:
            daily.append((si, day, hour, [farm_snapshot(obs["farms"][0]), farm_snapshot(obs["farms"][1])]))

        if si == 0:
            continue
        for p in (0, 1):
            act = step[p].get("action") or {}
            farmer = act.get("farmer") or ["PASS"]
            op = farmer[0] if farmer else "PASS"
            action_ops[p][op] += 1
            for h in act.get("hands") or []:
                if h:
                    action_ops[p][h[0]] += 1
            for m in act.get("market") or []:
                if not m:
                    continue
                mop = m[0]
                market_ops[p][mop] += 1
                if mop == "HIRE":
                    hire_by_day[p][day] += 1
                elif mop == "BUY_LAND":
                    land_days[p].append(day)
                elif len(m) >= 2:
                    item = m[1]
                    n = m[2] if len(m) >= 3 else 1
                    try:
                        n = int(n)
                    except Exception:
                        n = 1
                    market_items[p][mop][item] += n
                    if mop not in firsts[p]:
                        firsts[p][mop] = (day, hour, m)

    # last obs money already in rewards
    last_obs = steps[-1][0]["observation"]
    last_farms = [farm_snapshot(last_obs["farms"][i]) for i in range(2)]
    shops = last_obs.get("town", {}).get("unlocked_shops", [])
    prices = last_obs.get("market", {}).get("prices", {})

    # money trajectory at start of each day
    money_days = []
    for si, step in enumerate(steps):
        obs = step[0]["observation"]
        if obs.get("hour", 1) == 0:
            money_days.append((obs.get("day"), [obs["farms"][0]["money"], obs["farms"][1]["money"]]))

    print("=" * 72)
    print(os.path.basename(path), "episode", data.get("info", {}).get("EpisodeId"))
    print("players:", names)
    print("final $:", rewards, "winner:", names[winner] if winner is not None else "TIE", f"(P{winner})")
    print("status", data["statuses"], "shops", shops)
    print("end prices", {k: prices.get(k) for k in ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]})

    for p in (0, 1):
        tag = "WIN" if p == winner else "lose"
        print(f"\n--- P{p} {names[p]} [{tag}] end state ---")
        print(last_farms[p])
        print("worker ops", dict(action_ops[p].most_common()))
        print("market ops", dict(market_ops[p]))
        for mop, c in market_items[p].items():
            print(f"  {mop}", dict(c))
        print("hires/day", dict(sorted(hire_by_day[p].items())) , "total", sum(hire_by_day[p].values()))
        print("BUY_LAND days", land_days[p])
        print("first market", firsts[p])

    print("\nMoney by day (P0, P1):")
    for d, m in money_days:
        if d in (0, 1, 2, 3, 5, 8, 12, 16, 20, 24, 28, 29) or d % 5 == 0:
            print(f"  day {d:2d}: {m[0]:8.0f}  {m[1]:8.0f}")

    print("\nFarm composition selected days:")
    seen = set()
    for si, day, hour, snaps in daily:
        if hour != 0 and si != len(steps) - 1:
            continue
        if day in seen and si != len(steps) - 1:
            continue
        if day not in (0, 1, 2, 3, 5, 8, 12, 20, 29) and si != len(steps) - 1:
            continue
        seen.add(day)
        for p in (0, 1):
            s = snaps[p]
            print(f"  d{day} P{p} ${s['money']:.0f} land={s['unlocked']} hands={s['hands']} crops={s['crops']} animals={s['animals']} empty={s['empty']} weeds={s['weeds']}")


def main():
    for p in PATHS:
        analyze(p)


if __name__ == "__main__":
    main()
