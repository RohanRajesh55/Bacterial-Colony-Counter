"""
Benchmark only ONNX models on Raspberry Pi (strict ONNX-only execution).

This script runs inference for ONNX models only and never falls back to PT.
Each model is benchmarked with identical inference settings for fair comparison.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psutil
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ultralytics import YOLO

MODELS_ROOT = Path("/home/syntech/yolo/paper_assets/models_new")
CSV_REFERENCE = Path("/home/syntech/yolo/paper_assets/results/per_image_results.csv")
IMAGES_DIR = Path("/home/syntech/yolo/val")
ANNOTATIONS_DIR = Path("/home/syntech/yolo/val_annotations")
OUTPUT_DIR = Path("/home/syntech/yolo/paper_assets/results/Results_onnx_only")

CHECKPOINT_FILE = OUTPUT_DIR / "_checkpoint_onnx_models.json"
LOG_FILE = OUTPUT_DIR / "onnx_models_benchmark.log"

ONNX_MODELS = [
    "fp32.onnx",
    "fp16.onnx",
    "best1_int8_static_qdq.onnx",
    "best1_pruned_25.onnx",
    "sparsified_model.onnx",
]

INFER_PARAMS = {"imgsz": 832, "conf": 0.25, "iou": 0.50}
MAX_EVAL_IMAGES = 100

WARMUP = 3
TEMP_THRESHOLD_C = 70.0
TEMP_CRITICAL_C = 78.0
TEMP_COOLDOWN_TARGET = 60.0
TEMP_CHECK_INTERVAL = 5
COOLDOWN_BETWEEN_IMGS = 1.0
COOLDOWN_BETWEEN_BATCH = 15
BATCH_SIZE = 10
MIN_RAM_MB = 200


@dataclass
class BenchmarkRow:
    model: str
    image: str
    gt_count: int
    pred_count: int
    error: int
    abs_error: int
    latency_ms: float
    ram_mb: float


def setup_logging() -> logging.Logger:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("benchmark_onnx_models")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(stream)
        file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
    return logger


log = setup_logging()
_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    log.warning("Shutdown requested. Saving checkpoint.")


import signal as sig

sig.signal(sig.SIGINT, _signal_handler)
sig.signal(sig.SIGTERM, _signal_handler)


def get_cpu_temp() -> float | None:
    try:
        p = Path("/sys/class/thermal/thermal_zone0/temp")
        if p.exists():
            return int(p.read_text().strip()) / 1000.0
    except Exception:
        pass
    return None


def thermal_guard(context: str = "") -> bool:
    if _shutdown_requested:
        return False
    t = get_cpu_temp()
    if t is None:
        return True
    if t >= TEMP_CRITICAL_C:
        log.warning(f"Critical temp {t:.1f}C at {context}. Cooling down.")
        while not _shutdown_requested:
            time.sleep(TEMP_CHECK_INTERVAL)
            tt = get_cpu_temp()
            if tt is None or tt <= TEMP_COOLDOWN_TARGET:
                return True
        return False
    if t >= TEMP_THRESHOLD_C:
        log.warning(f"High temp {t:.1f}C at {context}. Cooling down.")
        while not _shutdown_requested:
            time.sleep(TEMP_CHECK_INTERVAL)
            tt = get_cpu_temp()
            if tt is None or tt <= TEMP_COOLDOWN_TARGET:
                break
    return not _shutdown_requested


def check_ram() -> tuple[bool, float]:
    avail = psutil.virtual_memory().available / (1024 * 1024)
    return avail >= MIN_RAM_MB, avail


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "completed_models": [],
        "in_progress_model": None,
        "in_progress_image_idx": 0,
        "in_progress_details": [],
    }


def save_checkpoint(state: dict) -> None:
    tmp = CHECKPOINT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
    tmp.rename(CHECKPOINT_FILE)


def find_model_path(name: str) -> Path | None:
    cands = sorted(MODELS_ROOT.rglob(name), key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None


def resolve_image_path(image_name: str) -> Path | None:
    exact = IMAGES_DIR / image_name
    if exact.exists():
        return exact
    stem = Path(image_name).stem
    for ext in (".jpg", ".jpeg"):
        c = IMAGES_DIR / f"{stem}{ext}"
        if c.exists():
            return c
    return None


def load_ground_truth_count(image_name: str) -> int:
    img = resolve_image_path(image_name)
    if img is None:
        raise FileNotFoundError(f"missing image: {image_name}")
    ann = ANNOTATIONS_DIR / f"{img.stem}.json"
    if not ann.exists():
        raise FileNotFoundError(f"missing annotation: {image_name}")
    data = json.loads(ann.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "colonies_number" in data:
            return int(data["colonies_number"])
        if isinstance(data.get("annotations"), list):
            return len(data["annotations"])
        if isinstance(data.get("objects"), list):
            return len(data["objects"])
    return 0


def load_dataset() -> list[dict[str, Any]]:
    df = pd.read_csv(CSV_REFERENCE)
    images = list(df["image"].dropna().unique())
    ds: list[dict[str, Any]] = []
    for img in images:
        p = resolve_image_path(str(img))
        if p is None:
            continue
        try:
            gt = load_ground_truth_count(str(img))
            ds.append({"image_name": str(img), "image_path": str(p), "gt_count": gt})
            if len(ds) >= MAX_EVAL_IMAGES:
                break
        except Exception:
            continue
    return ds


def benchmark_model(model_name: str, model_path: Path, dataset: list[dict[str, Any]]) -> tuple[dict, list[dict]]:
    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / (1024 * 1024)

    ram_ok, ram_mb = check_ram()
    if not ram_ok:
        raise RuntimeError(f"insufficient RAM: {ram_mb:.1f}MB")
    if not thermal_guard("pre-load"):
        raise RuntimeError("thermal guard blocked startup")

    start_load = time.perf_counter()
    model = YOLO(str(model_path), task="detect")
    load_time_ms = (time.perf_counter() - start_load) * 1000.0

    for sample in dataset[: min(WARMUP, len(dataset))]:
        try:
            model.predict(sample["image_path"], **INFER_PARAMS, verbose=False)
        except Exception:
            break

    rows: list[BenchmarkRow] = []
    y_true: list[int] = []
    y_pred: list[int] = []
    lat: list[float] = []
    peak_ram = mem_before

    state = load_checkpoint()
    start_idx = 0
    if state.get("in_progress_model") == model_name:
        start_idx = int(state.get("in_progress_image_idx", 0))
        rows = [BenchmarkRow(**r) for r in state.get("in_progress_details", [])]
        y_true = [r.gt_count for r in rows]
        y_pred = [r.pred_count for r in rows]
        lat = [r.latency_ms for r in rows]

    for i in range(start_idx, len(dataset)):
        s = dataset[i]
        if _shutdown_requested or not thermal_guard(f"img {i+1}"):
            state.update(
                {
                    "in_progress_model": model_name,
                    "in_progress_image_idx": i,
                    "in_progress_details": [asdict(r) for r in rows],
                }
            )
            save_checkpoint(state)
            del model
            gc.collect()
            return None, []

        if i > start_idx and i % BATCH_SIZE == 0:
            time.sleep(COOLDOWN_BETWEEN_BATCH)

        t0 = time.perf_counter()
        res = model.predict(s["image_path"], **INFER_PARAMS, verbose=False)
        t_ms = (time.perf_counter() - t0) * 1000.0
        pred = int(len(res[0].boxes)) if res and len(res) > 0 else 0
        gt = int(s["gt_count"])
        pred = max(0, pred)

        y_true.append(gt)
        y_pred.append(pred)
        lat.append(t_ms)
        peak_ram = max(peak_ram, proc.memory_info().rss / (1024 * 1024))

        log.info(f"[{model_name}] {i + 1}/{len(dataset)}")

        rows.append(
            BenchmarkRow(
                model=model_name,
                image=s["image_name"],
                gt_count=gt,
                pred_count=pred,
                error=pred - gt,
                abs_error=abs(pred - gt),
                latency_ms=t_ms,
                ram_mb=peak_ram,
            )
        )

        state.update(
            {
                "in_progress_model": model_name,
                "in_progress_image_idx": i + 1,
                "in_progress_details": [asdict(r) for r in rows],
            }
        )
        save_checkpoint(state)
        time.sleep(COOLDOWN_BETWEEN_IMGS)

    yt = np.array(y_true)
    yp = np.array(y_pred)
    ae = np.abs(yt - yp)
    se = (yt - yp) ** 2

    summary = {
        "model": model_name,
        "model_file_used": model_path.name,
        "size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
        "load_mode": "direct-onnx",
        "status": "success",
        "imgsz_used": INFER_PARAMS["imgsz"],
        "conf_used": INFER_PARAMS["conf"],
        "iou_used": INFER_PARAMS["iou"],
        "load_time_ms": load_time_ms,
        "samples": len(dataset),
        "mae": float(mean_absolute_error(yt, yp)),
        "mae_std": float(np.std(ae)),
        "mse": float(mean_squared_error(yt, yp)),
        "mse_std": float(np.std(se)),
        "rmse": float(np.sqrt(mean_squared_error(yt, yp))),
        "r2": float(r2_score(yt, yp)) if len(yt) >= 2 else None,
        "latency_avg_ms": float(np.mean(lat)),
        "latency_std_ms": float(np.std(lat)),
        "ram_delta_mb": max(0.0, peak_ram - mem_before),
        "error": "",
    }

    state.update(
        {
            "completed_models": sorted(set(state.get("completed_models", [])) | {model_name}),
            "in_progress_model": None,
            "in_progress_image_idx": 0,
            "in_progress_details": [],
        }
    )
    save_checkpoint(state)

    del model
    gc.collect()
    return summary, [asdict(r) for r in rows]


def main() -> None:
    log.info("ONNX-only benchmark starting")
    dataset = load_dataset()
    if not dataset:
        raise RuntimeError("No dataset samples loaded")

    if len(dataset) < MAX_EVAL_IMAGES:
        log.warning(
            f"Only {len(dataset)} valid annotated images found; requested {MAX_EVAL_IMAGES}."
        )
    else:
        log.info(f"Using the same {len(dataset)} images for every ONNX model.")

    summaries: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    for name in ONNX_MODELS:
        log.info(f"\n--- TESTING {name} ---")
        p = find_model_path(name)
        if p is None:
            summaries.append(
                {
                    "model": name,
                    "model_file_used": None,
                    "size_mb": None,
                    "load_mode": "missing",
                    "status": "failed",
                    "samples": len(dataset),
                    "error": "ONNX file not found",
                }
            )
            continue

        try:
            s, rows = benchmark_model(name, p, dataset)
            if s is None:
                log.info("Interrupted. Resume by re-running script.")
                return
            summaries.append(s)
            details.extend(rows)
        except Exception as e:
            summaries.append(
                {
                    "model": name,
                    "model_file_used": p.name,
                    "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
                    "load_mode": "runtime-error",
                    "status": "failed",
                    "samples": len(dataset),
                    "error": str(e),
                }
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summaries).to_csv(OUTPUT_DIR / "summary_onnx_models.csv", index=False)
    pd.DataFrame(details).to_csv(OUTPUT_DIR / "per_image_onnx_models.csv", index=False)
    log.info("ONNX-only benchmark complete")


if __name__ == "__main__":
    main()
