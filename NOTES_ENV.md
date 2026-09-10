# Installed environment vs written spec (kaggle-environments 1.32.7)

Authoritative source: `kaggle_environments/envs/kaggriculture/kaggriculture.py`.

| Topic | Spec / docs | Installed implementation | Agent uses |
| --- | --- | --- | --- |
| Melon time-to-max in object table | 10 days | `max_yield_day = 12` (bonus window 6–12); yield still capped at 6, unfertilized cap reached at age 10 | code |
| Tomato / strawberry `max_yield_day` | last production age 11 / 16 | stored as first production day (8 / 10); 4 scheduled yields via interval | code |
| Shop names | "Pizza Shop" | `PIZZA_SHOP`, `BRUNCH_SPOT`, … | underscores |
| Empty coop/pasture | `animal: None` | key omitted (`"animal" not in tile`) | both |
| `actTimeout` | not emphasized | **1 second** | cheap greedy policy |
| Town consume | every 4 / 24 turns | also fires when `step % interval == 0` including step 0 | env |
| Fertilizer duration | 3 days | `fertilized_until_day = day + 2` (inclusive) | env |
| Sell at $1 | floor | unit bought but **not** added to market inventory | env |
| BUY_PRODUCT quote | — | priced at `inventory - 1` | env |
| Over-planting | none planted if demand > seeds | **all** PLANT ops for that crop become PASS that turn | avoid |
| FEED / FERTILIZE | — | items must be in **worker inventory**, not shed | pickup first |
| SELL | — | from **shed only** | DROP then SELL same turn works |
| Hire spawn | NWSE shed tiles | first hire `(5,4)` (locked NE until bought) | locked is passable |

Other mechanics (consecutive_unwatered starts at 1, animals at 0, I0=10000, land 1k/2k/4k, fib hiring, shed 100, 10 market orders, concurrent per-unit market) match the written spec.
