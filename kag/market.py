"""Market pricing, town demand, and sale/buy policy."""

from __future__ import annotations

from .config import StrategyConfig
from .constants import (
    FRAGILE_PRODUCTS,
    MARKET_I0,
    MARKET_PARAMS,
    PRODUCTS,
    SHOPS,
    TOWN_CENTER_PRODUCTS,
    market_price,
)
from .state import GameState


def town_demand_per_day(shops: list[str], turns_per_day: int = 24, shop_interval: int = 4, center_interval: int = 24) -> dict[str, float]:
    demand = {p: 0.0 for p in PRODUCTS}
    shop_ticks = turns_per_day / shop_interval
    center_ticks = turns_per_day / center_interval
    for p in TOWN_CENTER_PRODUCTS:
        demand[p] += center_ticks
    for name in shops:
        products = SHOPS.get(name, [])
        if not products:
            continue
        mult = 2 if len(products) == 1 else 1
        for item in products:
            demand[item] += shop_ticks * mult
    return demand


def scarcity(item: str, inventory: int) -> float:
    """Positive when below I0 (scarce), negative when glut."""
    I0 = MARKET_PARAMS[item]["I0"]
    T = MARKET_PARAMS[item]["T"]
    return (I0 - inventory) / max(1, T)


def predicted_price(item: str, inventory: int, extra_sold: int = 0, extra_bought: int = 0) -> int:
    inv = inventory + extra_sold - extra_bought
    return market_price(item, inv)


def sale_plan(state: GameState, cfg: StrategyConfig) -> list[tuple[str, int]]:
    """Items currently in the shed that we should sell this turn.

    Winning bots sell almost everything. Keep wheat for heads we own (including
    animals still in the shed) and a little fertilizer for unfertilized berries.
    """
    remaining = state.remaining_days
    n_animals = state.livestock_heads()
    wheat_keep = (n_animals + cfg.wheat_feed_reserve) if cfg.keep_wheat_for_feed else 0
    if remaining <= cfg.liquidation_days:
        wheat_keep = 0

    fert_keep = 0
    if remaining > cfg.liquidation_days and state.day >= 6 and state.money >= 80:
        want_fert = 0
        for p in state.me.plants:
            if p.is_fertilized(state.day):
                continue
            if (
                (p.crop == "STRAWBERRY" and cfg.fertilize_strawberry)
                or (p.crop == "TOMATO" and cfg.fertilize_tomato)
                or (p.crop == "MELON" and cfg.fertilize_melon)
            ):
                want_fert += 1
        price = state.market_prices.get("FERTILIZER", 100)
        if price < cfg.sell_fertilizer_if_price_ge:
            fert_keep = min(want_fert, 12)
        else:
            fert_keep = min(want_fert, 4)
        if state.wheat_available_for_feed() < n_animals:
            fert_keep = 0

    orders = []
    for item in PRODUCTS:
        have = state.shed_count(item)
        if have <= 0:
            continue
        price = state.market_prices.get(item, 1)
        if item == "WHEAT":
            sell = max(0, have - wheat_keep)
            if sell > 0:
                orders.append((item, sell))
            continue
        if item == "FERTILIZER":
            sell = have - fert_keep
            if sell > 0:
                orders.append((item, sell))
            continue
        if item in FRAGILE_PRODUCTS:
            n = min(have, cfg.max_sell_units_fragile if remaining > cfg.liquidation_days else have)
            if n > 0:
                orders.append((item, n))
            continue
        if cfg.sell_staple_always:
            orders.append((item, have))
    return orders


def daily_town_pull(state: GameState) -> dict[str, float]:
    return town_demand_per_day(state.shops, state.turns_per_day)
