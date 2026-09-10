"""BFS pathfinding. Locked tiles are passable. Occupancy is allowed."""

from __future__ import annotations

from collections import deque

from .constants import FARMER_MOVES, MOVE_FROM_DELTA


def in_bounds(x: int, y: int, n: int) -> bool:
    return 0 <= x < n and 0 <= y < n


def neighbors(pos: tuple[int, int], n: int):
    x, y = pos
    for dx, dy in FARMER_MOVES.values():
        nx, ny = x + dx, y + dy
        if in_bounds(nx, ny, n):
            yield (nx, ny)


def bfs_next_step(start: tuple[int, int], goal: tuple[int, int], n: int) -> str | None:
    """Return a movement op that reduces distance to goal, or None if already there / unreachable."""
    if start == goal:
        return None
    sx, sy = start
    gx, gy = goal
    # Manhattan greedy first (grid has no obstacles that block movement).
    dx = 0 if gx == sx else (1 if gx > sx else -1)
    dy = 0 if gy == sy else (1 if gy > sy else -1)
    # Prefer the larger remaining axis to keep paths short.
    if abs(gx - sx) >= abs(gy - sy) and dx:
        nx, ny = sx + dx, sy
        if in_bounds(nx, ny, n):
            return MOVE_FROM_DELTA[(dx, 0)]
    if dy:
        nx, ny = sx, sy + dy
        if in_bounds(nx, ny, n):
            return MOVE_FROM_DELTA[(0, dy)]
    if dx:
        nx, ny = sx + dx, sy
        if in_bounds(nx, ny, n):
            return MOVE_FROM_DELTA[(dx, 0)]
    return None


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def nearest(origin: tuple[int, int], targets: list[tuple[int, int]]) -> tuple[int, int] | None:
    if not targets:
        return None
    return min(targets, key=lambda t: manhattan(origin, t))


def bfs_path_exists(start: tuple[int, int], goal: tuple[int, int], n: int) -> bool:
    if start == goal:
        return True
    seen = {start}
    q = deque([start])
    while q:
        cur = q.popleft()
        for nxt in neighbors(cur, n):
            if nxt in seen:
                continue
            if nxt == goal:
                return True
            seen.add(nxt)
            q.append(nxt)
    return False
