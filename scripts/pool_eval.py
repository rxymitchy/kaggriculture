"""Evaluate a single-file agent against a pool of different opponents.

Usage: python scripts/pool_eval.py [candidate.py] [n_seeds] [opp1,opp2,...]

Opponents: starter, v4, v5, v6 (old versions pulled from git), self (mirror
match on a shared market), or any path to a .py file. Every seed is played
in both seats so neither side gets a lucky starting position.
"""

from __future__ import annotations

import os
import subprocess
import sys
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPP_DIR = os.path.join(ROOT, "opponents")
GIT_VERSIONS = {"v4": "55514ad", "v5": "36f1ae3", "v6": "1210e75"}


def ensure_git_opponents():
    os.makedirs(OPP_DIR, exist_ok=True)
    for name, sha in GIT_VERSIONS.items():
        path = os.path.join(OPP_DIR, f"{name}.py")
        if os.path.exists(path):
            continue
        src = subprocess.check_output(["git", "show", f"{sha}:main.py"], cwd=ROOT)
        with open(path, "wb") as f:
            f.write(src)


def load_agent(spec: str):
    if spec == "starter":
        return "starter"
    if spec.startswith("ranch"):
        sys.path.insert(0, ROOT)
        from kag.ranch import RanchAgent, RanchConfig

        cfg = RanchConfig()
        for kv in filter(None, spec.partition(":")[2].split("+")):
            k, v = kv.split("=")
            setattr(cfg, k, type(getattr(cfg, k))(v))
        brain = RanchAgent(cfg)
        return lambda obs, config=None: brain.act(obs, config)
    path = os.path.join(OPP_DIR, f"{spec}.py") if spec in GIT_VERSIONS else spec
    with open(path, encoding="utf-8-sig") as f:
        src = f.read()
    import types

    mod_name = f"kaggle_agent_{abs(hash(path))}_{len(sys.modules)}"
    mod = types.ModuleType(mod_name)
    sys.modules[mod_name] = mod
    ns = mod.__dict__
    exec(compile(src, path, "exec"), ns)
    if callable(ns.get("agent")):
        return ns["agent"]
    fns = [v for v in ns.values() if callable(v) and getattr(v, "__module__", None) == mod_name]
    return fns[-1]


def play(job):
    cand, opp, seed, seat = job
    from kaggle_environments import make

    a = load_agent(cand)
    b = load_agent(cand if opp == "self" else opp)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([a, b] if seat == 0 else [b, a])
    final = env.steps[-1]
    r = [float(s.reward or 0) for s in final]
    me, them = (r[0], r[1]) if seat == 0 else (r[1], r[0])
    status = final[seat].status
    return opp, seed, seat, me, them, status


def main():
    cand = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "main.py")
    n_seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    opps = sys.argv[3].split(",") if len(sys.argv) > 3 else ["starter", "v4", "v5", "v6", "self"]
    first_seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    ensure_git_opponents()
    seeds = range(first_seed, first_seed + n_seeds)
    jobs = [(cand, o, s, seat) for o in opps for s in seeds for seat in (0, 1)]
    with Pool(min(len(jobs), os.cpu_count() or 4)) as pool:
        results = pool.map(play, jobs)
    total_w = total_n = 0
    all_money = []
    print(f"candidate: {os.path.basename(cand)}  seeds={n_seeds}")
    for o in opps:
        rows = [r for r in results if r[0] == o]
        wins = sum(1 for r in rows if r[3] > r[4])
        mine = [r[3] for r in rows]
        theirs = [r[4] for r in rows]
        bad = [r for r in rows if r[5] != "DONE"]
        total_w += wins if o != "self" else 0
        total_n += len(rows) if o != "self" else 0
        all_money += mine
        print(
            f"  vs {o:8s} win {wins:2d}/{len(rows):2d}  my avg ${sum(mine)/len(mine):>9,.0f}"
            f"  opp avg ${sum(theirs)/len(theirs):>9,.0f}  min ${min(mine):>8,.0f}"
            + (f"  ERRORS {len(bad)}" if bad else "")
        )
    if total_n:
        print(f"  overall (no mirror) win {total_w}/{total_n}  avg money ${sum(all_money)/len(all_money):,.0f}")


if __name__ == "__main__":
    main()
