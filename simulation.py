"""Local episode runner used by experiments."""

from __future__ import annotations

import json
import time
from typing import Callable


def make_env(steps=720, seed=None, debug=False):
    from kaggle_environments import make

    cfg = {"episodeSteps": steps}
    if seed is not None:
        cfg["seed"] = seed
    return make("kaggriculture", configuration=cfg, debug=debug)


def run_episode(agent0, agent1, steps=720, seed=None, debug=False) -> dict:
    env = make_env(steps=steps, seed=seed, debug=debug)
    t0 = time.time()
    env.run([agent0, agent1])
    elapsed = time.time() - t0
    final = env.steps[-1]
    rewards = []
    statuses = []
    for s in final:
        rewards.append(float(s["reward"] if isinstance(s, dict) else s.reward or 0))
        statuses.append(s["status"] if isinstance(s, dict) else s.status)
    winner = None
    if rewards[0] > rewards[1]:
        winner = 0
    elif rewards[1] > rewards[0]:
        winner = 1
    logs = getattr(env, "logs", None)
    return {
        "rewards": rewards,
        "statuses": statuses,
        "winner": winner,
        "elapsed": elapsed,
        "n_steps": len(env.steps),
        "seed": seed,
        "env": env,
        "logs": logs,
    }


def save_replay(env, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(env.toJSON(), f)


def pass_agent(obs, config=None):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def wheat_loop_agent(obs, config=None):
    player = obs["player"] if isinstance(obs, dict) else obs.player
    farms = obs["farms"] if isinstance(obs, dict) else obs.farms
    private = obs["private"] if isinstance(obs, dict) else obs.private
    me = farms[player]
    fx, fy = me["farmer"]
    tile = me["tiles"][fy][fx]
    day = obs["day"] if isinstance(obs, dict) else obs.day
    seeds = private.get("seeds", {}) if hasattr(private, "get") else private["seeds"]
    shed = private.get("shed", {}) if hasattr(private, "get") else private["shed"]
    market = []
    if (shed.get("WHEAT", 0) if hasattr(shed, "get") else shed["WHEAT"]) > 0:
        market.append(["SELL", "WHEAT", shed.get("WHEAT", 0) if hasattr(shed, "get") else shed["WHEAT"]])
    seed_w = seeds.get("WHEAT", 0) if hasattr(seeds, "get") else seeds["WHEAT"]
    if seed_w == 0 and me["money"] >= 10:
        market.append(["BUY_SEED", "WHEAT", 1])
    if tile is None and seed_w > 0:
        return {"farmer": ["PLANT", "WHEAT"], "hands": [], "market": market}
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        age = day - tile["planted_day"]
        if age >= 4:
            return {"farmer": ["HARVEST"], "hands": [], "market": market}
        if not tile["watered_today"]:
            return {"farmer": ["WATER"], "hands": [], "market": market}
    return {"farmer": ["PASS"], "hands": [], "market": market}
