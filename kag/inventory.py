"""Shed capacity and inventory projections."""

from __future__ import annotations

from .state import GameState


def projected_occupancy(state: GameState) -> int:
    return state.shed_total() + state.carried_total()


def room_after_harvest(state: GameState, units: int) -> int:
    return state.shed_capacity - (projected_occupancy(state) + units)


def can_safely_harvest(state: GameState, units: int, endgame: bool = False) -> bool:
    if units <= 0:
        return False
    # Carried goods drop into the shed at end of day; overflow is destroyed.
    proj = projected_occupancy(state) + units
    if proj <= state.shed_capacity:
        return True
    # Allow harvest if we will sell from shed this turn (room appears after DROP+SELL,
    # but harvest lands in worker inventory). Keep a small buffer unless liquidating.
    buffer = 0 if endgame else 4
    return state.shed_room() + state.carried_total() + buffer >= 0 and proj <= state.shed_capacity + (8 if endgame else 0)


def items_to_drop(worker_inv: dict[str, int]) -> list[tuple[str, int]]:
    return [(k, v) for k, v in worker_inv.items() if v > 0]
