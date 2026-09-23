"""Winning-bot money engine: livestock opening, melon spike, strawberry fill, full expansion."""

from __future__ import annotations

from .config import DEFAULT_CONFIG, StrategyConfig
from .constants import (
    ANIMALS,
    CROPS,
    LAND_PRICES,
    MAX_MARKET_ORDERS,
    hire_cost,
)
from .economy import pick_crop_for_tile
from .farm import decaying, one_time_should_wait, plant_ready_to_harvest, protect_positions, water_adds_yield
from .inventory import projected_occupancy
from .market import sale_plan
from .movement import manhattan, nearest
from .opponent import extract as extract_opp
from .scheduler import Task, actions_to_output, assign
from .state import GameState, parse_state


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
