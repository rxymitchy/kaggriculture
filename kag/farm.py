"""Farm tile helpers."""

from __future__ import annotations

from .constants import CROPS, watering_window
from .state import FarmView, GameState, Plant


def plant_ready_to_harvest(plant: Plant, day: int) -> bool:
    cd = CROPS[plant.crop]
    if plant.yield_units <= 0:
        return False
    if day - plant.planted_day < cd["first_yield_day"]:
        return False
    return True


def one_time_should_wait(plant: Plant, day: int) -> bool:
    """Wait for extra watering bonus if we still have time and haven't capped."""
    cd = CROPS[plant.crop]
    if cd["ongoing"]:
        return False
    age = plant.age(day)
    start, end = watering_window(plant.crop)
    if plant.yield_units >= cd["max_yield"]:
        return False
    # Unfertilized practical cap is below max_yield for wheat/carrot.
    if plant.crop == "WHEAT" and plant.yield_units >= 4 and plant.fertilized_until_day < day:
        return False
    if plant.crop == "CARROT" and plant.yield_units >= 3 and plant.fertilized_until_day < day:
        return False
    if plant.crop == "MELON" and plant.yield_units >= 6:
        return False
    return start <= age < end


def in_bonus_window(plant: Plant, day: int) -> bool:
    cd = CROPS[plant.crop]
    if cd["ongoing"]:
        return False
    age = plant.age(day)
    start, end = watering_window(plant.crop)
    return start <= age <= end


def water_adds_yield(plant: Plant, day: int) -> bool:
    if plant.watered_today:
        return False
    cd = CROPS[plant.crop]
    if cd["ongoing"]:
        return False
    if not in_bonus_window(plant, day):
        return False
    if plant.yield_units >= cd["max_yield"]:
        return False
    if plant.crop == "WHEAT" and plant.yield_units >= 4 and plant.fertilized_until_day < day:
        return False
    if plant.crop == "CARROT" and plant.yield_units >= 3 and plant.fertilized_until_day < day:
        return False
    return True


def decaying(plant: Plant, step: int) -> bool:
    mls = plant.max_lifespan_step
    return mls >= 0 and step >= mls


def unused_unlocked(farm: FarmView) -> int:
    return len(farm.empty) + len(farm.weeds)


def protect_positions(state: GameState, protect_shed: bool) -> set[tuple[int, int]]:
    if not protect_shed:
        return set()
    # Keep at least one dump tile free of long-term structures if possible.
    tiles = state.shed_tiles()
    # Prefer (4,4) default spawn as a logistics hub.
    return {tiles[0]} if tiles else set()
