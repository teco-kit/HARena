# HARena

HARena is a Git-native benchmark and [website](https://teco-kit.github.io/whar-arena/) for wearable human activity
recognition. The arena has one official protocol, discovers datasets from
[`whar-datasets`](https://github.com/teco-kit/whar-datasets), discovers models
from [`whar-models`](https://github.com/teco-kit/whar-models), plans the full
benchmark matrix, and renders committed result files as a static website.

## Core Idea

- Official protocol
- All benchmark datasets from [`whar-datasets`](https://github.com/teco-kit/whar-datasets)
- All registered models from [`whar-models`](https://github.com/teco-kit/whar-models)
- Benchmark matrix

Every planned run receives a deterministic fingerprint. If a matching result
already exists, the run is skipped. When a dataset or model is added upstream,
the planner detects the new matrix entries automatically.

## Updating the Published Results

The website shows the paper snapshot from `harena-analysis`. After its data changes, regenerate
`paper-benchmark.json` and `deployment.json` in `apps/web/src/generated/`:

```bash
cd ../harena-analysis
PYTHONPATH=src uv run --no-sync python ../whar-arena/scripts/export_harena_results.py
```

## Quick Start

```bash
uv sync --all-extras
uv pip install -e ../whar-datasets -e ../whar-models
uv run whar-arena catalog
uv run whar-arena plan --limit 10
uv run whar-arena export-site-data

cd apps/web
npm install
npm run dev
```
