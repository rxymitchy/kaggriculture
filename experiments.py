"""Repeatable local experiments. Example: python experiments.py --games 8 --opp starter"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from evaluation import format_summary, summarize
from kag.config import VARIANTS
from kag.strategy import CompetitiveAgent, agent_with_config
from simulation import pass_agent, run_episode, wheat_loop_agent


def load_named(name: str):
    name = name.lower()
    if name == "pass":
        return "pass"
    if name == "random":
        return "random"
    if name == "starter":
        return "starter"
    if name == "wheat":
        return wheat_loop_agent
    if name == "passfn":
        return pass_agent
    if name in VARIANTS:
        return agent_with_config(VARIANTS[name])
    if name in ("us", "adaptive", "main"):
        return agent_with_config(VARIANTS["balanced"])
    raise SystemExit(f"unknown agent {name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=4)
    p.add_argument("--steps", type=int, default=720)
    p.add_argument("--opp", default="starter")
    p.add_argument("--us", default="balanced")
    p.add_argument("--seed0", type=int, default=1)
    p.add_argument("--debug", action="store_true")
    p.add_argument("--out", default="")
    args = p.parse_args()

    us = load_named(args.us)
    opp = load_named(args.opp)
    results = []
    for i in range(args.games):
        seed = args.seed0 + i
        print(f"game {i+1}/{args.games} seed={seed} ...", flush=True)
        r = run_episode(us, opp, steps=args.steps, seed=seed, debug=args.debug)
        r.pop("env", None)
        r.pop("logs", None)
        results.append(r)
        print(f"  rewards={r['rewards']} winner={r['winner']} status={r['statuses']} {r['elapsed']:.1f}s")

    summary = summarize(results, 0)
    print(format_summary(f"{args.us} vs {args.opp}", summary))
    record = {
        "us": args.us,
        "opp": args.opp,
        "steps": args.steps,
        "seed0": args.seed0,
        "summary": summary,
        "results": [{k: v for k, v in r.items() if k != "env"} for r in results],
    }
    out = args.out or os.path.join(ROOT, "experiments", f"{args.us}_vs_{args.opp}_n{args.games}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print("wrote", out)


if __name__ == "__main__":
    main()
