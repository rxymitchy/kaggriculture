# Kaggriculture agent

Private competitive bot for the [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) Kaggle simulation.

Two players run 10×10 farms for 30 days (720 turns). Winner is who has the most **coins in the bank**. Unsold shed inventory is worth nothing.

**Current version: v6-cash-first** (single-file `main.py` for Kaggle).

Repo: https://github.com/rxymitchy/kaggriculture (private)

## What it does

Each turn the agent:

1. Reads our farm, the opponent’s **visible** farm, market prices, and days left.
2. Places up to 10 market orders: hire, sell, land (only if packed), maybe cows later, seeds.
3. Lists farm jobs by urgency (don’t let plants die → harvest wheat/carrot for cash → plant).
4. Sends the nearest free worker to each job, or walks toward it.

It is a greedy checklist, not a neural net. Kaggle gives **1 second** per action.

## What’s different in v6-cash-first

v5-win-meta copied the ~$100k replay playbook (cows+sheep day 1, melon, then strawberries everywhere). Locally vs `starter` it printed **$77k**. On Kaggle (23 games) it went **11–12**, avg **$52.6k vs $54.9k**, because it was **broke through day 8** (~$78 in the bank vs opponents ~$746) and tried to catch up with a late berry spike.

That was overfitting. v6 throws the script out:

- **Days 0–7:** wheat + carrot (pay in 2–4 days). Keep ~$2.2k–$3.8k in the bank. No livestock dump, no 60 strawberries.
- **Land:** only when the current field is packed, leftover ≥ $800, not before day 8.
- **Animals:** none until the field is busy again and we still have ≥ $2k. Never the same turn as land.
- **Crops:** live price × days left × opponent glut — not a melon→berry checklist.
- **Labor cap:** plant only what we can water. Replays had ~37 thirsty plants; that is a burned $100 seed.

### Local vs Kaggle `starter` (4 games, seeds 1–4)

| Version | Win | Avg $ | Day-8 cash (seed 1) |
| --- | --- | --- | --- |
| v4 profit-speed | 4–0 | 38,939 | — |
| v5-win-meta (Kaggle 11–12) | 4–0 | 76,722 | **$78** in real games |
| **v6-cash-first** | **4–0** | **33,784** | **$3,379–$3,824** |

Final $ vs starter is lower on purpose. The old $77k was a day-12 berry dump that only works against a weak opponent. Against real bots we were already behind $4k by day 20. v6 is built to **not fall in a hole** early.

Kaggle leaderboard **600** is default skill, not coins.

## How a turn is prioritized

Workers, highest first:

1. Water a plant that dies tonight
2. Harvest wheat/carrot once they pay (don’t wait if we need cash)
3. Plant the live-EV crop next to workers
4. Feed / place animals only if we actually own some
5. Care, fertilizer, weeds if labor is free

Market: **hire → sell → land (packed only) → feed wheat → animals → seeds**. Never drain the bank below operating cash.

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
# kaggle competitions submit kaggriculture -f main.py -m "v6-cash-first"
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
