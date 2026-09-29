"""Ranch engine: price-forecast livestock + filler crops, value-per-distance worker matching.

Every purchase is scored by the money it returns before the game ends, using a
market forecast that counts our supply, the opponent's visible supply and town
demand. Nothing is tuned to one opponent; gluts lower scores automatically.
"""

from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    ANIMALS,
    CROPS,
    FRAGILE_PRODUCTS,
    LAND_PRICES,
    MARKET_PARAMS,
    MAX_MARKET_ORDERS,
    PRODUCTS,
    hire_cost,
    market_price,
)
from .farm import decaying, water_adds_yield
from .market import town_demand_per_day
from .movement import bfs_next_step, manhattan
from .state import GameState, Worker, parse_state

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
