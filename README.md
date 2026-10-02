# Kaggriculture agent

A competitive bot for the [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) Kaggle simulation.

Two players run 10×10 farms for 30 days (720 turns). Winner is who has the most **coins in the bank**. Unsold shed inventory is worth nothing.

**Current version: v7-ranch** (single-file `main.py` for Kaggle).

Repo: https://github.com/rxymitchy/kaggriculture 

## What it does

Each turn the agent:

1. Reads our farm, the opponent's **visible** farm, market prices, and days left.
2. Builds a **price forecast** for every product: our output, the opponent's output (measured from how the market stock moved yesterday), what the town eats, and stock we still hold.
3. Scores each possible buy (goose, cow, sheep, land, melon, wheat/carrot) by the money it returns before the game ends — including how much a new head lowers the price for the heads we already own.
4. Lists farm jobs with a value (feed, care, collect fertilizer, harvest, water, plant, build, place) and matches workers to jobs by **value minus walking distance**, with a bonus for finishing the tile a worker is standing on.

It is a forecast + greedy planner, not a neural net. A turn takes ~3 ms (max ~40 ms); Kaggle allows 1 second.

## Why v7 (41 Kaggle replays of v6)

v6-cash-first went 22–19 on Kaggle but made little money: one land purchase, ~35 plants, **no animals**, 37k idle worker turns and 7.6k walks to the shed. The top opponents made their money from animals (fertilizer, milk, eggs, wool) and staged land.

What the installed rules say (and v6 ignored):

- Every animal gives **1 fertilizer per day** from the first night; a goose pays back its $300 in ~2–3 days.
- **Feed + care** on the same day adds +1 unit on the next production night: goose ~2 eggs/day, cow ~3 milk per 2 days.
- Carried items **drop into the shed automatically at night** — mid-day shed trips are wasted unless the shed would overflow or it's the last day.
- Selling is **per unit**, each unit lowers the price. Eggs, wheat and fertilizer hold price well; milk, wool and strawberries crash after ~60–75 extra units.

v7 is built on those rules, not on copying one bot.

## Local results (opponent pool, both seats)

`starter` alone is too weak to judge a bot (v5 beat it by $77k and still went 11–12 on Kaggle). v7 is tested against a pool: `starter`, our old v4/v5/v6 (pulled from git), and a **mirror match** (v7 vs v7 on a shared market).

| Version | Wins (no mirror) | Avg $ | Mirror avg $ |
| --- | --- | --- | --- |
| v6-cash-first (seeds 1–3) | 8/24 | 24,561 | 24,396 |
| **v7-ranch (seeds 1–3)** | **24/24** | **83,766** | **61,741** |
| **v7-ranch (held-out seeds 7–10)** | **32/32** | **88,123** | **63,170** |

Held-out seeds were never used while building v7.

## Layout

- `main.py` — **Kaggle submission**. One file, `def agent(obs, config=None)`. Bundled from `kag/`.
- `kag/ranch.py` — v7 brain: forecast (`Outlook`), tile plan, jobs, worker matching, market orders
- `kag/` — shared helpers: `constants`, `state`, `farm`, `market`, `movement` (older `strategy.py` = v6)
- `scripts/pool_eval.py` — pool evaluation: `python scripts/pool_eval.py [main.py|ranch:k=v+k=v] [n_seeds] [opps] [first_seed]`
- `scripts/trace_ranch.py` / `scripts/probe_ranch.py` — one-game daily trace / planner internals
- `scripts/audit_my_replays.py`, `scripts/study_top_opps.py` — Kaggle replay audits
- `scripts/bundle_main.py` — concatenates `kag/` into `main.py` (Kaggle `exec()`s the file, so `__file__` and package imports fail)
- `tests/` — mechanics + env parity (`kaggle-environments==1.32.7`)
- `EXPERIMENTS.md` — version log

## Local test

```bash
python -m unittest tests.test_mechanics tests.test_env_parity
python scripts/pool_eval.py main.py 3 "starter,v4,v5,v6,self"
```

After editing `kag/`, rebuild the submission file:

```bash
python scripts/bundle_main.py
```

## Submit to Kaggle

Upload **`main.py` only**. Validation runs your bot against itself.

```bash
# kaggle competitions submit kaggriculture -f main.py -m "v7-ranch"
```

5 submits/day; only the latest 2 count on the ladder.

## Env details that matter

The installed interpreter wins when it differs from the written spec:

- New plants start `consecutive_unwatered=1` — plant and skip water the same day → weed that night
- Animals produce their base unit even unfed; 2 unfed days in a row → the animal escapes
- `FEED` / `FERTILIZE` use **worker inventory**; `SELL` uses the **shed**; unit actions run before market orders in the same turn
- Shed cap 100: overflow at the nightly drop is destroyed
- Fertilizer has no town demand — it only goes down as both players sell it
- Locked tiles are walkable; hands spawn on shed-access tiles
- `actTimeout` is 1 second

See `NOTES_ENV.md` for the full table.
