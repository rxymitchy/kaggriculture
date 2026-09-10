"""Tunable strategy parameters. Keep all thresholds here for experiments."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class StrategyConfig:
    version: str = "v3-adaptive"

    min_cash_reserve: float = 150.0
    land_min_cash_after: float = 900.0
    land_earliest_day: int = 4
    goose_min_wheat_plants: int = 8
    goose_earliest_day: int = 3
    max_geese_buy_per_turn: int = 1
    land_min_remaining_days: tuple = (8, 12, 16)
    land_unused_tile_trigger: int = 4

    target_hires: int = 8
    max_hires_per_turn: int = 8
    hire_if_tasks_per_worker: float = 1.4
    max_daily_hire_cost: float = 200.0

    wheat_tiles_per_animal: float = 1.4
    min_wheat_tiles: int = 6
    wheat_feed_reserve: int = 2
    max_geese: int = 8
    max_cows: int = 0
    max_sheep: int = 0
    goose_min_remaining_days: int = 10
    goose_min_egg_price: int = 20

    carrot_share: float = 0.35
    melon_share: float = 0.12
    strawberry_share: float = 0.10
    tomato_share: float = 0.05
    melon_min_price: int = 80
    strawberry_min_price: int = 40
    melon_max_visible_total: int = 12

    harvest_min_one_time_age_slack: int = 0
    care_geese: bool = True
    care_cows: bool = False
    care_sheep: bool = False
    fertilize_strawberry: bool = True
    fertilize_tomato: bool = True
    fertilize_melon: bool = True
    sell_fertilizer_if_price_ge: int = 70

    sell_fragile_if_price_ge: int = 30
    sell_staple_always: bool = True
    max_sell_units_fragile: int = 8
    keep_wheat_for_feed: bool = True

    endgame_days: int = 5
    no_new_animals_days: int = 8
    no_new_land_days: int = 6
    liquidation_days: int = 2

    opponent_glut_penalty: float = 0.65
    protect_shed_tiles: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_CONFIG = StrategyConfig()


VARIANTS = {
    "balanced": StrategyConfig(),
    "crop_heavy": StrategyConfig(
        version="crop-heavy",
        max_geese=2,
        min_wheat_tiles=10,
        carrot_share=0.45,
        melon_share=0.18,
        strawberry_share=0.12,
        target_hires=9,
    ),
    "animal_heavy": StrategyConfig(
        version="animal-heavy",
        max_geese=14,
        min_wheat_tiles=10,
        wheat_tiles_per_animal=1.5,
        carrot_share=0.15,
        melon_share=0.0,
        strawberry_share=0.0,
        goose_min_remaining_days=8,
        target_hires=10,
    ),
    "conservative": StrategyConfig(
        version="conservative",
        min_cash_reserve=400.0,
        target_hires=5,
        max_geese=4,
        melon_share=0.0,
        strawberry_share=0.05,
        land_min_remaining_days=(12, 16, 20),
    ),
    "aggressive_expand": StrategyConfig(
        version="aggressive-expand",
        min_cash_reserve=40.0,
        land_min_remaining_days=(5, 8, 12),
        target_hires=10,
        max_geese=10,
        land_min_cash_after=150.0,
    ),
}
