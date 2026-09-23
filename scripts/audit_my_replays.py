"""Audit our Kaggle replays: money curve, leaks, vs opponent."""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from glob import glob

FOLDER = r"c:\Users\Administrator\Downloads\my replays"


def names_of(data):
    info = data.get("info") or {}
    n = info.get("TeamNames")
    if n:
        return list(n)
    agents = info.get("Agents") or []
    return [a.get("Name") or a.get("SubmissionName") or "?" for a in agents]


def guess_us(names):
    for i, n in enumerate(names):
        s = (n or "").lower()
        if any(k in s for k in ("rxymitchy", "kag", "agr", "mitch", "farm")):
            return i
    return 0


def short(s, n=18):
    t = "".join(ch if ord(ch) < 128 else "?" for ch in str(s))
    return t[:n]


def farm_counts(farm):
    crops, animals = Counter(), Counter()
    empty = weeds = uw = uf = plants = 0
    for row in farm.get("tiles") or []:
        for t in row:
            if t is None:
                empty += 1
            elif t == "LOCKED":
                continue
            elif isinstance(t, dict):
                if t.get("kind") == "WEED":
                    weeds += 1
                if t.get("kind") == "PLANT":
                    plants += 1
                    crops[t.get("crop")] += 1
                    if not t.get("watered_today") and t.get("consecutive_unwatered", 0) >= 1:
                        uw += 1
                if t.get("animal"):
                    animals[t.get("animal")] += 1
                    if not t.get("fed_today") and t.get("consecutive_unfed", 0) >= 1:
                        uf += 1
    return {
        "money": farm.get("money", 0),
        "land": len(farm.get("unlocked_quadrants") or []),
        "hands": len(farm.get("hands") or []),
        "crops": dict(crops),
        "animals": dict(animals),
        "empty": empty,
        "weeds": weeds,
        "uw": uw,
        "uf": uf,
        "plants": plants,
        "n_ani": sum(animals.values()),
    }


def priv_of(step, player):
    # private is on this player's observation
    obs = step[player].get("observation") or step[0].get("observation") or {}
    return obs.get("private") or {}


