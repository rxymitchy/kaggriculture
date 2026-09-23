# Experiment log

## Env

- `kaggle-environments==1.32.7`
- Full games: 720 steps, `seed` in configuration

## Spec vs code

See `NOTES_ENV.md`. Most important: melon `max_yield_day=12` in code, `actTimeout=1s`, shop names underscored, FEED/FERTILIZE from worker inventory, SELL from shed.

## v0 — API validation

- Installed env, parsed observation (`player, step, farms, private, market, town`).
- Smoke: 48-step and 720-step episodes complete with status DONE.

## v1 — first 720-turn agent (broken)

- Hired, bought 8 geese immediately, pickup/DROP looped animals, cash reserve blocked replanting.
- Result vs starter seed 1: **$6 vs $4725** (loss).

## v2 — crop engine + cash floor

- Delay geese, never DROP live animals, seed buys ignore hard reserve, harvest/sell wheat & melon.
- vs pass seed 1: **$28578 vs $3000** (win) then **$30041** after land delay.

## v3 — current `balanced` (main.py)

Changes: operating cash floor ~$150, land after day 4 with $900 leftover, geese only with wheat pipeline and empty tiles, seed spend capped.

| Matchup | Games | Seeds | W/L/T | Avg $ | Opp avg $ |
| --- | --- | --- | --- | --- | --- |
| vs starter | 4 | 1–4 | 4/0/0 | 35070 | 3574 |
| vs pass | 1 | 1 | 1/0/0 | 30041 | 3000 |

### Failure modes still open

- Geese often remain in the shed (farm too full to BUILD_COOP).
- Over-planting vs worker count on some days (`uw` spikes if broke).
- Fragile melon/strawberry sales not staggered vs a strong opponent.
- No search/rollouts yet (`actTimeout=1s`).

## v4 — profit/speed (current)

Dropped fixed wheat/goose/land habits. Plant the crop with the best live profit, hire more, skip weeds/land we cannot use, skip geese (they were dead capital).

| Matchup | Games | Seeds | W/L/T | Avg $ | Opp avg $ |
| --- | --- | --- | --- | --- | --- |
| vs starter v3 | 4 | 1–4 | 4/0/0 | 35070 | 3574 |
| vs starter v4 | 4 | 1–4 | 4/0/0 | **38939** | 3454 |

Keep. Faster games (~10s vs ~15s) and ~$4k more vs starter.

## v5 — livestock-meta (current)

First pass copied the winning replay too hard (20 animals, strawberries everywhere) and **lost money** (~$8.5k vs starter). That was a bug, not the meta.

Current v5 is the **v4 crop engine** plus 2 cows, bought wheat feed, and an opening melon batch. Same “only plant what we can water / only buy land when packed” rules.

| Matchup | Games | Seeds | W/L/T | Avg $ | Opp avg $ |
| --- | --- | --- | --- | --- | --- |
| vs starter v4 | 4 | 1–4 | 4/0/0 | 38939 | 3454 |
| vs starter v5 | 4 | 1–4 | 4/0/0 | **38995** | 3615 |

Keep. Same 4–0, slightly more cash. Next real jump is a bigger herd that we can actually feed.

## v5-win-meta (current)

Winning-bot money engine: 2 cows + 3 sheep opening, bought wheat, melon spike, strawberry fill, land on days 6/9/10, rehire 10–12 every morning. Feed is higher priority than water so the herd doesn’t starve. Do not buy extra animals that sit in the shed.

| Matchup | Games | Seeds | W/L/T | Avg $ | Opp avg $ |
| --- | --- | --- | --- | --- | --- |
| vs starter v5 livestock-meta | 4 | 1–4 | 4/0/0 | 38995 | 3615 |
| vs starter v5-win-meta | 4 | 1–4 | 4/0/0 | **76722** | 3612 |

Keep. ~2× coins. Per-seed: 78478, 66865, 80011, 81533. Same hockey-stick as ~$100k replay bots (broke until berries, then a spike). Remaining gap is late berry deaths and unused tiles.

## Kaggle audit (23 replays, Mitchell Luciana)

11–12, avg **$52,572 vs $54,865**. Day-8 cash **$78 vs opponent $746**. ~37 thirsty plants. Bought 7,234 wheat as feed. Opponents grew wheat and sold milk/fert. The $77k vs starter did not transfer.

## v6-cash-first (current)

Throw out the winning-bot script. Wheat/carrot for early coins, packed land only after day 8 with leftover cash, no livestock dump, live-EV crops, tight labor cap.

| Matchup | Games | Seeds | W/L/T | Avg $ | Day-8 cash |
| --- | --- | --- | --- | --- | --- |
| vs starter v5-win-meta | 4 | 1–4 | 4/0/0 | 76722 | ~$78 on Kaggle |
| vs starter v6-cash-first | 4 | 1–4 | 4/0/0 | **33784** | **$3379–$3824** |

Keep for Kaggle: the hole is closed. Final $ vs starter is lower because we stopped the berry dump that only beat `starter`.
