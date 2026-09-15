"""Build a single-file main.py so Kaggle exec() loading cannot fail on imports."""

from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAG = os.path.join(ROOT, "kag")
OUT = os.path.join(ROOT, "main.py")

ORDER = [
    "constants.py",
    "config.py",
    "movement.py",
    "state.py",
    "farm.py",
    "inventory.py",
    "economy.py",
    "market.py",
    "opponent.py",
    "scheduler.py",
    "strategy.py",
]

REL_IMPORT = re.compile(
    r"^from \.[\w.]+ import \([^)]*\)\s*|^from \.[\w.]+ import .+\n",
    re.M,
)
FUTURE = re.compile(r"^from __future__ import .+\n", re.M)


def strip_module(src: str) -> str:
    src = FUTURE.sub("", src)
    src = REL_IMPORT.sub("", src)
    return src.strip() + "\n\n"


HEADER = '''\
"""Kaggriculture Kaggle agent. Single-file so exec() loading works without __file__ or packages."""
from __future__ import annotations

'''

FOOTER = '''
_AGENT = CompetitiveAgent()


def agent(obs, config=None):
    try:
        return _AGENT.act(obs, config)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
'''


def main():
    parts = [HEADER]
    for name in ORDER:
        path = os.path.join(KAG, name)
        with open(path, encoding="utf-8") as f:
            body = strip_module(f.read())
        parts.append(f"# === {name} ===\n")
        parts.append(body)
        if name == "opponent.py":
            parts.append("extract_opp = extract\n\n")
    parts.append(FOOTER)
    text = "".join(parts)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"wrote {OUT} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
