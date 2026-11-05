"""Export the HARena paper results from harena-analysis into the website's JSON files.

The analysis repository holds the raw server, device and MCU runs, and its loaders
define the numbers in the paper. This script reuses those loaders, so the website
and the paper cannot disagree. Run it after the analysis data changes:

    cd ../harena-analysis
    PYTHONPATH=src uv run --no-sync python ../whar-arena/scripts/export_harena_results.py

Writes to apps/web/src/generated/:
    paper-benchmark.json   catalog plus test/validation macro-F1 per model, dataset, window
    deployment.json        phone, watch and MCU measurements per model, dataset, window
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
from harena.data import BENCHMARK_DATASETS, PAPER_WINDOWS, load_runs, load_splits
from harena.efficiency import model_dataset_table
from harena.names import dataset_label, model_label
from harena.paths import PROJECT_ROOT

GENERATED = Path(__file__).resolve().parents[1] / "apps" / "web" / "src" / "generated"
SEED = 0
REFERENCE_MODEL = "liteway_light"
PAPER_TITLE = "HARena"

MODEL_IDS: dict[str, str] = {
    "AttendDiscriminate": "attend_discriminate",
    "CNNHAR": "cnn_har",
    "DANA": "dana",
    "DeepConvLSTM": "deepconv_lstm",
    "DeepConvLSTMAttention": "deepconv_lstm_attention",
    "DeepConvLSTM_ISWC": "deepconv_lstm_iswc",
    "DynamicWHAR": "dynamic_whar",
    "KNN": "knn",
    "LITEWAY": "liteway",
    "LITEWAYLight": "liteway_light",
    "LSTMsEnsemble": "lstms_ensemble",
    "MLPHAR": "mlp_har",
    "MLPMixer": "mlp_mixer",
    "RandomForest": "random_forest",
    "SA_HAR": "sa_har",
    "SVM": "svm",
    "TinierHAR": "tinierhar",
    "TinyHAR": "tinyhar",
    "TripleCrossDomainAttention": "triple_cross_domain_attention",
}
# Models that were not in the previous catalog; the others keep their catalog entry.
NEW_MODELS: dict[str, dict[str, str]] = {
    "liteway": {
        "family": "attn_cnn",
        "framework": "torch",
        "package": "whar-models",
        "paper": "LITEWAY: LIghtweight HAR via Temporal Efficient highWAY",
    },
    "liteway_light": {
        "family": "attn_cnn",
        "framework": "torch",
        "package": "whar-models",
        "paper": "LITEWAY: LIghtweight HAR via Temporal Efficient highWAY",
    },
}


def number(value: Any, digits: int = 8) -> float | None:
    """Float, or None for missing values (JSON has no NaN). Keep enough digits: Pareto fronts
    compare values exactly, so coarse rounding creates ties that change a front."""
    if value is None or pd.isna(value) or math.isinf(float(value)):
        return None
    return round(float(value), digits)


def build_catalog(previous: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Keep existing entries and their order, which fixes the marker of each entity."""
    old_models = {m["id"]: m for m in previous["models"]}
    code_by_id = {v: k for k, v in MODEL_IDS.items()}
    model_ids = [m["id"] for m in previous["models"] if m["id"] in code_by_id]
    model_ids += [i for i in code_by_id if i not in model_ids]
    models = [
        {**(old_models.get(i) or NEW_MODELS[i]), "id": i, "name": model_label(code_by_id[i])}
        for i in model_ids
    ]
    old_datasets = [d["id"] for d in previous["datasets"] if d["id"] in BENCHMARK_DATASETS]
    dataset_ids = old_datasets + [d for d in BENCHMARK_DATASETS if d not in old_datasets]
    datasets = [
        {"id": d, "name": dataset_label(d), "package": "whar-datasets"} for d in dataset_ids
    ]
    return {"datasets": datasets, "models": models}


def build_results() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for window in PAPER_WINDOWS:
        runs = load_runs(window_s=window, seed=SEED)
        unknown = set(runs["model"]) - set(MODEL_IDS)
        if unknown:
            raise ValueError(f"Models without a website id: {sorted(unknown)}")
        for run in runs.sort_values(["model", "dataset"]).itertuples():
            results.append(
                {
                    "dataset_id": run.dataset,
                    "model_id": MODEL_IDS[run.model],
                    "split_id": "mean",
                    "status": "complete" if run.complete else "incomplete",
                    "window_size_seconds": window,
                    "metrics": {
                        "macro_f1": number(run.test_f1_mean),
                        "val_macro_f1": number(run.val_f1_mean),
                    },
                }
            )
    return results


def build_deployment() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in PAPER_WINDOWS:
        table = model_dataset_table(window_s=window)
        for row in table.itertuples():
            rows.append(
                {
                    "model_id": MODEL_IDS[row.model],
                    "dataset_id": row.dataset,
                    "window_size_seconds": window,
                    "phone_latency_ms": number(row.phone_lat_ms),
                    "phone_memory_mb": number(row.phone_mem_mb),
                    "phone_oom": bool(row.phone_oom) if pd.notna(row.phone_oom) else False,
                    "watch_latency_ms": number(row.watch_lat_ms),
                    "watch_memory_mb": number(row.watch_mem_mb),
                    "watch_oom": bool(row.watch_oom) if pd.notna(row.watch_oom) else False,
                    "mcu_status": row.mcu_status if isinstance(row.mcu_status, str) else None,
                    "mcu_latency_ms": number(row.mcu_lat_ms),
                    "mcu_ram_kb": number(row.mcu_ram_kb),
                    "mcu_flash_kb": number(row.mcu_flash_kb),
                    "mcu_energy_mj": number(row.mcu_energy_mj),
                }
            )
    return rows


def snapshot_date() -> str:
    """Date of the analysis commit the results come from."""
    return subprocess.run(
        ["git", "log", "-1", "--format=%ad", "--date=short"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def write(name: str, data: dict[str, Any]) -> None:
    (GENERATED / name).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    previous = json.loads((GENERATED / "paper-benchmark.json").read_text(encoding="utf-8"))
    date = snapshot_date()
    training_runs = sum(
        len(load_splits(window_s=window, seed=SEED)) for window in PAPER_WINDOWS
    )
    write(
        "paper-benchmark.json",
        {
            "source": {
                "kind": "harena_analysis_snapshot",
                "paper": PAPER_TITLE,
                "snapshot_date": date,
                "training_runs": training_runs,
                "notes": "Exported by scripts/export_harena_results.py from harena-analysis.",
            },
            "catalog": build_catalog(previous["catalog"]),
            "results": build_results(),
        },
    )
    write(
        "deployment.json",
        {
            "source": {
                "kind": "harena_analysis_snapshot",
                "snapshot_date": date,
                "reference_model": REFERENCE_MODEL,
                "devices": {
                    "phone": "Galaxy S24 Ultra",
                    "watch": "Galaxy Watch5 Pro",
                    "mcu": "nRF5340",
                },
            },
            "rows": build_deployment(),
        },
    )


if __name__ == "__main__":
    main()
