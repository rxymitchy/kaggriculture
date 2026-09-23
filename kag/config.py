"""Tunable strategy parameters. Keep all thresholds here for experiments."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class StrategyConfig:
    version: str = "v6-cash-first"

    min_cash_reserve: float = 80.0
    land_min_cash_after: float = 800.0
    land_earliest_day: int = 8
    goose_min_wheat_plants: int = 0
    goose_earliest_day: int = 99
    max_geese_buy_per_turn: int = 0
    max_cows_buy_per_turn: int = 2
    max_sheep_buy_per_turn: int = 0
    land_min_remaining_days: tuple = (8, 10, 12)
    land_unused_tile_trigger: int = 3

    target_hires: int = 10
    opening_hires: int = 4
    max_hires_per_turn: int = 4
    hire_if_tasks_per_worker: float = 1.0
    max_daily_hire_cost: float = 400.0
    plants_per_worker: float = 3.5

    wheat_tiles_per_animal: float = 1.0
    min_wheat_tiles: int = 0
    opening_wheat_tiles: int = 10
    opening_carrot_tiles: int = 6
    opening_melon_tiles: int = 4
    wheat_feed_reserve: int = 2
    min_operating_cash: float = 400.0
    max_geese: int = 0
    max_cows: int = 4
    max_sheep: int = 0
    opening_cows: int = 0
    opening_sheep: int = 0
    goose_min_remaining_days: int = 8
    goose_min_egg_price: int = 20
    cow_min_milk_price: int = 25
    sheep_min_wool_price: int = 20
    animal_earliest_day: int = 8
    animal_min_cash: float = 2000.0

    carrot_share: float = 0.35
    melon_share: float = 0.15
    strawberry_share: float = 0.40
    tomato_share: float = 0.05
    melon_min_price: int = 80
    strawberry_min_price: int = 50
    melon_replant_min_price: int = 180
    melon_max_visible_total: int = 10

    harvest_min_one_time_age_slack: int = 0
    care_geese: bool = False
    care_cows: bool = True
    care_sheep: bool = False
    fertilize_strawberry: bool = True
    fertilize_tomato: bool = False
    fertilize_melon: bool = True
    sell_fertilizer_if_price_ge: int = 20

    sell_fragile_if_price_ge: int = 1
    sell_staple_always: bool = True
    max_sell_units_fragile: int = 100
    keep_wheat_for_feed: bool = True

    endgame_days: int = 3
    no_new_animals_days: int = 10
    no_new_land_days: int = 6
    liquidation_days: int = 2

    opponent_glut_penalty: float = 0.45
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
        opening_melon_tiles=6,
        strawberry_share=0.5,
        target_hires=10,
    ),
    "animal_heavy": StrategyConfig(
        version="animal-heavy",
        max_geese=0,
        max_cows=6,
        max_sheep=2,
        opening_cows=0,
        opening_sheep=0,
        animal_earliest_day=4,
        animal_min_cash=700.0,
        target_hires=10,
    ),
    "conservative": StrategyConfig(
        version="conservative",
        min_cash_reserve=150.0,
        target_hires=8,
        opening_hires=3,
        max_geese=0,
        max_cows=2,
        opening_sheep=0,
        plants_per_worker=3.0,
        land_min_cash_after=500.0,
    ),
    "aggressive_expand": StrategyConfig(
        version="aggressive-expand",
        land_min_remaining_days=(6, 8, 10),
        target_hires=12,
        land_min_cash_after=250.0,
        plants_per_worker=4.0,
        max_cows=4,
        opening_melon_tiles=6,
    ),
}
