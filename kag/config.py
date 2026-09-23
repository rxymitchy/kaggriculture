"""Tunable strategy parameters. Keep all thresholds here for experiments."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class StrategyConfig:
    version: str = "v5-win-meta"

    min_cash_reserve: float = 40.0
    land_min_cash_after: float = 80.0
    land_earliest_day: int = 6
    goose_min_wheat_plants: int = 0
    goose_earliest_day: int = 6
    max_geese_buy_per_turn: int = 3
    max_cows_buy_per_turn: int = 3
    max_sheep_buy_per_turn: int = 3
    land_min_remaining_days: tuple = (8, 10, 12)
    land_unused_tile_trigger: int = 4

    target_hires: int = 12
    opening_hires: int = 4
    max_hires_per_turn: int = 4
    hire_if_tasks_per_worker: float = 1.0
    max_daily_hire_cost: float = 1200.0
    plants_per_worker: float = 5.0

    wheat_tiles_per_animal: float = 0.0
    min_wheat_tiles: int = 0
    opening_wheat_tiles: int = 8
    opening_melon_tiles: int = 10
    wheat_feed_reserve: int = 6
    min_operating_cash: float = 40.0
    max_geese: int = 8
    max_cows: int = 10
    max_sheep: int = 3
    opening_cows: int = 2
    opening_sheep: int = 3
    goose_min_remaining_days: int = 8
    goose_min_egg_price: int = 20
    cow_min_milk_price: int = 25
    sheep_min_wool_price: int = 20

    carrot_share: float = 0.2
    melon_share: float = 0.2
    strawberry_share: float = 0.95
    tomato_share: float = 0.0
    melon_min_price: int = 80
    strawberry_min_price: int = 35
    melon_replant_min_price: int = 180
    melon_max_visible_total: int = 16

    harvest_min_one_time_age_slack: int = 0
    care_geese: bool = True
    care_cows: bool = True
    care_sheep: bool = True
    fertilize_strawberry: bool = True
    fertilize_tomato: bool = False
    fertilize_melon: bool = True
    sell_fertilizer_if_price_ge: int = 30

    sell_fragile_if_price_ge: int = 1
    sell_staple_always: bool = True
    max_sell_units_fragile: int = 100
    keep_wheat_for_feed: bool = True

    endgame_days: int = 3
    no_new_animals_days: int = 8
    no_new_land_days: int = 6
    liquidation_days: int = 2

    opponent_glut_penalty: float = 0.4
    protect_shed_tiles: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_CONFIG = StrategyConfig()


VARIANTS = {
    "balanced": StrategyConfig(),
    "crop_heavy": StrategyConfig(
        version="crop-heavy",
        max_geese=0,
        max_cows=0,
        max_sheep=0,
        opening_cows=0,
        opening_sheep=0,
        opening_melon_tiles=12,
        strawberry_share=0.95,
        target_hires=12,
    ),
    "animal_heavy": StrategyConfig(
        version="animal-heavy",
        max_geese=10,
        max_cows=12,
        max_sheep=5,
        opening_cows=2,
        opening_sheep=3,
        target_hires=12,
    ),
    "conservative": StrategyConfig(
        version="conservative",
        min_cash_reserve=150.0,
        target_hires=8,
        opening_hires=3,
        max_geese=2,
        max_cows=4,
        opening_sheep=0,
        plants_per_worker=4.0,
    ),
    "aggressive_expand": StrategyConfig(
        version="aggressive-expand",
        land_min_remaining_days=(6, 8, 10),
        target_hires=12,
        land_min_cash_after=40.0,
        plants_per_worker=6.0,
        max_geese=8,
        max_cows=10,
        opening_sheep=3,
    ),
}
