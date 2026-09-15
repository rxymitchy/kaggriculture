# Kaggriculture agent

Private competitive bot for the [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) Kaggle simulation.

Two players run 10×10 farms for 30 days (720 turns). Winner is who has the most **coins in the bank**. Unsold shed inventory is worth nothing.

**Current version: v4 profit-speed** (single-file `main.py` for Kaggle).

Repo: https://github.com/rxymitchy/kaggriculture (private)

## What it does

Each turn the agent:

1. Reads our farm, the opponent’s **visible** farm, market prices, and days left.
2. Places up to 10 market orders: hire workers, maybe buy land, buy the best-paying seeds, sell shed goods.
3. Lists farm jobs by urgency (don’t let plants die → harvest → plant → ignore busywork).
4. Sends the nearest free worker to each job, or walks toward it.

It is a greedy checklist, not a neural net. Kaggle gives **1 second** per action, so search/ML is not in this version.

## What’s different in v4

Older versions followed fixed habits (always wheat, always geese, always expand). Those lost money.

| Old habit (v1–v3) | v4 |
| --- | --- |
| Force ~6 wheat tiles | Wheat only if we have animals to feed |
| Buy geese early | **No geese** — they sat in the shed unused (~$2,400 dead) |
| Dig every weed / buy land when a bit full | Dig only if there is no empty tile; buy land only if the field is full **and** we have spare labor |
| Plant anything we can afford | Score crops from **live price × remaining days × worker actions** |
| Fertilize / care whenever possible | Skip those if harvest/water/plant is backed up |
| Protect the shed tile from planting | Use every unlocked tile |
| ~8 hires/day | ~10 hires/day; plant next to workers; only plant what we can water **today** |

Crop pick is price-aware: melon/strawberry only while their price is still high and the opponent is not already flooding that market. Late season it switches to fast crops (wheat/carrot) and sells everything.

### Local results vs Kaggle `starter` (4 games, seeds 1–4)

| Version | Win | Avg $ | Opp avg $ |
| --- | --- | --- | --- |
| v3 adaptive | 4–0 | 35,070 | 3,574 |
| **v4 profit-speed** | **4–0** | **38,939** | 3,454 |

v1 (first full game) scored **$6** — geese pickup/drop loop plus a cash floor that blocked replanting. That is fixed.

Kaggle leaderboard **600** is the default skill rating for a new bot, not farm money.

## How a turn is prioritized

Workers, highest first:

1. Water a plant that dies tonight / feed an animal that escapes tonight
2. Pick up wheat if animals still need feeding
3. Harvest decaying or ripe crops; drop produce at the shed (sell is a market order the same turn)
4. Plant the best-paying crop on empty tiles near workers
5. Routine watering
6. Dig weeds only if we need the tile

Market order order: **hire → land (rare) → seeds → emergency wheat → sell**.

## Layout

- `main.py` — **Kaggle submission**. One file, `def agent(obs, config=None)`. Bundled from `kag/`.
- `kag/` — source of truth: `state`, `economy`, `market`, `scheduler`, `strategy`, `config`
- `simulation.py` / `experiments.py` / `evaluation.py` — local matches
- `tests/` — mechanics + env parity (`kaggle-environments==1.32.7`)
- `scripts/bundle_main.py` — concatenates `kag/` into `main.py` (required: Kaggle `exec()`s the file, so `__file__` and package imports fail)
- `scripts/pack_submission.py` — rebuilds `main.py` and `submission.tar.gz`
- `NOTES_ENV.md` — spec vs installed interpreter
- `EXPERIMENTS.md` — version log

## Local test

Needs `kaggle-environments` (Kaggriculture env). On Windows, a full pip install can fail on long paths; `--no-deps` plus Flask/jsonschema/numpy/pydantic/gymnasium is enough.

```bash
python -m unittest tests.test_mechanics tests.test_env_parity
python experiments.py --games 4 --opp starter --us balanced --seed0 1
```

Full 720-turn smoke (uses bundled `main.py`, same as Kaggle load):

```bash
python -c "from kaggle_environments import make; env=make('kaggriculture', configuration={'episodeSteps':720,'seed':1}); env.run(['main.py','starter']); print([(s.status,s.reward) for s in env.steps[-1]])"
```

After editing `kag/`, rebuild the submission file:

```bash
python scripts/bundle_main.py
```

## Submit to Kaggle

Upload **`main.py` only** (not the old multi-file tar). Validation runs your bot against itself.

```bash
python scripts/pack_submission.py
# then upload Desktop/main.py or:
# kaggle competitions submit kaggriculture -f main.py -m "v4 profit-speed"
```

Join the competition on the website first. 5 submits/day; only the latest 2 count on the ladder.

## Env details that matter

The written Kaggle spec is close, but the **installed interpreter** wins when they differ. Highlights:

- Melon bonus window is ages 6–12 in code (`max_yield_day=12`); unfertilized cap is still 6 at age 10
- Shop names are `PIZZA_SHOP`, not `"Pizza Shop"`
- New plants start `consecutive_unwatered=1` — plant and skip water the same day → weed that night
- `FEED` / `FERTILIZE` use **worker inventory**; `SELL` uses the **shed**
- Locked tiles are walkable; first hire spawns on locked NE `(5,4)`
- `actTimeout` is 1 second

See `NOTES_ENV.md` for the full table.
