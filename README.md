# Kaggriculture agent

Competitive Python agent for the [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) simulation.

## Layout

- `main.py` — Kaggle entry (`agent(obs, config=None)`)
- `kag/` — state, economy, market, scheduler, strategy
- `simulation.py` / `experiments.py` / `evaluation.py` — local eval
- `tests/` — unit tests against the installed environment
- `scripts/pack_submission.py` — builds `submission.tar.gz`

## Local test

```bash
python -m unittest tests.test_mechanics tests.test_env_parity
python experiments.py --games 4 --opp starter --us balanced --seed0 1
```

Full 720-turn smoke:

```bash
python -c "from kaggle_environments import make; from main import agent; env=make('kaggriculture', configuration={'episodeSteps':720,'seed':1}, debug=True); env.run([agent,'starter']); print([(s.status,s.reward) for s in env.steps[-1]])"
```

## Submit

```bash
python scripts/pack_submission.py
kaggle competitions submit kaggriculture -f submission.tar.gz -m "v3 adaptive"
```

You must accept competition rules on Kaggle before submitting.
