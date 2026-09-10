"""Observable opponent features and coarse strategy class."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import ANIMALS, CROPS
from .state import FarmView, GameState


@dataclass
class OpponentModel:
    money: float
    unlocked: int
    crop_counts: dict[str, int]
    animal_counts: dict[str, int]
    weeds: int
    empty: int
    label: str
    likely_outputs: dict[str, float]


def classify(farm: FarmView) -> str:
    crops = farm.crop_counts()
    animals = farm.animal_counts()
    n_c = sum(crops.values())
    n_a = sum(animals.values())
    n_land = len(farm.unlocked_quadrants)
    if n_land >= 3:
        expand = True
    else:
        expand = False
    if n_a >= 4 and n_a >= n_c * 0.3:
        base = "animal-heavy"
    elif crops.get("MELON", 0) + crops.get("STRAWBERRY", 0) >= max(4, n_c * 0.35):
        base = "premium-crop-heavy"
    elif crops.get("WHEAT", 0) >= max(6, n_c * 0.5):
        base = "wheat-heavy"
    elif n_c >= 8:
        base = "diversified"
    elif n_c + n_a <= 2:
        base = "conservative"
    else:
        base = "mixed"
    if expand and base != "conservative":
        return base + "+expansion"
    return base


def likely_daily_output(farm: FarmView) -> dict[str, float]:
    out = {c: 0.0 for c in list(CROPS) + ["EGG", "MILK", "WOOL", "FERTILIZER"]}
    for p in farm.plants:
        if p.crop == "WHEAT":
            out["WHEAT"] += 0.8
        elif p.crop == "CARROT":
            out["CARROT"] += 0.75
        elif p.crop == "TOMATO":
            out["TOMATO"] += 0.33
        elif p.crop == "STRAWBERRY":
            out["STRAWBERRY"] += 0.24
        elif p.crop == "MELON":
            out["MELON"] += 0.55
    for a in farm.animals:
        prod = ANIMALS[a.animal]["product"]
        interval = ANIMALS[a.animal]["interval"]
        out[prod] += 1.0 / interval
        out["FERTILIZER"] += 1.0
    return out


def extract(state: GameState) -> OpponentModel:
    farm = state.opp
    return OpponentModel(
        money=farm.money,
        unlocked=len(farm.unlocked_quadrants),
        crop_counts=farm.crop_counts(),
        animal_counts=farm.animal_counts(),
        weeds=len(farm.weeds),
        empty=len(farm.empty),
        label=classify(farm),
        likely_outputs=likely_daily_output(farm),
    )