def analyze(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    names = names_of(data)
    rewards = data["rewards"]
    steps = data["steps"]
    us = guess_us(names)
    them = 1 - us
    n_steps = len(steps)

    money = [[], []]
    crops_by_day = []
    leaks = Counter()
    market = [Counter(), Counter()]
    bought = [defaultdict(Counter), defaultdict(Counter)]
    sold = [Counter(), Counter()]
    ops = [Counter(), Counter()]
    last_shed = [{}, {}]
    last_priv = [{}, {}]
    land_days = [[], []]
    animals_deadish = 0
    max_uw = 0
    max_uf = 0
    first_us_cash_day = None
    first_us_1k = None
    first_us_5k = None

    for si, step in enumerate(steps):
        obs = step[0]["observation"]
        day = obs.get("day", si // 24)
        hour = obs.get("hour", si % 24)
        farms = obs["farms"]
        if hour == 0:
            for p in (0, 1):
                money[p].append((day, farms[p]["money"]))
            snap = farm_counts(farms[us])
            crops_by_day.append((day, snap))
            max_uw = max(max_uw, snap["uw"])
            max_uf = max(max_uf, snap["uf"])
            if snap["uf"] >= 2:
                leaks["uf_days"] += 1
            if snap["uw"] >= 8:
                leaks["uw_days"] += 1
            if snap["weeds"] >= 4:
                leaks["weed_days"] += 1
            m = farms[us]["money"]
            if first_us_cash_day is None and m >= 200 and day > 0:
                first_us_cash_day = day
            if first_us_1k is None and m >= 1000:
                first_us_1k = day
            if first_us_5k is None and m >= 5000:
                first_us_5k = day
        if si == 0:
            continue
        for p in (0, 1):
            act = step[p].get("action") or {}
            farmer = act.get("farmer") or ["PASS"]
            ops[p][farmer[0] if farmer else "PASS"] += 1
            for h in act.get("hands") or []:
                if h:
                    ops[p][h[0]] += 1
            for m in act.get("market") or []:
                if not m:
                    continue
                market[p][m[0]] += 1
                if m[0] == "BUY_LAND":
                    land_days[p].append(day)
                item = m[1] if len(m) > 1 else None
                n = m[2] if len(m) > 2 else 1
                try:
                    n = int(n)
                except Exception:
                    n = 1
                if m[0] in ("BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT") and item:
                    bought[p][m[0]][item] += n
                if m[0] == "SELL" and item:
                    sold[p][item] += n

    last = steps[-1][0]["observation"]
    last_us = farm_counts(last["farms"][us])
    last_them = farm_counts(last["farms"][them])
    priv = None
    # private lives on the acting player's obs; try both
    for p in (us, 0, 1):
        pr = (steps[-1][p].get("observation") or {}).get("private")
        if pr:
            priv = pr
            break
    shed = {k: v for k, v in (priv or {}).get("shed", {}).items() if v} if priv else {}
    seeds = {k: v for k, v in (priv or {}).get("seeds", {}).items() if v} if priv else {}

    us_m = [m for _, m in money[us]]
    them_m = [m for _, m in money[them]]
    gap = []
    for (d, a), (_, b) in zip(money[us], money[them]):
        gap.append((d, a - b, a, b))

    def at(day):
        for d, m in money[us]:
            if d == day:
                return m
        return us_m[-1] if us_m else 0

    def at_them(day):
        for d, m in money[them]:
            if d == day:
                return m
        return them_m[-1] if them_m else 0

    return {
        "file": os.path.basename(path),
        "ep": (data.get("info") or {}).get("EpisodeId"),
        "names": names,
        "us": us,
        "us_name": names[us] if us < len(names) else "?",
        "them_name": names[them] if them < len(names) else "?",
        "us_final": rewards[us],
        "them_final": rewards[them],
        "win": rewards[us] > rewards[them],
        "status": data.get("statuses"),
        "d0": at(0),
        "d3": at(3),
        "d5": at(5),
        "d8": at(8),
        "d12": at(12),
        "d20": at(20),
        "d29": at(29) if any(d == 29 for d, _ in money[us]) else at(28),
        "them_d5": at_them(5),
        "them_d8": at_them(8),
        "them_d12": at_them(12),
        "them_d20": at_them(20),
        "them_d29": at_them(29) if any(d == 29 for d, _ in money[them]) else at_them(28),
        "first_200": first_us_cash_day,
        "first_1k": first_us_1k,
        "first_5k": first_us_5k,
        "max_uw": max_uw,
        "max_uf": max_uf,
        "leaks": dict(leaks),
        "last_us": last_us,
        "last_them": last_them,
        "end_shed": shed,
        "end_seeds": seeds,
        "bought": {k: dict(v) for k, v in bought[us].items()},
        "sold": dict(sold[us]),
        "bought_them": {k: dict(v) for k, v in bought[them].items()},
        "sold_them": dict(sold[them]),
        "ops": dict(ops[us].most_common(8)),
        "ops_them": dict(ops[them].most_common(8)),
        "market": dict(market[us]),
        "land": land_days[us],
        "land_them": land_days[them],
        "crops_sample": [(d, s["crops"], s["animals"], s["plants"], s["n_ani"], s["empty"], s["uw"], s["uf"]) for d, s in crops_by_day if d in (0, 2, 5, 8, 12, 20, 29)],
        "gap_d8": at(8) - at_them(8),
        "gap_d12": at(12) - at_them(12),
        "gap_d20": at(20) - at_them(20),
        "gap_end": rewards[us] - rewards[them],
        "n_steps": n_steps,
    }


def main():
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments", "replay_audit.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    class Tee:
        def __init__(self, *streams):
            self.streams = streams
        def write(self, s):
            for st in self.streams:
                st.write(s)
            return len(s)
        def flush(self):
            for st in self.streams:
                st.flush()

    import sys
    f = open(out, "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, f)
    paths = sorted(glob(os.path.join(FOLDER, "*.json")))
    print(f"found {len(paths)} replays in {FOLDER}")
    rows = []
    for p in paths:
        print("reading", os.path.basename(p), flush=True)
        rows.append(analyze(p))

    # identity check
    print("\n=== identity / W-L ===")
    name_counts = Counter(r["us_name"] for r in rows)
    print("guessed-us names", dict(name_counts))
    wins = sum(1 for r in rows if r["win"])
    print(f"W-L {wins}-{len(rows)-wins}  avg us ${sum(r['us_final'] for r in rows)/len(rows):.0f}  avg opp ${sum(r['them_final'] for r in rows)/len(rows):.0f}")

    print("\n=== each episode ===")
    print(f"{'file':16} {'us':10} {'opp':18} {'us$':>8} {'opp$':>8} {'d5':>6} {'d8':>6} {'d12':>7} {'d20':>7} {'gap8':>7} {'gapE':>8} W uw uf land")
    for r in rows:
        print(
            f"{r['file'][:16]:16} {short(r['us_name'],10):10} {short(r['them_name'],18):18} "
            f"{r['us_final']:8.0f} {r['them_final']:8.0f} {r['d5']:6.0f} {r['d8']:6.0f} {r['d12']:7.0f} {r['d20']:7.0f} "
            f"{r['gap_d8']:7.0f} {r['gap_end']:8.0f} {'W' if r['win'] else 'L'} {r['max_uw']:2d} {r['max_uf']:2d} {r['land']}"
        )

    def avg(key):
        return sum(r[key] for r in rows) / len(rows)

    print("\n=== average money curve (us vs opp) ===")
    for k, tk in [("d3", None), ("d5", "them_d5"), ("d8", "them_d8"), ("d12", "them_d12"), ("d20", "them_d20"), ("d29", "them_d29")]:
        if tk:
            print(f"  {k:4} us ${avg(k):7.0f}  opp ${avg(tk):7.0f}  gap ${avg(k)-avg(tk):7.0f}")
        else:
            print(f"  {k:4} us ${avg(k):7.0f}")
    print(f"  end  us ${avg('us_final'):7.0f}  opp ${avg('them_final'):7.0f}  gap ${avg('gap_end'):7.0f}")

    print("\n=== first cash ===")
    print("  first >=$200 day", Counter(r["first_200"] for r in rows))
    print("  first >=$1k day", Counter(r["first_1k"] for r in rows))
    print("  first >=$5k day", Counter(r["first_5k"] for r in rows))

    print("\n=== leaks ===")
    print("  avg max_uw", sum(r["max_uw"] for r in rows)/len(rows))
    print("  avg max_uf", sum(r["max_uf"] for r in rows)/len(rows))
    print("  leak flags", Counter(tuple(sorted(r["leaks"].items())) for r in rows))

    print("\n=== buys (us totals across games) ===")
    seed_tot = Counter()
    ani_tot = Counter()
    prod_tot = Counter()
    sell_tot = Counter()
    for r in rows:
        seed_tot.update(r["bought"].get("BUY_SEED", {}))
        ani_tot.update(r["bought"].get("BUY_ANIMAL", {}))
        prod_tot.update(r["bought"].get("BUY_PRODUCT", {}))
        sell_tot.update(r["sold"])
    print("  seeds", dict(seed_tot))
    print("  animals", dict(ani_tot))
    print("  products", dict(prod_tot))
    print("  sold", dict(sell_tot))

    print("\n=== opp buys ===")
    oseed = Counter()
    oani = Counter()
    osell = Counter()
    for r in rows:
        oseed.update(r["bought_them"].get("BUY_SEED", {}))
        oani.update(r["bought_them"].get("BUY_ANIMAL", {}))
        osell.update(r["sold_them"])
    print("  seeds", dict(oseed))
    print("  animals", dict(oani))
    print("  sold", dict(osell))

    print("\n=== end shed (us, games with leftover) ===")
    for r in rows:
        if r["end_shed"]:
            print(f"  {r['file']} win={r['win']} shed={r['end_shed']} seeds={r['end_seeds']} crops={r['last_us']['crops']} ani={r['last_us']['animals']}")

    print("\n=== farm samples (us) ===")
    for r in rows[:6]:
        print(short(r["file"]), short(r["us_name"], 20), "vs", short(r["them_name"], 24), "W" if r["win"] else "L")
        for row in r["crops_sample"]:
            print("   ", row)

    print("\n=== our worker ops vs theirs (avg counts) ===")
    our_ops = Counter()
    their_ops = Counter()
    for r in rows:
        our_ops.update(r["ops"])
        their_ops.update(r["ops_them"])
    print("  us", dict(our_ops))
    print("  opp", dict(their_ops))


if __name__ == "__main__":
    main()
