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
    """Items currently in the shed that we should sell this turn."""
    remaining = state.remaining_days
    n_animals = sum(state.me.animal_counts().values())
    wheat_keep = (n_animals + cfg.wheat_feed_reserve) if cfg.keep_wheat_for_feed else 0
    if remaining <= cfg.liquidation_days:
        wheat_keep = 0

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
            # Keep some for high-value crops unless price is good or endgame.
            keep = 0
            if remaining > cfg.endgame_days and price < cfg.sell_fertilizer_if_price_ge:
                keep = min(have, 4)
            sell = have - keep
            if sell > 0:
                orders.append((item, sell))
            continue
        if item in FRAGILE_PRODUCTS:
            if remaining <= cfg.liquidation_days or price >= cfg.sell_fragile_if_price_ge:
                n = min(have, cfg.max_sell_units_fragile if remaining > cfg.liquidation_days else have)
                if n > 0:
                    orders.append((item, n))
            elif price <= 2 and remaining > 3:
                # Hold a little if floor; town may lift it. Don't hold forever.
                if have > 6:
                    orders.append((item, have - 6))
            else:
                orders.append((item, min(have, max(1, have // 2))))
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

    def can_do(w: Worker, t: Task) -> bool:
        if t.need_item and w.inv_count(t.need_item) <= 0:
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
"""High-level competitive policy: survival, production, market, opponent, endgame."""




class CompetitiveAgent:
    def __init__(self, config: StrategyConfig | None = None):
        self.cfg = config or DEFAULT_CONFIG

    def act(self, obs, env_config=None) -> dict:
        state = parse_state(obs, env_config)
        opp = extract_opp(state)
        market = self._market(state, opp)
        tasks = self._tasks(state, opp)
        by_idx = assign(state, tasks)
        farmer, hands = actions_to_output(state, by_idx)
        return {"farmer": farmer, "hands": hands, "market": market}

    def _market(self, state: GameState, opp) -> list:
        cfg = self.cfg
        orders: list = []
        remaining = state.remaining_days
        money = state.money
        reserve = cfg.min_cash_reserve
        if remaining <= cfg.liquidation_days:
            reserve = 0

        # 1. Hire first (hands appear immediately and can act this turn).
        hires_today = state.me.hires_today
        n_workers = 1 + len(state.me.hands)
        wanted = cfg.target_hires
        if remaining <= 1:
            wanted = min(wanted, 4)
        n_jobs = len(state.me.plants) + len(state.me.animals) + len(state.me.empty) + len(state.me.weeds)
        if n_jobs > n_workers * cfg.hire_if_tasks_per_worker:
            wanted = max(wanted, min(12, n_jobs // 2))
        hire_budget = 0.0
        while (
            n_workers < wanted
            and len(orders) < cfg.max_hires_per_turn
            and len(orders) < MAX_MARKET_ORDERS - 2
        ):
            cost = hire_cost(hires_today)
            if money - cost < max(reserve, 80):
                break
            if hire_budget + cost > cfg.max_daily_hire_cost and n_workers >= 4:
                break
            orders.append(["HIRE"])
            money -= cost
            hire_budget += cost
            hires_today += 1
            n_workers += 1

        # 2. Land only if we already use current tiles AND labor can cover more.
        extra = len(state.me.unlocked_quadrants) - 1
        n_busy_tiles = len(state.me.plants) + len(state.me.animals) + len(state.me.empty_structures)
        unlocked_tiles = n_busy_tiles + len(state.me.empty) + len(state.me.weeds)
        labor_cap = max(8, int(n_workers * cfg.plants_per_worker))
        if (
            extra < 3
            and state.day >= cfg.land_earliest_day
            and remaining >= cfg.land_min_remaining_days[min(extra, 2)]
            and remaining >= cfg.no_new_land_days
            and len(state.me.empty) <= cfg.land_unused_tile_trigger
            and n_busy_tiles >= max(12, unlocked_tiles - 3)
            and labor_cap > unlocked_tiles + 8
        ):
            cost = LAND_PRICES[extra]
            if money - cost >= cfg.land_min_cash_after and len(orders) < MAX_MARKET_ORDERS:
                orders.append(["BUY_LAND"])
                money -= cost

        # 3. Animals (geese) only after a wheat pipeline exists.
        n_geese = state.me.animal_counts().get("GOOSE", 0) + state.shed_count("GOOSE") + state.carried_count("GOOSE")
        wheat_plants = state.me.crop_counts().get("WHEAT", 0)
        wheat_stock = state.shed_count("WHEAT") + state.carried_count("WHEAT")
        goose_ready = (
            state.day >= cfg.goose_earliest_day
            and (wheat_plants >= cfg.goose_min_wheat_plants or wheat_stock >= 4)
        )
        if (
            goose_ready
            and remaining >= cfg.goose_min_remaining_days
            and remaining >= cfg.no_new_animals_days
            and n_geese < cfg.max_geese
            and state.market_prices.get("EGG", 50) >= cfg.goose_min_egg_price
            and len(orders) < MAX_MARKET_ORDERS
        ):
            ev = animal_net_value(
                "GOOSE",
                state.market_prices.get("EGG", 50),
                state.market_prices.get("WHEAT", 25),
                state.market_prices.get("FERTILIZER", 100),
                remaining,
                cfg.care_geese,
            )
            empty_slots = len(state.me.empty) + sum(1 for s in state.me.empty_structures if s.kind == "COOP")
            if ev["can_buy"] and money - 300 >= max(reserve, 50) and empty_slots >= 1:
                n_buy = min(cfg.max_geese_buy_per_turn, cfg.max_geese - n_geese, max(1, empty_slots))
                if money - 300 * n_buy >= reserve and state.shed_room() > n_buy:
                    orders.append(["BUY_ANIMAL", "GOOSE", n_buy])
                    money -= 300 * n_buy

        # 4. Seeds for the best-paying crop only, limited to what we can plant/water.
        crop = pick_crop_for_tile(state, cfg, state.market_prices, opp.crop_counts)
        labor_cap = max(6, int(n_workers * cfg.plants_per_worker))
        room = max(0, labor_cap - len(state.me.plants) - len(state.me.animals))
        empty_n = len([p for p in state.me.empty if p not in protect_positions(state, cfg.protect_shed_tiles)])
        turns_left = max(1, state.turns_per_day - state.hour)
        water_debt = sum(1 for p in state.me.plants if not p.watered_today)
        plant_budget = min(empty_n, room, n_workers, max(0, (n_workers * turns_left - water_debt) // 2))
        need = {c: 0 for c in CROPS}
        wheat_have = state.me.crop_counts().get("WHEAT", 0)
        n_animals = sum(state.me.animal_counts().values())
        wheat_target = int(cfg.wheat_tiles_per_animal * n_animals) if n_animals else cfg.min_wheat_tiles
        if wheat_target and wheat_have < wheat_target and remaining >= 3:
            need["WHEAT"] = min(plant_budget, wheat_target - wheat_have)
            plant_budget -= need["WHEAT"]
        if plant_budget > 0:
            need[crop] += plant_budget
        for c, n in need.items():
            have = state.seed_count(c)
            buy = n - have
            floor = max(40, int(reserve * 0.5))
            if buy > 0 and len(orders) < MAX_MARKET_ORDERS:
                cost_u = CROPS[c]["seed"]
                max_buy = max(0, int((money - floor) // cost_u))
                buy = min(buy, max_buy)
                if buy > 0:
                    cost = cost_u * buy
                    orders.append(["BUY_SEED", c, buy])
                    money -= cost

        # 5. Emergency wheat buy for feed if we would lose animals.
        critical_feed = sum(1 for a in state.me.animals if a.dies_tonight_if_unfed() and not a.fed_today)
        wheat_now = state.wheat_available_for_feed()
        if critical_feed > wheat_now and len(orders) < MAX_MARKET_ORDERS:
            buy_n = critical_feed - wheat_now
            # BUY_PRODUCT wheat goes to shed; workers still need to PICKUP.
            wprice = state.market_prices.get("WHEAT", 25)
            if money - wprice * buy_n >= 0 and state.shed_room() >= buy_n:
                orders.append(["BUY_PRODUCT", "WHEAT", buy_n])
                money -= wprice * buy_n

        # 6. Sell shed goods (after buys so we don't sell wheat we need).
        for item, n in sale_plan(state, cfg):
            if len(orders) >= MAX_MARKET_ORDERS:
                break
            if n > 0:
                orders.append(["SELL", item, n])

        return orders[:MAX_MARKET_ORDERS]

    def _tasks(self, state: GameState, opp) -> list[Task]:
        cfg = self.cfg
        tasks: list[Task] = []
        remaining = state.remaining_days
        protected = protect_positions(state, cfg.protect_shed_tiles)
        shed_tiles = state.shed_tiles()
        endgame = remaining <= cfg.endgame_days
        liquidate = remaining <= cfg.liquidation_days

        # --- inventory dump: harvest products only (never dump live animals / feed) ---
        keep_items = set(ANIMALS)
        if any(not a.fed_today for a in state.me.animals):
            keep_items.add("WHEAT")
        for w in state.workers:
            droppable = sum(n for item, n in w.inventory.items() if item not in keep_items and n > 0)
            if droppable <= 0:
                continue
            dest = nearest(w.pos, shed_tiles) or shed_tiles[0]
            pos = w.pos if w.pos in shed_tiles else dest
            pri = 940 if w.pos in shed_tiles else 710
            tasks.append(Task(pri, pos, ["DROP"], key=f"drop-{w.idx}"))

        # --- survival watering ---
        for p in state.me.plants:
            if p.watered_today:
                continue
            if p.dies_tonight_if_unwatered():
                tasks.append(Task(1000, p.pos, ["WATER"], key=f"water-{p.pos}"))
            elif water_adds_yield(p, state.day):
                tasks.append(Task(900, p.pos, ["WATER"], key=f"water-{p.pos}"))
            elif in_bonus_window(p, state.day) or True:
                # Ongoing crops still need daily water for survival and doubled fert yield.
                tasks.append(Task(860, p.pos, ["WATER"], key=f"water-{p.pos}"))

        # --- feed: pickup wheat then feed ---
        unfed = [a for a in state.me.animals if not a.fed_today]
        wheat_carried = state.carried_count("WHEAT")
        wheat_shed = state.shed_count("WHEAT")
        need_feed = len(unfed)
        if need_feed > wheat_carried and wheat_shed > 0:
            remaining_need = need_feed - wheat_carried
            shed_left = wheat_shed
            for i, st in enumerate(shed_tiles):
                if remaining_need <= 0 or shed_left <= 0:
                    break
                n = min(3, remaining_need, shed_left)
                tasks.append(Task(980, st, ["PICKUP", "WHEAT", n], key=f"pickup-wheat-{i}"))
                remaining_need -= n
                shed_left -= n

        for a in unfed:
            pri = 990 if a.dies_tonight_if_unfed() else 870
            tasks.append(Task(pri, a.pos, ["FEED"], need_item="WHEAT", key=f"feed-{a.pos}"))

        # --- harvest ---
        room = state.shed_capacity - projected_occupancy(state)
        for p in state.me.plants:
            if not plant_ready_to_harvest(p, state.day):
                continue
            if decaying(p, state.step):
                tasks.append(Task(950, p.pos, ["HARVEST"], key=f"harv-{p.pos}"))
                continue
            if CROPS[p.crop]["ongoing"]:
                if p.yield_units > 0 and (p.yield_units >= 2 or liquidate or room > 8):
                    tasks.append(Task(840, p.pos, ["HARVEST"], key=f"harv-{p.pos}"))
            else:
                waiting = one_time_should_wait(p, state.day) and remaining > 2
                if liquidate or not waiting:
                    if p.yield_units > 0:
                        pri = 910 if p.age(state.day) >= CROPS[p.crop]["max_yield_day"] else 880
                        tasks.append(Task(pri, p.pos, ["HARVEST"], key=f"harv-{p.pos}"))

        for a in state.me.animals:
            cap = ANIMALS[a.animal]["max_held"]
            if a.yield_units > 0 and (a.yield_units >= 2 or a.yield_units >= cap - 1 or liquidate):
                tasks.append(Task(845, a.pos, ["HARVEST"], key=f"aharv-{a.pos}"))

        busy_core = (
            sum(1 for p in state.me.plants if not p.watered_today)
            + sum(1 for p in state.me.plants if plant_ready_to_harvest(p, state.day) and not one_time_should_wait(p, state.day))
            + min(len(state.me.empty), 8)
        )
        spare_labor = busy_core < len(state.workers)

        # --- fertilizer collect ---
        if spare_labor:
            for a in state.me.animals:
                if a.fertilizer_available:
                    tasks.append(Task(820, a.pos, ["COLLECT_FERTILIZER"], key=f"fert-{a.pos}"))

        # --- care ---
        if spare_labor:
            for a in state.me.animals:
                if a.cared_today:
                    continue
                if a.animal == "GOOSE" and cfg.care_geese:
                    tasks.append(Task(780, a.pos, ["CARE"], key=f"care-{a.pos}"))
                elif a.animal == "COW" and cfg.care_cows:
                    tasks.append(Task(760, a.pos, ["CARE"], key=f"care-{a.pos}"))
                elif a.animal == "SHEEP" and cfg.care_sheep:
                    tasks.append(Task(760, a.pos, ["CARE"], key=f"care-{a.pos}"))

        # --- fertilize high-value plants ---
        if spare_labor:
            fert_carried = state.carried_count("FERTILIZER")
            fert_shed = state.shed_count("FERTILIZER")
            if fert_carried == 0 and fert_shed > 0:
                tasks.append(Task(770, shed_tiles[0], ["PICKUP", "FERTILIZER", min(3, fert_shed)], key="pickup-fert"))
            for p in state.me.plants:
                if p.is_fertilized(state.day):
                    continue
                want = (
                    (p.crop == "STRAWBERRY" and cfg.fertilize_strawberry)
                    or (p.crop == "TOMATO" and cfg.fertilize_tomato)
                    or (p.crop == "MELON" and cfg.fertilize_melon)
                )
                if want:
                    tasks.append(Task(750, p.pos, ["FERTILIZE"], need_item="FERTILIZER", key=f"fz-{p.pos}"))

        # --- place animals / build only if we actually intend to run livestock ---
        geese_shed = state.shed_count("GOOSE")
        empty_coops = [s for s in state.me.empty_structures if s.kind == "COOP"]
        if cfg.max_geese > 0 or geese_shed > 0 or any(w.inv_count("GOOSE") > 0 for w in state.workers):
            for w in state.workers:
                if w.inv_count("GOOSE") > 0:
                    if empty_coops:
                        dest = nearest(w.pos, [s.pos for s in empty_coops])
                        tasks.append(Task(935, dest, ["PLACE", "GOOSE"], key=f"place-goose-{dest}"))
                    else:
                        empties = [p for p in state.me.empty if p not in protected]
                        if empties:
                            dest = nearest(w.pos, empties)
                            tasks.append(Task(900, dest, ["BUILD_COOP"], key=f"build-coop-{dest}"))
            if geese_shed > 0 and empty_coops:
                n_pick = min(len(empty_coops), geese_shed, 4)
                for i, st in enumerate(shed_tiles[:n_pick]):
                    tasks.append(Task(820, st, ["PICKUP", "GOOSE", 1], key=f"pickup-goose-{i}"))
            elif geese_shed > 0 and remaining >= cfg.no_new_animals_days:
                empties = [p for p in state.me.empty if p not in protected]
                if empties:
                    tasks.append(Task(800, empties[0], ["BUILD_COOP"], key=f"build-coop-{empties[0]}"))
                elif state.me.weeds:
                    tasks.append(Task(790, state.me.weeds[0], ["DIG"], key=f"dig-for-coop-{state.me.weeds[0]}"))

        # --- plant what pays, only as many as we can water today ---
        crop_choice = pick_crop_for_tile(state, cfg, state.market_prices, opp.crop_counts)
        labor_cap = max(6, int((1 + len(state.me.hands)) * cfg.plants_per_worker))
        room = max(0, labor_cap - len(state.me.plants) - len(state.me.animals))
        turns_left = max(0, state.turns_per_day - state.hour)
        water_debt = sum(1 for p in state.me.plants if not p.watered_today)
        can_plant_n = min(
            room,
            max(0, (len(state.workers) * turns_left - water_debt) // 2),
        )
        worker_pos = [w.pos for w in state.workers]
        empties = [p for p in state.me.empty if p not in protected]
        empties = sorted(empties, key=lambda p: min(manhattan(p, wp) for wp in worker_pos))
        seeds = dict(state.seeds)
        planted = 0
        n_animals = sum(state.me.animal_counts().values())
        wheat_target = int(cfg.wheat_tiles_per_animal * n_animals) if n_animals else cfg.min_wheat_tiles
        for pos in empties:
            if planted >= can_plant_n:
                break
            crop = crop_choice
            wheat_have = state.me.crop_counts().get("WHEAT", 0)
            if wheat_target and wheat_have < wheat_target and seeds.get("WHEAT", 0) > 0:
                crop = "WHEAT"
            if seeds.get(crop, 0) <= 0:
                crop = next((c for c, n in seeds.items() if n > 0), None)
            if not crop:
                break
            if remaining < CROPS[crop]["first_yield_day"]:
                continue
            tasks.append(Task(885, pos, ["PLANT", crop], key=f"plant-{pos}"))
            seeds[crop] = seeds.get(crop, 0) - 1
            planted += 1

        # --- dig weeds only if we have no empty tile left and still have plant room ---
        if not state.me.empty and room > 0:
            for pos in state.me.weeds:
                tasks.append(Task(680, pos, ["DIG"], key=f"dig-{pos}"))

        # --- decaying leftover plants occupying land ---
        for p in state.me.plants:
            if decaying(p, state.step) and p.yield_units <= 0:
                tasks.append(Task(900, p.pos, ["DIG"], key=f"digp-{p.pos}"))

        return tasks


def unused_after_expand_needed(state: GameState) -> bool:
    unused = len(state.me.empty) + len(state.me.weeds)
    return unused <= 4


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
