"""Kaggriculture Kaggle agent. Single-file so exec() loading works without __file__ or packages."""
from __future__ import annotations

# === constants.py ===
"""Game constants mirrored from installed kaggle_environments 1.32.7 kaggriculture.py."""


import math

CROPS = {
    "WHEAT":      {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT":     {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO":     {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON":      {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}

ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
ANIMAL_NAMES = list(ANIMALS.keys())
CROP_NAMES = list(CROPS.keys())

MARKET_I0 = 10000
PRICE_FLOOR = 1
HINGE_GAIN = 8.0

MARKET_PARAMS = {
    "WHEAT":      {"base":  25, "I0": MARKET_I0, "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base":  35, "I0": MARKET_I0, "T": 450, "below_func": "hinge",  "below_target": 1.00, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base":  60, "I0": MARKET_I0, "T": 200, "below_func": "hinge",  "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": MARKET_I0, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "I0": MARKET_I0, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base":  50, "I0": MARKET_I0, "T": 332, "below_func": "hinge",  "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "I0": MARKET_I0, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "I0": MARKET_I0, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": MARKET_I0, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

FARMER_MOVES = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST":  (1, 0),
    "WEST":  (-1, 0),
}
MOVE_FROM_DELTA = {v: k for k, v in FARMER_MOVES.items()}

LAND_ORDER = ["NE", "SW", "SE"]
LAND_PRICES = [1000, 2000, 4000]
QUADRANT_ALL = ["NW", "NE", "SW", "SE"]

SHOPS = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA_SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE":     ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE":       ["CARROT"],
    "SMOOTHIE_SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

TOWN_CENTER_PRODUCTS = [p for p in PRODUCTS if p != "FERTILIZER"]
MAX_SHOP_INSTANCES = 8
MAX_MARKET_ORDERS = 10
DEFAULT_BOARD = 10
DEFAULT_TURNS_PER_DAY = 24
DEFAULT_DAYS = 30
DEFAULT_STEPS = 720
DEFAULT_SHED = 100
DEFAULT_STARTING_MONEY = 3000
DEFAULT_WEED_CHANCE = 0.005
FRAGILE_PRODUCTS = {"STRAWBERRY", "MELON", "MILK", "WOOL"}
BUYABLE_PRODUCTS = ("WHEAT", "FERTILIZER")


def shape(func: str, x: float, T=None) -> float:
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "log10":
        return math.log10(1.0 + x)
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + HINGE_GAIN * max(0.0, u - 1.0) ** 2
    return x


def market_price(item: str, inventory: int, params=None) -> int:
    p = (params or MARKET_PARAMS)[item]
    base = p["base"]
    I0 = p["I0"]
    T = p["T"]
    if inventory < I0:
        f = p["below_func"]
        amp = p["below_target"] * base / shape(f, T, T)
        price = base + amp * shape(f, I0 - inventory, T)
    else:
        f = p["above_func"]
        amp = p["above_target"] * base / shape(f, T, T)
        price = base - amp * shape(f, inventory - I0, T)
    return max(PRICE_FLOOR, int(round(price)))


def fib(n: int) -> int:
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def hire_cost(n_already_today: int, mult: int = 1) -> int:
    return mult * fib(n_already_today)


def shed_access_tiles(board_size: int = 10) -> list[tuple[int, int]]:
    half = board_size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def quadrant_of(x: int, y: int, board_size: int = 10) -> str:
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def watering_window(crop: str) -> tuple[int, int]:
    cd = CROPS[crop]
    start = (cd["max_yield_day"] + 1) // 2
    return start, cd["max_yield_day"]

# === config.py ===
"""Tunable strategy parameters. Keep all thresholds here for experiments."""


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

# === movement.py ===
"""BFS pathfinding. Locked tiles are passable. Occupancy is allowed."""


from collections import deque



def in_bounds(x: int, y: int, n: int) -> bool:
    return 0 <= x < n and 0 <= y < n


def neighbors(pos: tuple[int, int], n: int):
    x, y = pos
    for dx, dy in FARMER_MOVES.values():
        nx, ny = x + dx, y + dy
        if in_bounds(nx, ny, n):
            yield (nx, ny)


def bfs_next_step(start: tuple[int, int], goal: tuple[int, int], n: int) -> str | None:
    """Return a movement op that reduces distance to goal, or None if already there / unreachable."""
    if start == goal:
        return None
    sx, sy = start
    gx, gy = goal
    # Manhattan greedy first (grid has no obstacles that block movement).
    dx = 0 if gx == sx else (1 if gx > sx else -1)
    dy = 0 if gy == sy else (1 if gy > sy else -1)
    # Prefer the larger remaining axis to keep paths short.
    if abs(gx - sx) >= abs(gy - sy) and dx:
        nx, ny = sx + dx, sy
        if in_bounds(nx, ny, n):
            return MOVE_FROM_DELTA[(dx, 0)]
    if dy:
        nx, ny = sx, sy + dy
        if in_bounds(nx, ny, n):
            return MOVE_FROM_DELTA[(0, dy)]
    if dx:
        nx, ny = sx + dx, sy
        if in_bounds(nx, ny, n):
            return MOVE_FROM_DELTA[(dx, 0)]
    return None


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def nearest(origin: tuple[int, int], targets: list[tuple[int, int]]) -> tuple[int, int] | None:
    if not targets:
        return None
    return min(targets, key=lambda t: manhattan(origin, t))


def bfs_path_exists(start: tuple[int, int], goal: tuple[int, int], n: int) -> bool:
    if start == goal:
        return True
    seen = {start}
    q = deque([start])
    while q:
        cur = q.popleft()
        for nxt in neighbors(cur, n):
            if nxt in seen:
                continue
            if nxt == goal:
                return True
            seen.add(nxt)
            q.append(nxt)
    return False

# === state.py ===
"""Normalized observation parsing. Works with dicts and kaggle structify objects."""


from dataclasses import dataclass, field
from typing import Any, Optional

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

# === farm.py ===
"""Farm tile helpers."""




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

# === market.py ===
"""Market pricing, town demand, and sale/buy policy."""




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
    """Sell produce. Keep only wheat that animals will eat tonight/tomorrow."""
    remaining = state.remaining_days
    n_animals = state.livestock_heads()
    wheat_keep = n_animals if cfg.keep_wheat_for_feed else 0
    if remaining <= cfg.liquidation_days:
        wheat_keep = 0

    fert_keep = 0
    if remaining > cfg.liquidation_days and n_animals > 0 and state.money >= 80:
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
            fert_keep = min(want_fert, 6)
        else:
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

# === ranch.py ===
"""Ranch engine: price-forecast livestock + filler crops, value-per-distance worker matching.

Every purchase is scored by the money it returns before the game ends, using a
market forecast that counts our supply, the opponent's visible supply and town
demand. Nothing is tuned to one opponent; gluts lower scores automatically.
"""


from dataclasses import dataclass


PRODUCT_OF = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
DAILY_RATE = {"GOOSE": 2.0, "COW": 1.5, "SHEEP": 4.0 / 3.0}
NIGHT_ADD = {"GOOSE": 2, "COW": 3, "SHEEP": 4}
LABOR_PER_ANIMAL = 7.0
LABOR_PER_PLANT = 3.0
TURNS_PER_WORKER = 22.0
MAX_HANDS = 13
DIST_W = 5.0
STAY_BONUS = 40.0
HUB = (4.5, 4.5)


@dataclass
class RanchConfig:
    version: str = "v7-ranch"
    min_animal_roi: float = 0.3
    land_min_remaining: int = 8
    land_idle_cash: float = 4000.0
    land_cash_after: float = 600.0
    max_unplaced: int = 6
    labor_cost_per_day: float = 8.0
    fragile_floor_frac: float = 0.2
    melon_min_remaining: int = 14
    melon_min_value: float = 500.0
    horizon_days: int = 14
    daily_discount: float = 0.04
    glut_weight: float = 0.7
    rich_cash: float = 2500.0
    opp_visible_floor: float = 0.3


@dataclass
class Job:
    value: float
    pos: tuple
    action: list
    key: str
    need_item: str | None = None
    worker: int | None = None
    tile_op: bool = True


def _hub_dist(p) -> float:
    return abs(p[0] - HUB[0]) + abs(p[1] - HUB[1])


class Outlook:
    """Forecast prices from both farms' visible supply and town demand."""

    def __init__(self, state: GameState, cfg: "RanchConfig", opp_sold: dict | None = None):
        self.state = state
        self.cfg = cfg
        self.R = state.remaining_days
        self.rich = state.money >= cfg.rich_cash
        self.demand = town_demand_per_day(state.shops, state.turns_per_day)
        self.my_rate = {p: 0.0 for p in PRODUCTS}
        visible = {p: 0.0 for p in PRODUCTS}
        opp = state.opp.animal_counts()
        self.herd_both = 0
        for a in ANIMALS:
            mine = state.animal_owned(a)
            theirs = opp.get(a, 0)
            self.my_rate[PRODUCT_OF[a]] += mine * DAILY_RATE[a]
            self.my_rate["FERTILIZER"] += mine
            visible[PRODUCT_OF[a]] += theirs * DAILY_RATE[a]
            visible["FERTILIZER"] += theirs
            self.herd_both += mine + theirs
        # Opponent supply: what they were seen selling, but at least a share of their herd's output.
        self.supply = {}
        for p in PRODUCTS:
            seen = opp_sold.get(p) if opp_sold else None
            theirs = visible[p] * 0.7 if seen is None else max(seen, visible[p] * cfg.opp_visible_floor)
            self.supply[p] = self.my_rate[p] + theirs
        # Stock we still hold is supply the market has not seen yet.
        self.held = {p: state.shed_count(p) + state.carried_count(p) for p in PRODUCTS}
        for a in state.me.animals:
            self.held[PRODUCT_OF[a.animal]] += a.yield_units
        self.melons = state.me.crop_counts().get("MELON", 0) + state.opp.crop_counts().get("MELON", 0)

    def horizon(self) -> float:
        return max(1.0, min(self.R, self.cfg.horizon_days) / 2.0)

    def price(self, item: str, extra_rate: float = 0.0) -> float:
        surplus = self.supply[item] + extra_rate - self.demand.get(item, 0.0)
        held = self.held.get(item, 0) if item != "WHEAT" else 0
        inv = self.state.market_inv.get(item, MARKET_PARAMS[item]["I0"]) + held + surplus * self.horizon()
        return float(market_price(item, int(inv)))

    def wheat_price(self) -> float:
        inv = self.state.market_inv.get("WHEAT", 10000) - self.herd_both * 0.5 * self.horizon()
        return float(max(market_price("WHEAT", int(inv)), self.state.market_prices.get("WHEAT", 25)))

    def animal_value(self, animal: str, cfg: "RanchConfig") -> float:
        """Discounted marginal profit of one more head bought today."""
        R = self.R
        a = ANIMALS[animal]
        prod = PRODUCT_OF[animal]
        disc = 1.0 if self.rich else 1.0 - cfg.daily_discount
        p0, p1 = self.price(prod), self.price(prod, DAILY_RATE[animal])
        f0, f1 = self.price("FERTILIZER"), self.price("FERTILIZER", 1.0)
        daily_cost = self.wheat_price() + cfg.labor_cost_per_day
        value = 0.0
        for t in range(R):
            if t >= 1:
                value += f1 * disc ** t
            if t <= R - 2:
                value -= daily_cost * disc ** t
        first, iv = a["first_yield_day"], a["interval"]
        t, k = first, 0
        while t <= R - 1:
            units = min(a["max_held"], first) if k == 0 else NIGHT_ADD[animal]
            value += units * p1 * disc ** t
            t += iv
            k += 1
        days = max(0, R - 1)
        value -= cfg.glut_weight * (self.my_rate[prod] * days * (p0 - p1) + self.my_rate["FERTILIZER"] * days * (f0 - f1))
        return value - a["cost"]

    def clone(self) -> "Outlook":
        c = Outlook.__new__(Outlook)
        c.__dict__.update(self.__dict__)
        c.supply = dict(self.supply)
        c.my_rate = dict(self.my_rate)
        return c

    def add_animal(self, animal: str):
        self.supply[PRODUCT_OF[animal]] += DAILY_RATE[animal]
        self.supply["FERTILIZER"] += 1
        self.my_rate[PRODUCT_OF[animal]] += DAILY_RATE[animal]
        self.my_rate["FERTILIZER"] += 1
        self.herd_both += 1

    def melon_value(self) -> float:
        if self.R < 14:
            return -1.0
        surplus = (self.melons + 1) * 6 - self.demand.get("MELON", 0.0) * 13
        inv = self.state.market_inv.get("MELON", 10000) + max(0.0, surplus) * 0.5
        return 6 * market_price("MELON", int(inv)) - CROPS["MELON"]["seed"] - 13 * 4

    def filler_crop(self) -> str | None:
        R = self.R
        opts = []
        if R >= 5:
            wheat = self.price("WHEAT")
            if self.my_rate["FERTILIZER"] > 0:
                wheat = max(wheat, self.wheat_price())
            opts.append(((4 * wheat - 10) / 5.0, "WHEAT"))
        if R >= 4:
            opts.append(((3 * self.price("CARROT") - 20) / 4.0, "CARROT"))
        opts = [o for o in opts if o[0] > 3]
        return max(opts)[1] if opts else None


def _cum_hire_cost(n_hands: int) -> int:
    return sum(hire_cost(i) for i in range(n_hands))


class RanchAgent:
    def __init__(self, cfg: RanchConfig | None = None):
        self.cfg = cfg or RanchConfig()
        self.last_key: dict[int, str] = {}
        self.last_step = -1
        self._reset_tracking()

    def _reset_tracking(self):
        self.track_day = -1
        self.day_inv: dict[str, int] | None = None
        self.day_demand: dict[str, float] = {}
        self.my_flow: dict[str, int] = {}
        self.opp_sold: dict[str, float] = {}

    def _track_market(self, state: GameState):
        """Infer the opponent's daily sales from market inventory changes."""
        if state.step < self.last_step:
            self._reset_tracking()
        if state.day == self.track_day:
            return
        if self.day_inv is not None and state.day == self.track_day + 1:
            for p in PRODUCTS:
                if p == "WHEAT":
                    continue
                delta = state.market_inv.get(p, 0) - self.day_inv.get(p, 0)
                seen = max(0.0, delta + self.day_demand.get(p, 0.0) - self.my_flow.get(p, 0))
                prev = self.opp_sold.get(p)
                self.opp_sold[p] = seen if prev is None else 0.5 * prev + 0.5 * seen
        self.track_day = state.day
        self.day_inv = dict(state.market_inv)
        self.day_demand = town_demand_per_day(state.shops, state.turns_per_day)
        self.my_flow = {}

    # ------------------------------------------------------------------ entry
    def act(self, obs, env_config=None) -> dict:
        state = parse_state(obs, env_config)
        self._track_market(state)
        out = Outlook(state, self.cfg, self.opp_sold)
        plan = self._plan_tiles(state, out)
        jobs = self._jobs(state, out, plan)
        actions = self._assign(state, jobs)
        market = self._market(state, out, plan, actions)
        for o in market:
            if o[0] == "SELL":
                self.my_flow[o[1]] = self.my_flow.get(o[1], 0) + o[2]
            elif o[0] == "BUY_PRODUCT":
                self.my_flow[o[1]] = self.my_flow.get(o[1], 0) - o[2]
        farmer = actions.get(0, ["PASS"])
        hands = [actions.get(i + 1, ["PASS"]) for i in range(len(state.me.hands))]
        return {"farmer": farmer, "hands": hands, "market": market}

    # ------------------------------------------------------------- tile plan
    def _plan_tiles(self, state: GameState, out: Outlook) -> dict:
        free = sorted(state.me.empty, key=_hub_dist)
        unplaced = {a: state.shed_count(a) + state.carried_count(a) for a in ANIMALS}
        slots = {"COOP": 0, "PASTURE": 0}
        for s in state.me.empty_structures:
            slots[s.kind] += 1
        need = {"COOP": unplaced["GOOSE"], "PASTURE": unplaced["COW"] + unplaced["SHEEP"]}
        builds = []
        fi = 0
        for kind in ("PASTURE", "COOP"):
            for _ in range(max(0, need[kind] - slots[kind])):
                if fi >= len(free):
                    break
                builds.append((free[fi], kind))
                fi += 1
        rest = free[fi:]
        cash_soon = state.money + self._daily_income_guess(state, out)
        wanted = self._want_animals(state, out.clone(), cash_soon, self._labor(state, {"builds": builds}))
        spare_slots = max(0, slots["COOP"] + slots["PASTURE"] - (sum(unplaced.values()) - len(builds)))
        reserve = min(len(rest), max(0, len(wanted) - spare_slots + (1 if wanted else 0)))
        animal_zone = rest[:reserve]
        crop_tiles = rest[reserve:]
        return {
            "builds": builds,
            "animal_zone": animal_zone,
            "crop_tiles": crop_tiles,
            "wanted": wanted,
            "unplaced": unplaced,
            "slots": slots,
        }

    def _want_animals(self, state: GameState, out: Outlook, cash: float, labor: float) -> list[str]:
        """Animals worth buying with this cash if space were unlimited, best first."""
        cfg = self.cfg
        labor_cap = (1 + MAX_HANDS) * TURNS_PER_WORKER
        reserve = 40.0 + sum(state.animal_owned(a) for a in ANIMALS) * out.wheat_price() * 0.5
        wanted: list[str] = []
        while len(wanted) < 40 and labor + LABOR_PER_ANIMAL < labor_cap:
            roi, animal = max((out.animal_value(a, cfg) / ANIMALS[a]["cost"], a) for a in ANIMALS)
            cost = ANIMALS[animal]["cost"]
            if roi < cfg.min_animal_roi or cash - cost < reserve:
                break
            wanted.append(animal)
            cash -= cost
            out.add_animal(animal)
            labor += LABOR_PER_ANIMAL
        return wanted

    def _daily_income_guess(self, state: GameState, out: Outlook) -> float:
        g = 0.0
        for a in state.me.animals:
            g += out.price("FERTILIZER") + DAILY_RATE[a.animal] * out.price(PRODUCT_OF[a.animal]) * 0.8
        return g

    # ----------------------------------------------------------------- jobs
    def _jobs(self, state: GameState, out: Outlook, plan: dict) -> list[Job]:
        jobs: list[Job] = []
        R = out.R
        last_day = R <= 1
        tpd = state.turns_per_day
        hour = state.hour
        shed_tiles = state.shed_tiles()
        near_shed = lambda p: min(shed_tiles, key=lambda s: manhattan(p, s))
        p_fert = float(state.market_prices.get("FERTILIZER", 100) or 1)

        # Animals: feed, care, fertilizer, harvest.
        unfed = [a for a in state.me.animals if not a.fed_today]
        if not last_day:
            for a in unfed:
                v = 400.0 if a.consecutive_unfed >= 1 else 70.0
                jobs.append(Job(v, a.pos, ["FEED"], f"feed{a.pos}", need_item="WHEAT"))
        for a in state.me.animals:
            if R >= 3 and not a.cared_today:
                jobs.append(Job(45.0, a.pos, ["CARE"], f"care{a.pos}"))
            if a.fertilizer_available and p_fert > 3:
                jobs.append(Job(max(10.0, 0.8 * p_fert), a.pos, ["COLLECT_FERTILIZER"], f"fz{a.pos}"))
            if a.yield_units > 0:
                cap = ANIMALS[a.animal]["max_held"]
                v = 15.0 + 8.0 * a.yield_units
                if a.yield_units + NIGHT_ADD[a.animal] > cap:
                    v += 90.0
                if last_day:
                    v = 150.0
                jobs.append(Job(v, a.pos, ["HARVEST"], f"ah{a.pos}"))

        # Wheat for feeding: every worker carries its share.
        if not last_day and unfed:
            carried = state.carried_count("WHEAT")
            shed_w = state.shed_count("WHEAT")
            n_w = max(1, len(state.workers))
            share = min(10, -(-len(unfed) // n_w) + 2)
            if len(unfed) > carried and shed_w > 0:
                for w in state.workers:
                    if w.inv_count("WHEAT") >= share or any(w.inv_count(x) for x in ANIMALS):
                        continue
                    n = min(share - w.inv_count("WHEAT"), shed_w)
                    if n <= 0:
                        break
                    jobs.append(Job(90.0, near_shed(w.pos), ["PICKUP", "WHEAT", n], f"pw{w.idx}", worker=w.idx, tile_op=False))
                    shed_w -= n
            elif len(unfed) > carried:
                for p in state.me.plants:
                    if p.crop == "WHEAT" and p.yield_units > 0 and p.age(state.day) >= CROPS["WHEAT"]["first_yield_day"]:
                        jobs.append(Job(85.0, p.pos, ["HARVEST"], f"ph{p.pos}"))

        # Livestock logistics: build, pick up, place.
        for pos, kind in plan["builds"]:
            op = "BUILD_COOP" if kind == "COOP" else "BUILD_PASTURE"
            jobs.append(Job(75.0, pos, [op], f"b{pos}"))
        empty_struct = {"COOP": [s.pos for s in state.me.empty_structures if s.kind == "COOP"],
                        "PASTURE": [s.pos for s in state.me.empty_structures if s.kind == "PASTURE"]}
        for w in state.workers:
            for animal in ANIMALS:
                if w.inv_count(animal) <= 0:
                    continue
                kind = ANIMALS[animal]["structure"]
                if empty_struct[kind]:
                    dest = min(empty_struct[kind], key=lambda p: manhattan(w.pos, p))
                    jobs.append(Job(150.0, dest, ["PLACE", animal], f"pl{w.idx}{animal}", worker=w.idx))
                else:
                    tiles = [p for p, k in plan["builds"] if k == kind] or plan["animal_zone"] or plan["crop_tiles"]
                    if tiles:
                        dest = min(tiles, key=lambda p: manhattan(w.pos, p))
                        op = "BUILD_COOP" if kind == "COOP" else "BUILD_PASTURE"
                        jobs.append(Job(140.0, dest, [op], f"b{dest}", worker=w.idx))
        for animal in ANIMALS:
            n_shed = state.shed_count(animal)
            if n_shed <= 0:
                continue
            kind = ANIMALS[animal]["structure"]
            ready = len(empty_struct[kind]) + sum(1 for _, k in plan["builds"] if k == kind)
            carried = state.carried_count(animal)
            n = min(n_shed, max(0, ready - carried), 4)
            if n > 0:
                jobs.append(Job(80.0, shed_tiles[0], ["PICKUP", animal, n], f"pa{animal}", tile_op=False))

        # Plants.
        for p in state.me.plants:
            cd = CROPS[p.crop]
            age = p.age(state.day)
            if not p.watered_today and not last_day:
                if p.consecutive_unwatered >= 1:
                    jobs.append(Job(250.0, p.pos, ["WATER"], f"w{p.pos}"))
                elif water_adds_yield(p, state.day):
                    jobs.append(Job(60.0 if p.crop != "MELON" else 90.0, p.pos, ["WATER"], f"w{p.pos}"))
                elif cd["ongoing"] or age < cd["max_yield_day"]:
                    jobs.append(Job(12.0, p.pos, ["WATER"], f"w{p.pos}"))
            if p.yield_units > 0 and age >= cd["first_yield_day"]:
                price = float(state.market_prices.get(p.crop, 10) or 1)
                bonus = min(60.0, price * p.yield_units / 20)
                capped = age > cd["max_yield_day"] or (age == cd["max_yield_day"] and p.watered_today)
                if decaying(p, state.step):
                    jobs.append(Job(120.0, p.pos, ["HARVEST"], f"ph{p.pos}"))
                elif last_day:
                    jobs.append(Job(100.0 + bonus, p.pos, ["HARVEST"], f"ph{p.pos}"))
                elif cd["ongoing"] or capped:
                    jobs.append(Job(40.0 + bonus, p.pos, ["HARVEST"], f"ph{p.pos}"))

        # New plantings on crop tiles (must be watered the same day).
        if hour <= tpd - 3 and not last_day:
            seeds = dict(state.seeds)
            for pos in plan["crop_tiles"]:
                crop = next((c for c in ("MELON", "CARROT", "WHEAT") if seeds.get(c, 0) > 0), None)
                if not crop:
                    break
                seeds[crop] -= 1
                jobs.append(Job(50.0 if crop == "MELON" else 35.0, pos, ["PLANT", crop], f"pt{pos}"))
            if not plan["crop_tiles"] and not plan["animal_zone"] and not plan["builds"]:
                for pos in state.me.weeds:
                    jobs.append(Job(8.0, pos, ["DIG"], f"d{pos}"))

        # Drop produce at the shed: last day, overflow risk, or when passing by.
        saleable = lambda w: sum(n for it, n in w.inventory.items() if it in PRODUCTS and (it != "WHEAT" or last_day or not unfed))
        pending = sum(saleable(w) for w in state.workers)
        overflow = hour >= tpd - 6 and state.shed_total() + pending > state.shed_capacity - 8
        for w in state.workers:
            c = saleable(w)
            if c <= 0 or any(w.inv_count(a) for a in ANIMALS):
                continue
            if last_day and hour >= tpd - 8:
                v = 300.0
            elif overflow:
                v = 150.0
            else:
                v = (4.0 if state.money < 1500 else 2.0) * c
            jobs.append(Job(v, near_shed(w.pos), ["DROP"], f"dr{w.idx}", worker=w.idx, tile_op=False))
        return jobs

    # ------------------------------------------------------------ matching
    def _assign(self, state: GameState, jobs: list[Job]) -> dict[int, list]:
        if state.step != self.last_step + 1 or state.hour == 0:
            self.last_key = {}
        self.last_step = state.step
        pairs = []
        for j in jobs:
            for w in state.workers:
                if j.worker is not None and j.worker != w.idx:
                    continue
                if j.need_item and w.inv_count(j.need_item) <= 0:
                    continue
                holder = any(w.inv_count(a) > 0 for a in ANIMALS)
                if holder and j.action[0] not in ("PLACE", "BUILD_COOP", "BUILD_PASTURE"):
                    continue
                d = manhattan(w.pos, j.pos)
                stick = 30.0 if self.last_key.get(w.idx) == j.key else 0.0
                pairs.append((j.value - DIST_W * d + (STAY_BONUS if d == 0 else 0.0) + stick, w.idx, id(j), j))
        pairs.sort(key=lambda t: -t[0])
        busy: set[int] = set()
        used_keys: set[str] = set()
        used_pos: set = set()
        pos_of = {w.idx: w.pos for w in state.workers}
        actions: dict[int, list] = {w.idx: ["PASS"] for w in state.workers}
        for score, widx, _, j in pairs:
            if widx in busy or j.key in used_keys:
                continue
            here = pos_of[widx] == j.pos
            if j.tile_op and here and j.pos in used_pos:
                continue
            if here:
                actions[widx] = list(j.action)
                if j.tile_op:
                    used_pos.add(j.pos)
                self.last_key.pop(widx, None)
            else:
                step = bfs_next_step(pos_of[widx], j.pos, state.board_size)
                actions[widx] = [step] if step else ["PASS"]
                self.last_key[widx] = j.key
            busy.add(widx)
            used_keys.add(j.key)
        return actions

    # --------------------------------------------------------------- market
    def _market(self, state: GameState, out: Outlook, plan: dict, actions: dict) -> list:
        cfg = self.cfg
        R = out.R
        last_day = R <= 1
        orders: list = []
        money = float(state.money)
        dropping = {i for i, a in actions.items() if a and a[0] == "DROP"}
        in_bag: dict[str, int] = {}
        for w in state.workers:
            if w.idx in dropping:
                for it, n in w.inventory.items():
                    in_bag[it] = in_bag.get(it, 0) + n

        # 1. Sell first so the cash is there for hires and buys.
        unfed = sum(1 for a in state.me.animals if not a.fed_today)
        herd = sum(state.animal_owned(a) for a in ANIMALS)
        wheat_keep = 0 if R <= 2 else max(0, unfed - state.carried_count("WHEAT") + in_bag.get("WHEAT", 0))
        if state.hour >= state.turns_per_day - 4 and R > 2:
            wheat_keep = max(wheat_keep, herd)
        for item in PRODUCTS:
            have = state.shed_count(item) + in_bag.get(item, 0)
            if item == "WHEAT":
                have -= wheat_keep
            if have <= 0:
                continue
            floor = 1
            if item in FRAGILE_PRODUCTS and R > 2 and state.shed_total() < state.shed_capacity - 30:
                floor = int(cfg.fragile_floor_frac * MARKET_PARAMS[item]["base"])
            inv = state.market_inv.get(item, 10000)
            n = 0
            gain = 0.0
            while n < have:
                p = market_price(item, inv + n)
                if p < floor:
                    break
                gain += p
                n += 1
            if n > 0:
                orders.append(["SELL", item, n])
                money += gain

        # 2. Hire for today's workload.
        n_workers = 1 + len(state.me.hands)
        want = self._workers_wanted(state, plan)
        k = state.me.hires_today
        while n_workers < want and len(orders) < MAX_MARKET_ORDERS - 2 and len(state.me.hands) < MAX_HANDS:
            c = hire_cost(k)
            if money - c < 20 or c > 260:
                break
            orders.append(["HIRE"])
            money -= c
            k += 1
            n_workers += 1

        # 3. Wheat for today's feed.
        if not last_day and len(orders) < MAX_MARKET_ORDERS:
            have_w = state.shed_count("WHEAT") + state.carried_count("WHEAT")
            need = unfed + 2 - have_w
            if state.hour >= state.turns_per_day - 3:
                need = 0
            wp = float(state.market_prices.get("WHEAT", 25) or 25)
            n = min(max(0, need), state.shed_room(), int(max(0.0, money - 20) // max(1.0, wp * 1.1)))
            if n > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", n])
                money -= n * wp * 1.1

        # 4. Livestock by forecast value per dollar.
        reserve = 40.0 + herd * out.wheat_price() * 0.5
        unplaced = sum(plan["unplaced"].values())
        room = len(plan["builds"]) + len(plan["animal_zone"]) + plan["slots"]["COOP"] + plan["slots"]["PASTURE"]
        room = max(0, room - max(0, unplaced - len(plan["builds"]) - plan["slots"]["COOP"] - plan["slots"]["PASTURE"]))
        room = min(room, cfg.max_unplaced - unplaced, state.shed_room())
        labor_cap = (1 + MAX_HANDS) * TURNS_PER_WORKER
        labor_now = self._labor(state, plan)
        buys: dict[str, int] = {}
        while room > 0 and len(orders) + len(buys) < MAX_MARKET_ORDERS - 1 and labor_now + LABOR_PER_ANIMAL < labor_cap:
            scored = [(out.animal_value(a, cfg) / ANIMALS[a]["cost"], a) for a in ANIMALS]
            roi, animal = max(scored)
            cost = ANIMALS[animal]["cost"]
            if roi < cfg.min_animal_roi or money - cost < reserve:
                break
            buys[animal] = buys.get(animal, 0) + 1
            money -= cost
            out.add_animal(animal)
            room -= 1
            labor_now += LABOR_PER_ANIMAL
        for animal, n in buys.items():
            orders.append(["BUY_ANIMAL", animal, n])

        # 5. Land when the buy plan wants more heads than we have room for,
        #    or when idle cash can turn a new quadrant into home-grown feed.
        extra = len(state.me.unlocked_quadrants) - 1
        if extra < 3 and len(orders) < MAX_MARKET_ORDERS and R >= cfg.land_min_remaining:
            cost = LAND_PRICES[extra]
            space = len(plan["animal_zone"]) + len(plan["crop_tiles"]) + plan["slots"]["COOP"] + plan["slots"]["PASTURE"]
            crowded = len(plan["wanted"]) > space - 1
            idle = money >= cost + cfg.land_idle_cash and len(plan["crop_tiles"]) < 6 and R >= cfg.land_min_remaining + 2
            if (crowded or idle) and money >= cost + cfg.land_cash_after:
                orders.append(["BUY_LAND"])
                money -= cost

        # 6. Seeds for the crop tiles that labor can water.
        crop_tiles = len(plan["crop_tiles"])
        if crop_tiles and not last_day and len(orders) < MAX_MARKET_ORDERS:
            have_seeds = sum(state.seeds.values())
            spare_labor = max(0.0, (1 + MAX_HANDS) * TURNS_PER_WORKER - labor_now) / LABOR_PER_PLANT
            n_plant = int(min(crop_tiles - have_seeds, spare_labor))
            budget = money - reserve
            if n_plant > 0 and budget > 0:
                n_melon = 0
                mv = out.melon_value()
                if mv >= cfg.melon_min_value:
                    n_melon = min(n_plant, int(budget * 0.5 // CROPS["MELON"]["seed"]), max(0, 12 - out.melons))
                if n_melon > 0:
                    orders.append(["BUY_SEED", "MELON", n_melon])
                    budget -= n_melon * CROPS["MELON"]["seed"]
                    money -= n_melon * CROPS["MELON"]["seed"]
                    n_plant -= n_melon
                filler = out.filler_crop()
                if filler and n_plant > 0 and len(orders) < MAX_MARKET_ORDERS:
                    n = min(n_plant, int(budget // CROPS[filler]["seed"]))
                    if n > 0:
                        orders.append(["BUY_SEED", filler, n])
        return orders[:MAX_MARKET_ORDERS]

    def _labor(self, state: GameState, plan: dict) -> float:
        herd = sum(state.animal_owned(a) for a in ANIMALS)
        return herd * LABOR_PER_ANIMAL + len(state.me.plants) * LABOR_PER_PLANT + len(plan["builds"]) * 3

    def _workers_wanted(self, state: GameState, plan: dict) -> int:
        load = self._labor(state, plan) + 2 * min(len(plan["crop_tiles"]), sum(state.seeds.values()) + 6)
        if state.remaining_days <= 1:
            load *= 0.7
        return max(3, min(1 + MAX_HANDS, int(load / TURNS_PER_WORKER + 0.999) + 1))


def ranch_agent(cfg: RanchConfig | None = None):
    brain = RanchAgent(cfg)

    def agent(obs, config=None):
        return brain.act(obs, config)

    return agent


_AGENT = RanchAgent()


def agent(obs, config=None):
    try:
        return _AGENT.act(obs, config)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
