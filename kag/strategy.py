"""High-level competitive policy: survival, production, market, opponent, endgame."""

from __future__ import annotations

from .config import DEFAULT_CONFIG, StrategyConfig
from .constants import (
    ANIMALS,
    CROPS,
    LAND_PRICES,
    MAX_MARKET_ORDERS,
    hire_cost,
)
from .economy import animal_net_value, pick_crop_for_tile
from .farm import decaying, in_bonus_window, one_time_should_wait, plant_ready_to_harvest, protect_positions, water_adds_yield
from .inventory import projected_occupancy
from .market import sale_plan
from .movement import manhattan, nearest
from .opponent import extract as extract_opp
from .scheduler import Task, actions_to_output, assign
from .state import GameState, parse_state


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

        # 2. Land as an investment.
        extra = len(state.me.unlocked_quadrants) - 1
        if (
            extra < 3
            and state.day >= cfg.land_earliest_day
            and remaining >= cfg.land_min_remaining_days[min(extra, 2)]
            and remaining >= cfg.no_new_land_days
            and unused_after_expand_needed(state)
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

        # 4. Seeds for planned plantings.
        crop = pick_crop_for_tile(state, cfg, state.market_prices, opp.crop_counts)
        empty_n = len([p for p in state.me.empty if p not in protect_positions(state, cfg.protect_shed_tiles)])
        plant_budget = min(empty_n, max(1, n_workers))
        need = {c: 0 for c in CROPS}
        # Ensure wheat seeds if we are wheat-short.
        wheat_have = state.me.crop_counts().get("WHEAT", 0)
        wheat_target = max(cfg.min_wheat_tiles, int(cfg.wheat_tiles_per_animal * max(1, sum(state.me.animal_counts().values()))))
        if wheat_have < wheat_target and remaining >= 3:
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

        # --- fertilizer collect ---
        for a in state.me.animals:
            if a.fertilizer_available:
                tasks.append(Task(820, a.pos, ["COLLECT_FERTILIZER"], key=f"fert-{a.pos}"))

        # --- care ---
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

        # --- place animals / build: pickup only when a free coop exists ---
        geese_shed = state.shed_count("GOOSE")
        empty_coops = [s for s in state.me.empty_structures if s.kind == "COOP"]
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

        # --- plant ---
        crop_choice = pick_crop_for_tile(state, cfg, state.market_prices, opp.crop_counts)
        empties = [p for p in state.me.empty if p not in protected]
        # Prefer tiles closer to current workers / shed to reduce walking.
        empties = sorted(empties, key=lambda p: manhattan(p, state.me.farmer))
        seeds = dict(state.seeds)
        for pos in empties:
            crop = crop_choice
            # Force wheat if below target.
            wheat_have = state.me.crop_counts().get("WHEAT", 0)
            wheat_target = max(cfg.min_wheat_tiles, int(cfg.wheat_tiles_per_animal * max(1, sum(state.me.animal_counts().values()))))
            if wheat_have < wheat_target and seeds.get("WHEAT", 0) > 0:
                crop = "WHEAT"
            if seeds.get(crop, 0) <= 0:
                # fallback any seed
                crop = next((c for c, n in seeds.items() if n > 0), None)
            if not crop:
                break
            if remaining < CROPS[crop]["first_yield_day"]:
                continue
            tasks.append(Task(720, pos, ["PLANT", crop], key=f"plant-{pos}"))
            seeds[crop] = seeds.get(crop, 0) - 1

        # --- dig weeds ---
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
