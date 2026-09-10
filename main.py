"""Kaggle submission entry. Must expose agent(obs) at module top level."""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kag.strategy import CompetitiveAgent

_AGENT = CompetitiveAgent()


def agent(obs, config=None):
    return _AGENT.act(obs, config)

