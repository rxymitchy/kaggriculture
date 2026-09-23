# Kaggriculture agent

Private competitive bot for the [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) Kaggle simulation.

Two players run 10×10 farms for 30 days (720 turns). Winner is who has the most **coins in the bank**. Unsold shed inventory is worth nothing.

**Current version: v5-win-meta** (single-file `main.py` for Kaggle).

Repo: https://github.com/rxymitchy/kaggriculture (private)

## What it does

Each turn the agent:

1. Reads our farm, the opponent’s **visible** farm, market prices, and days left.
2. Places up to 10 market orders: hire, animals, wheat feed, seeds, land, sell.
3. Lists farm jobs by urgency (feed first → don’t let plants die → harvest berries → plant).
4. Sends the nearest free worker to each job, or walks toward it.

It is a greedy checklist, not a neural net. Kaggle gives **1 second** per action.

## What’s different in v5-win-meta

Same playbook as the ~$100k winning Kaggle bots, with logistics that actually keep the farm alive:

- **Opening:** 2 cows + 3 sheep, bought wheat, ~10 melon + wheat on the starting land, 4 hires
- **Fill:** strawberries on most tiles once the opening is down (no 8% berry cap)
- **Crew:** rehire 10–12 workers every morning (hands reset at night), max 4 hires per turn
- **Land:** days 6 / 9 / 10 when we have the coins
- **Feed before water** so the herd doesn’t starve while the berry field is thirsty
- **Sell everything** except wheat for the animals we own

The old v5 only added 2 cows on top of the wheat/carrot engine (~$39k). This one runs the winning money engine.

### Local results vs Kaggle `starter` (4 games, seeds 1–4)

| Version | Win | Avg $ | Opp avg $ |
| --- | --- | --- | --- |
| v3 adaptive | 4–0 | 35,070 | 3,574 |
| v4 profit-speed | 4–0 | 38,939 | 3,454 |
| v5 livestock-meta (2 cows + old crops) | 4–0 | 38,995 | 3,615 |
| **v5-win-meta** | **4–0** | **76,722** | 3,612 |

Seeds: $78.5k, $66.9k, $80.0k, $81.5k. About **2×** the previous bot. Top replay bots still print ~$96k–$119k, so there is room, but this is the same shape of game (broke until berries, then a hockey-stick).

Kaggle leaderboard **600** is the default skill rating for a new bot, not farm money.

## How a turn is prioritized

Workers, highest first:

1. Feed animals / pick up wheat (before watering)
2. Water a plant that dies tonight
3. Place animals still in the shed
4. Harvest ripe berries / melon; drop produce at the shed
5. Plant strawberries (melon/wheat only in the opening)
6. Care, fertilizer, weeds if labor is free

Market order: **hire → sell → land → wheat feed → animals → seeds**.

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
# kaggle competitions submit kaggriculture -f main.py -m "v5-win-meta"
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
