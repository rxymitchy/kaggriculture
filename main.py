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

# === inventory.py ===
"""Shed capacity and inventory projections."""




def projected_occupancy(state: GameState) -> int:
    return state.shed_total() + state.carried_total()


def room_after_harvest(state: GameState, units: int) -> int:
    return state.shed_capacity - (projected_occupancy(state) + units)


def can_safely_harvest(state: GameState, units: int, endgame: bool = False) -> bool:
    if units <= 0:
        return False
    # Carried goods drop into the shed at end of day; overflow is destroyed.
    proj = projected_occupancy(state) + units
    if proj <= state.shed_capacity:
        return True
    # Allow harvest if we will sell from shed this turn (room appears after DROP+SELL,
    # but harvest lands in worker inventory). Keep a small buffer unless liquidating.
    buffer = 0 if endgame else 4
    return state.shed_room() + state.carried_total() + buffer >= 0 and proj <= state.shed_capacity + (8 if endgame else 0)


def items_to_drop(worker_inv: dict[str, int]) -> list[tuple[str, int]]:
    return [(k, v) for k, v in worker_inv.items() if v > 0]

# === economy.py ===
"""Expected-value crop and animal economics given remaining time and prices."""




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
    units_per = 1.0 + (0.9 if care else 0.0)
    product_units = n_prod * units_per
    fert_units = max(0, remaining_days)
    feed_units = max(0, remaining_days)
    revenue = product_units * product_price + fert_units * min(fert_price, 80)
    cost = a["cost"] + wheat_feed_cost(wheat_price, feed_units)
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
            score += 8
        if not ev["can_plant"]:
            score = -1e9
        scored.append((score, crop))
    scored.sort(reverse=True)
    return scored[0][1] if scored else "WHEAT"


def pick_crop_for_tile(state: GameState, cfg: StrategyConfig, prices: dict[str, float], opp_counts: dict[str, int]) -> str:
    """Winning fill: melon spike, wheat cash, then strawberries on almost every tile."""
    remaining = state.remaining_days
    my_counts = state.me.crop_counts()
    if remaining <= 2:
        return "WHEAT"

    melon_price = float(prices.get("MELON", 250) or 0)
    berry_price = float(prices.get("STRAWBERRY", 120) or 0)

    if (
        state.day <= 2
        and my_counts.get("MELON", 0) < cfg.opening_melon_tiles
        and remaining >= CROPS["MELON"]["first_yield_day"]
        and melon_price >= cfg.melon_min_price
    ):
        return "MELON"

    if state.day <= 4 and my_counts.get("WHEAT", 0) < cfg.opening_wheat_tiles and remaining >= 3:
        return "WHEAT"

    if (
        remaining >= 12
        and melon_price >= cfg.melon_replant_min_price
        and my_counts.get("MELON", 0) < min(6, cfg.opening_melon_tiles)
        and opp_counts.get("MELON", 0) + my_counts.get("MELON", 0) < 12
    ):
        return "MELON"

    if remaining >= 8 and berry_price >= cfg.strawberry_min_price:
        return "STRAWBERRY"
    if remaining >= 3:
        return "CARROT"
    return "WHEAT"

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

# === opponent.py ===
"""Observable opponent features and coarse strategy class."""


from dataclasses import dataclass



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

extract_opp = extract

# === scheduler.py ===
"""Greedy worker-to-task assignment and movement."""


from dataclasses import dataclass, field


_HOLDER_OPS = {"PLACE", "BUILD_COOP", "BUILD_PASTURE"}


@dataclass
class Task:
    priority: float
    pos: tuple[int, int]
    action: list
    need_item: str | None = None
    key: str = ""
    once: bool = True


