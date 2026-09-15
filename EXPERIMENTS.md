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
