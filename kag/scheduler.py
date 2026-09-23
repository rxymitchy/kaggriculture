"""Greedy worker-to-task assignment and movement."""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import ANIMALS
from .movement import bfs_next_step, manhattan
from .state import GameState, Worker

_HOLDER_OPS = {"PLACE", "BUILD_COOP", "BUILD_PASTURE"}


@dataclass
class Task:
    priority: float
    pos: tuple[int, int]
    action: list
    need_item: str | None = None
    key: str = ""
    once: bool = True


def assign(state: GameState, tasks: list[Task]) -> dict[int, list]:
    """Return farmer/hand action lists keyed by worker idx."""
    tasks = sorted(tasks, key=lambda t: -t.priority)
    reserved: set[str] = set()
    reserved_pos: set[tuple[int, int]] = set()
    busy: set[int] = set()
    actions: dict[int, list] = {w.idx: ["PASS"] for w in state.workers}
    tile_ops = {
        "WATER", "HARVEST", "PLANT", "FERTILIZE", "FEED", "CARE",
        "COLLECT_FERTILIZER", "BUILD_COOP", "BUILD_PASTURE", "DIG", "PLACE",
    }

    def holding_animal(w: Worker) -> bool:
        return any(w.inv_count(a) > 0 for a in ANIMALS)

    def can_do(w: Worker, t: Task) -> bool:
        if t.need_item and w.inv_count(t.need_item) <= 0:
            return False
        op = t.action[0] if t.action else "PASS"
        # DROP dumps the whole bag — never send a livestock carrier to dump produce.
        if holding_animal(w) and op not in _HOLDER_OPS:
            return False
        return True

    for t in tasks:
        tk = t.key or f"{t.action[0]}:{t.pos}:{id(t)}"
        if t.once and tk in reserved:
            continue
        op = t.action[0] if t.action else "PASS"
        if op in tile_ops and t.pos in reserved_pos:
            continue
        candidates = [w for w in state.workers if w.idx not in busy and can_do(w, t)]
        if not candidates:
            continue
        w = min(candidates, key=lambda ww: manhattan(ww.pos, t.pos))
        if w.pos == t.pos:
            actions[w.idx] = list(t.action)
        else:
            step = bfs_next_step(w.pos, t.pos, state.board_size)
            actions[w.idx] = [step] if step else ["PASS"]
        busy.add(w.idx)
        if t.once:
            reserved.add(tk)
        if op in tile_ops:
            reserved_pos.add(t.pos)

    return actions


def actions_to_output(state: GameState, by_idx: dict[int, list]) -> tuple[list, list]:
    farmer = by_idx.get(0, ["PASS"])
    hands = [by_idx.get(i + 1, ["PASS"]) for i in range(len(state.me.hands))]
    return farmer, hands