def assign(state: GameState, tasks: list[Task]) -> dict[int, list]:
    """Return farmer/hand action lists keyed by worker idx."""
    tasks = sorted(tasks, key=lambda t: -t.priority)
    reserved: set[str] = set()
    reserved_pos: set[tuple[int, int]] = set()
    busy: set[int] = set()
    actions: dict[int, list] = {w.idx: ["PASS"] for w in state.workers}
    tile_ops = {
        "WATER", "HARVEST", "PLANT", "FERTILIZE", "FEED", "CARE",
        "COLLECT_FERTILIZER", "BUILD_COOP", "BUILD_PASTURE", "DIG", "PLACE",
    }

    def holding_animal(w: Worker) -> bool:
        return any(w.inv_count(a) > 0 for a in ANIMALS)

    def can_do(w: Worker, t: Task) -> bool:
        if t.need_item and w.inv_count(t.need_item) <= 0:
            return False
        op = t.action[0] if t.action else "PASS"
        # DROP dumps the whole bag — never send a livestock carrier to dump produce.
        if holding_animal(w) and op not in _HOLDER_OPS:
            return False
        return True

    for t in tasks:
        tk = t.key or f"{t.action[0]}:{t.pos}:{id(t)}"
        if t.once and tk in reserved:
            continue
        op = t.action[0] if t.action else "PASS"
        if op in tile_ops and t.pos in reserved_pos:
            continue
        candidates = [w for w in state.workers if w.idx not in busy and can_do(w, t)]
        if not candidates:
            continue
        w = min(candidates, key=lambda ww: manhattan(ww.pos, t.pos))
        if w.pos == t.pos:
            actions[w.idx] = list(t.action)
        else:
            step = bfs_next_step(w.pos, t.pos, state.board_size)
            actions[w.idx] = [step] if step else ["PASS"]
        busy.add(w.idx)
        if t.once:
            reserved.add(tk)
        if op in tile_ops:
            reserved_pos.add(t.pos)

    return actions


def actions_to_output(state: GameState, by_idx: dict[int, list]) -> tuple[list, list]:
    farmer = by_idx.get(0, ["PASS"])
    hands = [by_idx.get(i + 1, ["PASS"]) for i in range(len(state.me.hands))]
    return farmer, hands

# === strategy.py ===
"""Winning-bot money engine: livestock opening, melon spike, strawberry fill, full expansion."""




def animal_targets(state: GameState, cfg: StrategyConfig) -> dict[str, int]:
    remaining = state.remaining_days
    owned = {a: state.animal_owned(a) for a in ANIMALS}
    if remaining < cfg.no_new_animals_days:
        return owned
    cows = cfg.opening_cows if remaining >= 10 else 0
    sheep = cfg.opening_sheep if remaining >= 10 else 0
    return {
        "COW": max(owned["COW"], cows),
        "SHEEP": max(owned["SHEEP"], sheep),
        "GOOSE": owned["GOOSE"],
    }


def hire_wanted(state: GameState, cfg: StrategyConfig) -> int:
    remaining = state.remaining_days
    n_quad = len(state.me.unlocked_quadrants)
    if remaining <= 0:
        return min(4, 1 + len(state.me.hands))
    if state.day == 0:
        return 1 + cfg.opening_hires
    if n_quad >= 4 or state.day >= 8:
        return cfg.target_hires
    if n_quad >= 2 or state.day >= 3:
        return max(10, cfg.target_hires - 2)
    return 8


def plants_allowed(n_workers: int, n_animals: int, cfg: StrategyConfig) -> int:
    # Water/feed first. 12 workers can hold ~60 tiles; overplanting kills berries.
    if n_workers >= 12:
        ppw = 6.0
    elif n_workers >= 8:
        ppw = 5.0
    else:
        ppw = 3.5
    return max(8, int(n_workers * ppw) - n_animals)


def _place_room(state: GameState, animal: str) -> int:
    kind = ANIMALS[animal]["structure"]
    built = sum(1 for s in state.me.empty_structures if s.kind == kind)
    return len(state.me.empty) + built


