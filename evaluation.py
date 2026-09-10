"""Aggregate metrics over many episodes."""

from __future__ import annotations


def summarize(results: list[dict], us_index: int = 0) -> dict:
    n = len(results)
    wins = sum(1 for r in results if r["winner"] == us_index)
    losses = sum(1 for r in results if r["winner"] == 1 - us_index)
    ties = sum(1 for r in results if r["winner"] is None)
    our = [r["rewards"][us_index] for r in results]
    opp = [r["rewards"][1 - us_index] for r in results]
    diffs = [a - b for a, b in zip(our, opp)]
    statuses = [r["statuses"][us_index] for r in results]
    errors = sum(1 for s in statuses if s not in ("DONE", "ACTIVE"))
    return {
        "games": n,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / n if n else 0,
        "avg_money": sum(our) / n if n else 0,
        "avg_opp_money": sum(opp) / n if n else 0,
        "avg_diff": sum(diffs) / n if n else 0,
        "min_money": min(our) if our else 0,
        "max_money": max(our) if our else 0,
        "errors": errors,
        "avg_elapsed": sum(r["elapsed"] for r in results) / n if n else 0,
    }


def format_summary(name: str, s: dict) -> str:
    return (
        f"{name}: games={s['games']} W/L/T={s['wins']}/{s['losses']}/{s['ties']} "
        f"win_rate={s['win_rate']:.2%} avg${s['avg_money']:.0f} vs ${s['avg_opp_money']:.0f} "
        f"diff={s['avg_diff']:.0f} errors={s['errors']} t={s['avg_elapsed']:.1f}s"
    )
