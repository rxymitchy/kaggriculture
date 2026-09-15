"""Tunable strategy parameters. Keep all thresholds here for experiments."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class StrategyConfig:
    version: str = "v4-profit-speed"

    min_cash_reserve: float = 80.0
    land_min_cash_after: float = 700.0
    land_earliest_day: int = 3
    goose_min_wheat_plants: int = 10
    goose_earliest_day: int = 5
    max_geese_buy_per_turn: int = 1
    land_min_remaining_days: tuple = (10, 14, 18)
    land_unused_tile_trigger: int = 2

    target_hires: int = 10
    max_hires_per_turn: int = 9
    hire_if_tasks_per_worker: float = 1.1
    max_daily_hire_cost: float = 400.0
    plants_per_worker: float = 3.0

    wheat_tiles_per_animal: float = 1.4
    min_wheat_tiles: int = 0
    wheat_feed_reserve: int = 2
    max_geese: int = 0
    max_cows: int = 0
    max_sheep: int = 0
    goose_min_remaining_days: int = 12
    goose_min_egg_price: int = 35

    carrot_share: float = 0.5
    melon_share: float = 0.2
    strawberry_share: float = 0.08
    tomato_share: float = 0.0
    melon_min_price: int = 100
    strawberry_min_price: int = 50
    melon_max_visible_total: int = 8

    harvest_min_one_time_age_slack: int = 0
    care_geese: bool = False
    care_cows: bool = False
    care_sheep: bool = False
    fertilize_strawberry: bool = False
    fertilize_tomato: bool = False
    fertilize_melon: bool = False
    sell_fertilizer_if_price_ge: int = 40

    sell_fragile_if_price_ge: int = 20
    sell_staple_always: bool = True
    max_sell_units_fragile: int = 12
    keep_wheat_for_feed: bool = True

    endgame_days: int = 4
    no_new_animals_days: int = 10
    no_new_land_days: int = 7
    liquidation_days: int = 2

    opponent_glut_penalty: float = 0.35
    protect_shed_tiles: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_CONFIG = StrategyConfig()


VARIANTS = {
    "balanced": StrategyConfig(),
    "crop_heavy": StrategyConfig(
        version="crop-heavy",
        max_geese=0,
        melon_share=0.25,
        strawberry_share=0.1,
        target_hires=11,
    ),
    "animal_heavy": StrategyConfig(
        version="animal-heavy",
        max_geese=8,
        min_wheat_tiles=8,
        wheat_tiles_per_animal=1.5,
        melon_share=0.0,
        strawberry_share=0.0,
        goose_min_remaining_days=8,
        target_hires=10,
        care_geese=True,
    ),
    "conservative": StrategyConfig(
        version="conservative",
        min_cash_reserve=250.0,
        target_hires=6,
        max_geese=0,
        melon_share=0.0,
        plants_per_worker=2.5,
    ),
    "aggressive_expand": StrategyConfig(
        version="aggressive-expand",
        min_cash_reserve=40.0,
        land_min_remaining_days=(6, 10, 14),
        target_hires=12,
        land_min_cash_after=400.0,
        plants_per_worker=3.5,
    ),
}
