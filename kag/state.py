"""Normalized observation parsing. Works with dicts and kaggle structify objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .constants import (
    ANIMALS,
    CROPS,
    DEFAULT_BOARD,
    DEFAULT_DAYS,
    DEFAULT_SHED,
    DEFAULT_STEPS,
    DEFAULT_TURNS_PER_DAY,
    PRODUCTS,
    shed_access_tiles,
)


def getv(obj: Any, key: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        return obj[key]
    except Exception:
        return getattr(obj, key, default)


def as_int(v, default=0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def as_float(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def as_pos(v) -> Optional[tuple[int, int]]:
    if v is None:
        return None
    try:
        return (int(v[0]), int(v[1]))
    except Exception:
        return None


def tile_is_locked(tile) -> bool:
    return tile == "LOCKED"


def tile_is_empty(tile) -> bool:
    return tile is None


def tile_kind(tile) -> Optional[str]:
    if tile is None or tile == "LOCKED":
        return None
    if isinstance(tile, dict):
        return tile.get("kind")
    return getv(tile, "kind")


def animal_on_tile(tile) -> Optional[str]:
    if not isinstance(tile, dict) and not (tile is not None and tile != "LOCKED"):
        if tile is None or tile == "LOCKED":
            return None
    kind = tile_kind(tile)
    if kind not in ("COOP", "PASTURE") and not (isinstance(tile, dict) and "animal" in tile):
        # still check animal key for occupied structures
        pass
    if tile is None or tile == "LOCKED":
        return None
    animal = getv(tile, "animal", None)
    if animal in ANIMALS:
        return animal
    return None


@dataclass
class Plant:
    x: int
    y: int
    crop: str
    planted_day: int
    watered_today: bool
    consecutive_unwatered: int
    yield_units: int
    max_lifespan_step: int
    fertilized_until_day: int

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    def age(self, day: int) -> int:
        return day - self.planted_day

    def dies_tonight_if_unwatered(self) -> bool:
        return (not self.watered_today) and self.consecutive_unwatered >= 1

    def is_fertilized(self, day: int) -> bool:
        return self.fertilized_until_day >= day


@dataclass
class Animal:
    x: int
    y: int
    kind: str  # COOP / PASTURE
    animal: str
    placed_day: int
    yield_units: int
    fed_today: bool
    consecutive_unfed: int
    cared_today: bool
    fertilizer_available: bool
    pending_care_bonus: int

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    def dies_tonight_if_unfed(self) -> bool:
        return (not self.fed_today) and self.consecutive_unfed >= 1

    def product(self) -> str:
        return ANIMALS[self.animal]["product"]

    def structure(self) -> str:
        return ANIMALS[self.animal]["structure"]


@dataclass
class Structure:
    x: int
    y: int
    kind: str  # empty COOP/PASTURE

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass
class Worker:
    idx: int  # 0 farmer
    pos: tuple[int, int]
    inventory: dict[str, int]

    def inv_count(self, item: str) -> int:
        return int(self.inventory.get(item, 0) or 0)

    def inv_total(self) -> int:
        return sum(int(v or 0) for v in self.inventory.values())


@dataclass
class FarmView:
    money: float
    tiles: list
    farmer: tuple[int, int]
    hands: list[tuple[int, int]]
    unlocked_quadrants: list[str]
    hires_today: int
    plants: list[Plant] = field(default_factory=list)
    animals: list[Animal] = field(default_factory=list)
    weeds: list[tuple[int, int]] = field(default_factory=list)
    empty: list[tuple[int, int]] = field(default_factory=list)
    empty_structures: list[Structure] = field(default_factory=list)
    board_size: int = 10

    def crop_counts(self) -> dict[str, int]:
        out = {c: 0 for c in CROPS}
        for p in self.plants:
            out[p.crop] = out.get(p.crop, 0) + 1
        return out

    def animal_counts(self) -> dict[str, int]:
        out = {a: 0 for a in ANIMALS}
        for a in self.animals:
            out[a.animal] = out.get(a.animal, 0) + 1
        return out


@dataclass
class GameState:
    player: int
    step: int
    day: int
    hour: int
    me: FarmView
    opp: FarmView
    market_inv: dict[str, int]
    market_prices: dict[str, int]
    shops: list[str]
    shed: dict[str, int]
    seeds: dict[str, int]
    workers: list[Worker]
    board_size: int
    turns_per_day: int
    episode_steps: int
    shed_capacity: int
    days_total: int

    @property
    def remaining_steps(self) -> int:
        return max(0, self.episode_steps - self.step)

    @property
    def remaining_days(self) -> int:
        # inclusive-ish: days whose turns are not fully elapsed
        return max(0, self.days_total - self.day)

    @property
    def money(self) -> float:
        return self.me.money

    def shed_count(self, item: str) -> int:
        return int(self.shed.get(item, 0) or 0)

    def seed_count(self, crop: str) -> int:
        return int(self.seeds.get(crop, 0) or 0)

    def shed_total(self) -> int:
        return sum(int(v or 0) for v in self.shed.values())

    def shed_room(self) -> int:
        return max(0, self.shed_capacity - self.shed_total())

    def carried_count(self, item: str) -> int:
        return sum(w.inv_count(item) for w in self.workers)

    def carried_total(self) -> int:
        return sum(w.inv_total() for w in self.workers)

    def wheat_available_for_feed(self) -> int:
        return self.shed_count("WHEAT") + self.carried_count("WHEAT")

    def animal_owned(self, name: str) -> int:
        return (
            self.me.animal_counts().get(name, 0)
            + self.shed_count(name)
            + self.carried_count(name)
        )

    def livestock_heads(self) -> int:
        return sum(self.animal_owned(a) for a in ANIMALS)

    def holding_any_animal(self) -> bool:
        return any(self.carried_count(a) > 0 for a in ANIMALS)

    def is_end_of_day_turn(self) -> bool:
        return (self.hour + 1) >= self.turns_per_day

    def shed_tiles(self) -> list[tuple[int, int]]:
        return shed_access_tiles(self.board_size)


def parse_farm(raw, board_size: int) -> FarmView:
    money = as_float(getv(raw, "money", 0))
    tiles = getv(raw, "tiles", []) or []
    farmer = as_pos(getv(raw, "farmer", [0, 0])) or (0, 0)
    hands_raw = getv(raw, "hands", []) or []
    hands = [as_pos(h) or (0, 0) for h in hands_raw]
    unlocked = list(getv(raw, "unlocked_quadrants", ["NW"]) or ["NW"])
    hires = as_int(getv(raw, "hires_today", 0))

    plants = []
    animals = []
    weeds = []
    empty = []
    empty_structures = []

    n = len(tiles) if tiles else board_size
    for y in range(n):
        row = tiles[y]
        for x in range(len(row)):
            tile = row[x]
            if tile is None:
                empty.append((x, y))
                continue
            if tile == "LOCKED":
                continue
            kind = getv(tile, "kind") if not isinstance(tile, str) else None
            animal = getv(tile, "animal", None) if not isinstance(tile, str) else None
            if kind == "WEED":
                weeds.append((x, y))
            elif kind == "PLANT":
                plants.append(Plant(
                    x=x, y=y,
                    crop=str(getv(tile, "crop")),
                    planted_day=as_int(getv(tile, "planted_day", 0)),
                    watered_today=bool(getv(tile, "watered_today", False)),
                    consecutive_unwatered=as_int(getv(tile, "consecutive_unwatered", 0)),
                    yield_units=as_int(getv(tile, "yield_units", 0)),
                    max_lifespan_step=as_int(getv(tile, "max_lifespan_step", -1)),
                    fertilized_until_day=as_int(getv(tile, "fertilized_until_day", -1)),
                ))
            elif animal in ANIMALS:
                animals.append(Animal(
                    x=x, y=y,
                    kind=str(kind or ANIMALS[animal]["structure"]),
                    animal=str(animal),
                    placed_day=as_int(getv(tile, "placed_day", 0)),
                    yield_units=as_int(getv(tile, "yield_units", 0)),
                    fed_today=bool(getv(tile, "fed_today", False)),
                    consecutive_unfed=as_int(getv(tile, "consecutive_unfed", 0)),
                    cared_today=bool(getv(tile, "cared_today", False)),
                    fertilizer_available=bool(getv(tile, "fertilizer_available", False)),
                    pending_care_bonus=as_int(getv(tile, "pending_care_bonus", 0)),
                ))
            elif kind in ("COOP", "PASTURE"):
                empty_structures.append(Structure(x=x, y=y, kind=str(kind)))

    return FarmView(
        money=money, tiles=tiles, farmer=farmer, hands=hands,
        unlocked_quadrants=unlocked, hires_today=hires,
        plants=plants, animals=animals, weeds=weeds, empty=empty,
        empty_structures=empty_structures, board_size=n,
    )


def _inv_map(raw) -> dict[str, int]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(k): as_int(v, 0) for k, v in raw.items()}
    try:
        return {str(k): as_int(v, 0) for k, v in raw.items()}
    except Exception:
        return {}


def parse_state(obs, config=None) -> GameState:
    config = config or {}
    player = as_int(getv(obs, "player", 0))
    step = as_int(getv(obs, "step", 0))
    day = as_int(getv(obs, "day", 0))
    hour = as_int(getv(obs, "hour", 0))
    farms = getv(obs, "farms", []) or []
    board_size = as_int(getv(config, "boardSize", DEFAULT_BOARD), DEFAULT_BOARD)
    turns_per_day = as_int(getv(config, "turnsPerDay", DEFAULT_TURNS_PER_DAY), DEFAULT_TURNS_PER_DAY)
    episode_steps = as_int(getv(config, "episodeSteps", DEFAULT_STEPS), DEFAULT_STEPS)
    shed_capacity = as_int(getv(config, "shedCapacity", DEFAULT_SHED), DEFAULT_SHED)
    days_total = max(1, (episode_steps + turns_per_day - 1) // turns_per_day)
    if days_total < DEFAULT_DAYS and episode_steps >= DEFAULT_STEPS:
        days_total = DEFAULT_DAYS

    me_raw = farms[player] if player < len(farms) else farms[0]
    opp_raw = farms[1 - player] if len(farms) > 1 else farms[0]
    me = parse_farm(me_raw, board_size)
    opp = parse_farm(opp_raw, board_size)

    market = getv(obs, "market", {}) or {}
    market_inv = _inv_map(getv(market, "inventory", {}))
    market_prices = _inv_map(getv(market, "prices", {}))
    for p in PRODUCTS:
        market_inv.setdefault(p, 10000)
        market_prices.setdefault(p, 0)

    town = getv(obs, "town", {}) or {}
    shops = list(getv(town, "unlocked_shops", []) or [])

    private = getv(obs, "private", {}) or {}
    shed = _inv_map(getv(private, "shed", {}))
    seeds = _inv_map(getv(private, "seeds", {}))
    invs = getv(private, "inventories", [{}]) or [{}]

    workers = []
    positions = [me.farmer] + list(me.hands)
    for i, pos in enumerate(positions):
        inv = _inv_map(invs[i] if i < len(invs) else {})
        workers.append(Worker(idx=i, pos=pos, inventory=inv))

    return GameState(
        player=player, step=step, day=day, hour=hour,
        me=me, opp=opp,
        market_inv=market_inv, market_prices=market_prices,
        shops=shops, shed=shed, seeds=seeds, workers=workers,
        board_size=me.board_size or board_size,
        turns_per_day=turns_per_day,
        episode_steps=episode_steps,
        shed_capacity=shed_capacity,
        days_total=days_total,
    )
