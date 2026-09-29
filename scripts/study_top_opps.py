"""Day-by-day plan of the strongest opponents in a replay folder."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from glob import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_my_replays import farm_counts, guess_us, names_of, short  # noqa: E402


def study(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    names = names_of(data)
    us = guess_us(names)
    p = 1 - us
    steps = data["steps"]
    print("=" * 80)
    print(os.path.basename(path), short(names[p], 30), "final", data["rewards"][p], "vs us", data["rewards"][us])
    buys = defaultdict(Counter)
    hires = Counter()
    for si, step in enumerate(steps):
        obs = step[0]["observation"]
        day = obs.get("day", si // 24)
        act = step[p].get("action") or {}
        for m in act.get("market") or []:
            if not m:
                continue
            if m[0] == "HIRE":
                hires[day] += 1
            elif m[0] == "BUY_LAND":
                buys[day]["LAND"] += 1
            elif m[0] in ("BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT") and len(m) > 1:
                n = int(m[2]) if len(m) > 2 else 1
                buys[day][f"{m[0][4:]}:{m[1]}"] += n
    for si, step in enumerate(steps):
        obs = step[0]["observation"]
        if obs.get("hour") != 0:
            continue
        day = obs["day"]
        if day > 16 and day % 4:
            continue
        s = farm_counts(obs["farms"][p])
        print(
            f" d{day:02d} ${s['money']:7.0f} land={s['land']} hands={s['hands']} plants={s['plants']} "
            f"crops={s['crops']} ani={s['animals']} empty={s['empty']} hires={hires.get(day, 0)} buys={dict(buys.get(day, {}))}"
        )


def main():
    folder = sys.argv[1]
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    rows = []
    for path in glob(os.path.join(folder, "*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        us = guess_us(names_of(data))
        rows.append((data["rewards"][1 - us], path))
    rows.sort(reverse=True)
    for _, path in rows[:top]:
        study(path)


if __name__ == "__main__":
    main()
