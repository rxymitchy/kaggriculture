"""Expected-value crop and animal economics given remaining time and prices."""

from __future__ import annotations

from .config import StrategyConfig
from .constants import ANIMALS, CROPS, watering_window
from .state import GameState


def expected_one_time_yield(crop: str, remaining_days: int, fertilized: bool) -> tuple[int, int]:
    """Return (yield_units, days_occupied) if planted now, or (0,0) if it cannot mature."""
    cd = CROPS[crop]
    first = cd["first_yield_day"]
    start, end = watering_window(crop)
    if remaining_days < first:
        return 0, 0
    harvest_age = min(end if remaining_days >= end else max(first, remaining_days), end)
    # Melon unfertilized hits cap 6 at age 10 even though window ends at 12.
    if crop == "MELON":
        cap_age = 8 if fertilized else 10
        harvest_age = min(harvest_age, cap_age, remaining_days)
        harvest_age = max(harvest_age, first if remaining_days >= first else 0)
        if harvest_age < first:
            return 0, 0
        y = 1
        bonus = 2 if fertilized else 1
        for age in range(start, harvest_age + 1):
            y = min(6, y + bonus)
        return y, harvest_age
    y = 1
    bonus = 2 if fertilized else 1
    last = min(harvest_age, remaining_days)
    if last < first:
        return 0, 0
    for age in range(start, last + 1):
        y = min(cd["max_yield"], y + bonus)
    if not fertilized:
        if crop == "WHEAT":
            y = min(4, y)
        if crop == "CARROT":
            y = min(3, y)
    return y, last


def expected_ongoing_yield(crop: str, remaining_days: int, fertilized: bool) -> tuple[int, int]:
    cd = CROPS[crop]
    first = cd["first_yield_day"]
    if remaining_days < first:
        return 0, 0
    interval = cd["interval"]
    max_prod = cd["max_yield"]
    productions = 0
    # Production fires at end of day when next_day = planted + first + k*interval
    # i.e. after `first` full days have elapsed, then every `interval` days, up to 4.
    days_needed = first
    while productions < max_prod and days_needed <= remaining_days:
        productions += 1
        days_needed += interval
    units_each = 2 if fertilized else 1
    occupy = min(remaining_days, first + (productions - 1) * interval + 1)
    return productions * units_each, occupy


def crop_net_value(crop: str, price: float, remaining_days: int, fertilized: bool = False) -> dict:
    cd = CROPS[crop]
    if cd["ongoing"]:
        units, days = expected_ongoing_yield(crop, remaining_days, fertilized)
    else:
        units, days = expected_one_time_yield(crop, remaining_days, fertilized)
    revenue = units * price
    cost = cd["seed"]
    net = revenue - cost
    actions = 1 + days + 1  # plant + daily water + harvest (approx)
    return {
        "crop": crop,
        "units": units,
        "days": days,
        "net": net,
        "per_day": net / max(1, days),
        "per_action": net / max(1, actions),
        "per_capital": net / max(1, cost),
        "can_plant": units > 0 and net > 0,
    }


def wheat_feed_cost(price_wheat: float, units: int) -> float:
    return units * max(0.0, price_wheat)


def animal_remaining_productions(animal: str, remaining_days: int) -> int:
    a = ANIMALS[animal]
    first = a["first_yield_day"]
    if remaining_days < first:
        return 0
    # first production after `first` days, then every interval
    left = remaining_days - first
    return 1 + left // a["interval"]


def animal_net_value(
    animal: str,
    product_price: float,
    wheat_price: float,
    fert_price: float,
    remaining_days: int,
    care: bool,
) -> dict:
    a = ANIMALS[animal]
    n_prod = animal_remaining_productions(animal, remaining_days)
    # Care: roughly +1 extra unit per production if we care every day (geese),
    # or + (interval) extra if cared on non-prod days too. Conservative: +0.7 if care.
    units_per = 1.0 + (0.9 if care else 0.0)
    product_units = n_prod * units_per
    fert_units = max(0, remaining_days)  # 1/day if collected
    feed_units = max(0, remaining_days)  # feed daily
    revenue = product_units * product_price + fert_units * min(fert_price, 80)
    cost = a["cost"] + wheat_feed_cost(wheat_price, feed_units)
    # structure + place + daily feed/care/collect/harvest actions
    actions = 2 + remaining_days * (1.0 + (1.0 if care else 0.0) + 0.4)
    net = revenue - cost
    return {
        "animal": animal,
        "productions": n_prod,
        "net": net,
        "per_day": net / max(1, remaining_days),
        "per_action": net / max(1, actions),
        "can_buy": n_prod > 0 and net > 50,
    }


def best_crop(
    state: GameState,
    cfg: StrategyConfig,
    prices: dict[str, float],
    opponent_penalty: dict[str, float],
) -> str:
    remaining = state.remaining_days
    scored = []
    for crop in CROPS:
        ev = crop_net_value(crop, prices.get(crop, 1), remaining, fertilized=False)
        score = ev["per_day"] * opponent_penalty.get(crop, 1.0)
        if crop == "WHEAT":
            score += 8  # feed option value
        if not ev["can_plant"]:
            score = -1e9
        scored.append((score, crop))
    scored.sort(reverse=True)
    return scored[0][1] if scored else "WHEAT"


def pick_crop_for_tile(state: GameState, cfg: StrategyConfig, prices: dict[str, float], opp_counts: dict[str, int]) -> str:
    """Choose the crop with the best expected profit given remaining time and live prices."""
    remaining = state.remaining_days
    my_counts = state.me.crop_counts()
    n_animals = sum(state.me.animal_counts().values())
    wheat_needed = int(cfg.wheat_tiles_per_animal * n_animals) if n_animals else 0
    wheat_needed = max(wheat_needed, cfg.min_wheat_tiles)
    if remaining <= 2:
        return "WHEAT"
    if wheat_needed and my_counts.get("WHEAT", 0) < wheat_needed and remaining >= 3:
        return "WHEAT"

    scored: list[tuple[float, str]] = []
    for crop in CROPS:
        if crop == "TOMATO" and cfg.tomato_share <= 0:
            continue
        price = float(prices.get(crop, 1) or 1)
        ev = crop_net_value(crop, price, remaining, fertilized=False)
        if not ev["can_plant"] or ev["net"] <= 0:
            continue
        vis = opp_counts.get(crop, 0) + my_counts.get(crop, 0)
        glut = 1.0
        if crop in ("MELON", "STRAWBERRY", "MILK", "WOOL"):
            if price < (cfg.melon_min_price if crop == "MELON" else cfg.strawberry_min_price if crop == "STRAWBERRY" else 20):
                continue
            if vis >= cfg.melon_max_visible_total:
                glut = cfg.opponent_glut_penalty
        # Speed-weighted: extra credit for fast cycles (high per_action).
        score = 0.55 * ev["per_day"] + 0.45 * ev["per_action"]
        score *= glut
        n_plants = max(1, sum(my_counts.values()))
        share = my_counts.get(crop, 0) / n_plants
        if crop == "MELON" and share >= cfg.melon_share:
            continue
        if crop == "STRAWBERRY" and share >= cfg.strawberry_share:
            continue
        if crop == "TOMATO" and share >= max(0.01, cfg.tomato_share):
            continue
        scored.append((score, crop))
    if not scored:
        return "CARROT" if remaining >= 3 else "WHEAT"
    scored.sort(reverse=True)
    return scored[0][1]