class CompetitiveAgent:
    def __init__(self, config: StrategyConfig | None = None):
        self.cfg = config or DEFAULT_CONFIG

    def act(self, obs, env_config=None) -> dict:
        state = parse_state(obs, env_config)
        opp = extract_opp(state)
        targets = animal_targets(state, self.cfg)
        market = self._market(state, opp, targets)
        tasks = self._tasks(state, opp, targets)
        by_idx = assign(state, tasks)
        farmer, hands = actions_to_output(state, by_idx)
        return {"farmer": farmer, "hands": hands, "market": market}

    def _market(self, state: GameState, opp, targets: dict[str, int]) -> list:
        cfg = self.cfg
        orders: list = []
        remaining = state.remaining_days
        money = state.money
        reserve = cfg.min_cash_reserve if remaining > cfg.liquidation_days else 0.0

        sells = [(item, n) for item, n in sale_plan(state, cfg) if n > 0]
        sell_slots = 1 if sells else 0

        # 1. Rehire the crew (hands reset every night). Max 4/turn so sell/feed still fit.
        hires_today = state.me.hires_today
        n_workers = 1 + len(state.me.hands)
        wanted = hire_wanted(state, cfg)
        hire_cap = min(cfg.max_hires_per_turn, MAX_MARKET_ORDERS - 3 - sell_slots)
        if state.day == 0:
            hire_cap = min(hire_cap, cfg.opening_hires)
        hire_budget = 0.0
        wprice = float(state.market_prices.get("WHEAT", 25) or 25)
        heads_now = state.livestock_heads()
        if state.day <= 1:
            heads_now = max(heads_now, cfg.opening_cows + cfg.opening_sheep)
        feed_cash_need = max(0, heads_now + cfg.wheat_feed_reserve - state.wheat_available_for_feed()) * wprice
        while n_workers < wanted and len(orders) < hire_cap:
            cost = hire_cost(hires_today)
            if money - cost < 0:
                break
            if n_workers >= 1 + cfg.opening_hires and money - cost < feed_cash_need:
                break
            if hire_budget + cost > cfg.max_daily_hire_cost and n_workers >= cfg.opening_hires:
                break
            orders.append(["HIRE"])
            money -= cost
            hire_budget += cost
            hires_today += 1
            n_workers += 1

        # 2. Sell harvest so later land/animals can use real next-turn cash.
        sold = set()
        for item, n in sells:
            if len(orders) >= MAX_MARKET_ORDERS - 3:
                break
            orders.append(["SELL", item, n])
            sold.add(item)

        # 3. Land like winning bots: day 6 / 9 / 10 when we have the coins.
        extra = len(state.me.unlocked_quadrants) - 1
        land_cost = LAND_PRICES[extra] if extra < 3 else 10**9
        packed = len(state.me.empty) <= cfg.land_unused_tile_trigger
        land_day = 6 if extra == 0 else 9 if extra == 1 else 10
        timed = extra < 3 and state.day >= land_day
        can_land = (
            extra < 3
            and state.day >= cfg.land_earliest_day
            and remaining >= cfg.land_min_remaining_days[min(extra, 2)]
            and remaining >= cfg.no_new_land_days
            and (packed or timed)
            and money >= land_cost + max(cfg.land_min_cash_after, feed_cash_need + 200)
            and (heads_now == 0 or state.wheat_available_for_feed() >= heads_now)
        )
        if can_land and len(orders) < MAX_MARKET_ORDERS:
            orders.append(["BUY_LAND"])
            money -= land_cost

        # 4. Wheat feed buffer (bought, not grown).
        heads = state.livestock_heads()
        if state.day <= 1:
            heads = max(heads, cfg.opening_cows + cfg.opening_sheep)
        wheat_want = heads + cfg.wheat_feed_reserve if heads else 0
        if state.day == 0:
            wheat_want = min(max(wheat_want, 6), 10)
        wheat_have = state.wheat_available_for_feed()
        sold_wheat = any(item == "WHEAT" for item, n in sells if n > 0)
        if wheat_want > wheat_have and not sold_wheat and len(orders) < MAX_MARKET_ORDERS:
            max_n = min(wheat_want - wheat_have, state.shed_room(), max(0, int(money // max(1, wprice))))
            if max_n > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", max_n])
                money -= wprice * max_n

        # 5. Animals with cash already in the bank. Never buy while heads sit in the shed.
        unplaced = sum(state.shed_count(a) + state.carried_count(a) for a in ANIMALS)
        if unplaced == 0 and remaining >= cfg.no_new_animals_days and money > reserve + 300:
            buy_plan = [("COW", cfg.max_cows_buy_per_turn), ("SHEEP", cfg.max_sheep_buy_per_turn), ("GOOSE", cfg.max_geese_buy_per_turn)]
            if state.day == 0:
                buy_plan = [("COW", cfg.opening_cows), ("SHEEP", 1)]
            for animal, cap in buy_plan:
                if cap <= 0 or len(orders) >= MAX_MARKET_ORDERS - 1:
                    break
                have = state.animal_owned(animal)
                need = targets.get(animal, 0) - have
                if need <= 0:
                    continue
                room = max(0, _place_room(state, animal))
                if room <= 0:
                    continue
                unit = ANIMALS[animal]["cost"]
                max_buy = min(need, cap, room, state.shed_room(), max(0, int((money - reserve) // unit)))
                if max_buy <= 0:
                    continue
                orders.append(["BUY_ANIMAL", animal, max_buy])
                money -= unit * max_buy

        # 6. Seeds: melon/wheat opening, then strawberries to fill.
        reserved_barns = max(0, sum(targets.values()) - sum(state.me.animal_counts().values()) - len(state.me.empty_structures))
        empty_n = max(0, len(state.me.empty) - reserved_barns)
        labor = plants_allowed(n_workers, sum(state.me.animal_counts().values()), cfg)
        room = max(0, labor - len(state.me.plants))
        plant_budget = min(empty_n, room)
        need: dict[str, int] = {}
        my = state.me.crop_counts()
        if remaining >= CROPS["MELON"]["first_yield_day"] and state.day <= 3:
            m = max(0, cfg.opening_melon_tiles - my.get("MELON", 0) - state.seed_count("MELON"))
            need["MELON"] = min(plant_budget, m)
            plant_budget -= need["MELON"]
        if remaining >= 3 and state.day <= 4:
            w = max(0, cfg.opening_wheat_tiles - my.get("WHEAT", 0) - state.seed_count("WHEAT"))
            need["WHEAT"] = min(plant_budget, w)
            plant_budget -= need["WHEAT"]
        crop = pick_crop_for_tile(state, cfg, state.market_prices, opp.crop_counts)
        if crop == "MELON" and my.get("MELON", 0) + state.seed_count("MELON") >= 12:
            crop = "STRAWBERRY" if remaining >= 8 else "WHEAT"
        if plant_budget > 0 and remaining >= CROPS[crop]["first_yield_day"]:
            need[crop] = need.get(crop, 0) + max(0, plant_budget - state.seed_count(crop))
        for c in ("MELON", "WHEAT", "STRAWBERRY", "CARROT", "TOMATO"):
            n = need.get(c, 0)
            if n <= 0 or len(orders) >= MAX_MARKET_ORDERS:
                continue
            cost_u = CROPS[c]["seed"]
            buy = min(n, max(0, int((money - reserve) // cost_u)))
            if buy > 0:
                orders.append(["BUY_SEED", c, buy])
                money -= cost_u * buy

        for item, n in sells:
            if item in sold or n <= 0 or len(orders) >= MAX_MARKET_ORDERS:
                continue
            orders.append(["SELL", item, n])

        return orders[:MAX_MARKET_ORDERS]

    def _tasks(self, state: GameState, opp, targets: dict[str, int]) -> list[Task]:
        cfg = self.cfg
        tasks: list[Task] = []
        remaining = state.remaining_days
        protected = protect_positions(state, cfg.protect_shed_tiles)
        shed_tiles = state.shed_tiles()
        liquidate = remaining <= cfg.liquidation_days
        unfed = [a for a in state.me.animals if not a.fed_today]

        keep_items = set(ANIMALS)
        if unfed:
            keep_items.add("WHEAT")
        for w in state.workers:
            if any(w.inv_count(a) > 0 for a in ANIMALS):
                continue
            if "WHEAT" in keep_items and w.inv_count("WHEAT") > 0:
                continue
            droppable = sum(n for item, n in w.inventory.items() if item not in keep_items and n > 0)
            if droppable <= 0:
                continue
            dest = nearest(w.pos, shed_tiles) or shed_tiles[0]
            pos = w.pos if w.pos in shed_tiles else dest
            pri = 942 if w.pos in shed_tiles else 725
            tasks.append(Task(pri, pos, ["DROP"], key=f"drop-{w.idx}"))

        for p in state.me.plants:
            if p.watered_today:
                continue
            if p.dies_tonight_if_unwatered():
                tasks.append(Task(1000, p.pos, ["WATER"], key=f"water-{p.pos}"))
            elif water_adds_yield(p, state.day):
                tasks.append(Task(900, p.pos, ["WATER"], key=f"water-{p.pos}"))
            else:
                tasks.append(Task(855, p.pos, ["WATER"], key=f"water-{p.pos}"))

        wheat_carried = state.carried_count("WHEAT")
        wheat_shed = state.shed_count("WHEAT")
        if len(unfed) > wheat_carried and wheat_shed > 0:
            remaining_need = len(unfed) - wheat_carried
            shed_left = wheat_shed
            for i, st in enumerate(shed_tiles):
                if remaining_need <= 0 or shed_left <= 0:
                    break
                n = min(6, remaining_need, shed_left)
                tasks.append(Task(1085, st, ["PICKUP", "WHEAT", n], key=f"pickup-wheat-{i}"))
                remaining_need -= n
                shed_left -= n
        if len(unfed) > wheat_carried + wheat_shed:
            broke = state.money < state.market_prices.get("WHEAT", 25)
            if broke or state.hour >= state.turns_per_day - 4:
                for p in state.me.plants:
                    if p.crop == "WHEAT" and p.yield_units > 0:
                        tasks.append(Task(1075, p.pos, ["HARVEST"], key=f"harv-feed-{p.pos}"))
        for a in unfed:
            pri = 1100 if a.dies_tonight_if_unfed() else 1060
            tasks.append(Task(pri, a.pos, ["FEED"], need_item="WHEAT", key=f"feed-{a.pos}"))

        empty_p = [s for s in state.me.empty_structures if s.kind == "PASTURE"]
        empty_c = [s for s in state.me.empty_structures if s.kind == "COOP"]
        empties = [p for p in state.me.empty if p not in protected]
        worker_pos = [w.pos for w in state.workers] or [(4, 4)]
        unplaced_p = state.shed_count("COW") + state.shed_count("SHEEP") + state.carried_count("COW") + state.carried_count("SHEEP")
        unplaced_g = state.shed_count("GOOSE") + state.carried_count("GOOSE")
        need_pasture_builds = min(len(empties), max(0, unplaced_p - len(empty_p)))
        need_coop_builds = min(max(0, len(empties) - need_pasture_builds), max(0, unplaced_g - len(empty_c)))
        build_tiles = sorted(empties, key=lambda p: min(manhattan(p, wp) for wp in worker_pos))
        bi = 0
        for _ in range(need_pasture_builds):
            if bi >= len(build_tiles):
                break
            pos = build_tiles[bi]
            bi += 1
            tasks.append(Task(955, pos, ["BUILD_PASTURE"], key=f"build-pasture-{pos}"))
        for _ in range(need_coop_builds):
            if bi >= len(build_tiles):
                break
            pos = build_tiles[bi]
            bi += 1
            tasks.append(Task(950, pos, ["BUILD_COOP"], key=f"build-coop-{pos}"))
        reserved_build = set(build_tiles[:bi])

        for w in state.workers:
            for animal in ("COW", "SHEEP", "GOOSE"):
                if w.inv_count(animal) <= 0:
                    continue
                kind = ANIMALS[animal]["structure"]
                slots = [s.pos for s in (empty_c if kind == "COOP" else empty_p)]
                if slots:
                    dest = nearest(w.pos, slots)
                    tasks.append(Task(970, dest, ["PLACE", animal], need_item=animal, key=f"place-{animal}-{dest}-{w.idx}"))
                elif empties:
                    dest = nearest(w.pos, list(reserved_build) or empties)
                    build = "BUILD_COOP" if kind == "COOP" else "BUILD_PASTURE"
                    tasks.append(Task(960, dest, [build], key=f"build-hold-{animal}-{dest}-{w.idx}"))

        pasture_slots = len(empty_p)
        n_cow = min(state.shed_count("COW"), pasture_slots)
        for i in range(n_cow):
            tasks.append(Task(930, shed_tiles[i % len(shed_tiles)], ["PICKUP", "COW", 1], key=f"pickup-COW-{i}"))
        n_sheep = min(state.shed_count("SHEEP"), max(0, pasture_slots - n_cow))
        for i in range(n_sheep):
            tasks.append(Task(928, shed_tiles[i % len(shed_tiles)], ["PICKUP", "SHEEP", 1], key=f"pickup-SHEEP-{i}"))
        for i in range(min(state.shed_count("GOOSE"), len(empty_c))):
            tasks.append(Task(926, shed_tiles[i % len(shed_tiles)], ["PICKUP", "GOOSE", 1], key=f"pickup-GOOSE-{i}"))
        if need_pasture_builds > 0 and (state.shed_count("COW") + state.shed_count("SHEEP")) > 0:
            animal = "COW" if state.shed_count("COW") > 0 else "SHEEP"
            tasks.append(Task(912, shed_tiles[0], ["PICKUP", animal, 1], key=f"pickup-ready-{animal}"))
        if need_coop_builds > 0 and state.shed_count("GOOSE") > 0:
            tasks.append(Task(908, shed_tiles[0], ["PICKUP", "GOOSE", 1], key="pickup-ready-goose"))

        room = state.shed_capacity - projected_occupancy(state)
        for p in state.me.plants:
            if not plant_ready_to_harvest(p, state.day):
                continue
            if decaying(p, state.step):
                tasks.append(Task(948, p.pos, ["HARVEST"], key=f"harv-{p.pos}"))
                continue
            if CROPS[p.crop]["ongoing"]:
                if p.yield_units > 0 and (p.yield_units >= 1 or liquidate or room > 6):
                    pri = 888 if p.crop == "STRAWBERRY" else 848
                    tasks.append(Task(pri, p.pos, ["HARVEST"], key=f"harv-{p.pos}"))
            else:
                waiting = one_time_should_wait(p, state.day) and remaining > 2
                if liquidate or not waiting:
                    if p.yield_units > 0:
                        pri = 912 if p.age(state.day) >= CROPS[p.crop]["max_yield_day"] else 882
                        tasks.append(Task(pri, p.pos, ["HARVEST"], key=f"harv-{p.pos}"))
        for a in state.me.animals:
            cap = ANIMALS[a.animal]["max_held"]
            if a.yield_units > 0 and (a.yield_units >= 1 or a.yield_units >= cap - 1 or liquidate):
                tasks.append(Task(886, a.pos, ["HARVEST"], key=f"aharv-{a.pos}"))

        # Care/fert every day for a small herd; after that only if labor is free.
        lots_empty = len(empties) > 10
        n_heads = len(state.me.animals)
        do_polish = n_heads <= 8 or not lots_empty
        if do_polish:
            for a in state.me.animals:
                if a.fertilizer_available:
                    tasks.append(Task(830, a.pos, ["COLLECT_FERTILIZER"], key=f"fert-{a.pos}"))
            for a in state.me.animals:
                if a.cared_today:
                    continue
                if (a.animal == "GOOSE" and cfg.care_geese) or (a.animal == "COW" and cfg.care_cows) or (a.animal == "SHEEP" and cfg.care_sheep):
                    tasks.append(Task(820, a.pos, ["CARE"], key=f"care-{a.pos}"))
            fert_shed = state.shed_count("FERTILIZER")
            if state.carried_count("FERTILIZER") == 0 and fert_shed > 0:
                tasks.append(Task(800, shed_tiles[0], ["PICKUP", "FERTILIZER", min(4, fert_shed)], key="pickup-fert"))
            for p in state.me.plants:
                if p.is_fertilized(state.day):
                    continue
                if (p.crop == "STRAWBERRY" and cfg.fertilize_strawberry) or (p.crop == "MELON" and cfg.fertilize_melon):
                    tasks.append(Task(790, p.pos, ["FERTILIZE"], need_item="FERTILIZER", key=f"fz-{p.pos}"))

        crop_choice = pick_crop_for_tile(state, cfg, state.market_prices, opp.crop_counts)
        n_workers = max(1, len(state.workers))
        labor = plants_allowed(n_workers, n_heads, cfg)
        room = max(0, labor - len(state.me.plants))
        turns_left = max(0, state.turns_per_day - state.hour)
        water_debt = sum(1 for p in state.me.plants if not p.watered_today)
        can_plant_n = min(room, len(empties), max(0, n_workers * turns_left - water_debt))
        plant_empties = [p for p in empties if p not in reserved_build]
        plant_empties = sorted(plant_empties, key=lambda p: min(manhattan(p, wp) for wp in worker_pos))
        seeds = dict(state.seeds)
        planted = 0
        for pos in plant_empties:
            if planted >= can_plant_n:
                break
            crop = crop_choice
            if state.day <= 2 and seeds.get("MELON", 0) > 0 and state.me.crop_counts().get("MELON", 0) < cfg.opening_melon_tiles:
                crop = "MELON"
            elif state.day <= 4 and seeds.get("WHEAT", 0) > 0 and state.me.crop_counts().get("WHEAT", 0) < cfg.opening_wheat_tiles:
                crop = "WHEAT"
            if seeds.get(crop, 0) <= 0:
                crop = next((c for c, n in seeds.items() if n > 0), None)
            if not crop:
                break
            if remaining < CROPS[crop]["first_yield_day"]:
                crop = "CARROT" if remaining >= 3 and seeds.get("CARROT", 0) > 0 else "WHEAT"
                if seeds.get(crop, 0) <= 0:
                    continue
            tasks.append(Task(870, pos, ["PLANT", crop], key=f"plant-{pos}"))
            seeds[crop] = seeds.get(crop, 0) - 1
            planted += 1

        if not state.me.empty and room > 0:
            for pos in state.me.weeds:
                tasks.append(Task(680, pos, ["DIG"], key=f"dig-{pos}"))
        for p in state.me.plants:
            if decaying(p, state.step) and p.yield_units <= 0:
                tasks.append(Task(898, p.pos, ["DIG"], key=f"digp-{p.pos}"))

        return tasks


def unused_after_expand_needed(state: GameState) -> bool:
    return len(state.me.empty) + len(state.me.weeds) <= 4


def agent_with_config(cfg: StrategyConfig):
    brain = CompetitiveAgent(cfg)

    def agent(obs, config=None):
        return brain.act(obs, config)

    return agent


_AGENT = CompetitiveAgent()


def agent(obs, config=None):
    try:
        return _AGENT.act(obs, config)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
