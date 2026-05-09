"""
Single-model benchmark runner for best1_int8_static_qdq.onnx.

This script is intentionally narrow: it benchmarks only the INT8 QDQ ONNX model
and writes a compact summary plus per-image details. It also tolerates the common
CSV/image naming mismatch by trying .jpg and .jpeg variants for each image.
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

MODELS_ROOT = Path(r"/home/syntech/yolo/paper_assets/models_new")
CSV_REFERENCE = Path(r"/home/syntech/yolo/paper_assets/results/per_image_results.csv")
IMAGES_DIR = Path(r"/home/syntech/yolo/val")
ANNOTATIONS_DIR = Path(r"/home/syntech/yolo/val_annotations")
OUTPUT_DIR = Path(r"/home/syntech/yolo/paper_assets/results/Results_new")

CHECKPOINT_FILE = OUTPUT_DIR / "_checkpoint_best1_int8_static_qdq.json"
LOG_FILE = OUTPUT_DIR / "best1_int8_static_qdq.log"

WARMUP = 3
TEMP_THRESHOLD_C = 70.0
TEMP_CRITICAL_C = 78.0
TEMP_COOLDOWN_TARGET = 55.0
TEMP_CHECK_INTERVAL = 5
COOLDOWN_BETWEEN_IMGS = 1.0
COOLDOWN_BETWEEN_BATCH = 15
BATCH_SIZE = 10
MIN_RAM_MB = 200
IMAGE_TIMEOUT_SEC = 120

MODEL_FILE_NAME = "best1_int8_static_qdq.onnx"
MODEL_INFERENCE_PARAMS = {
    "imgsz": 832,
    "conf": 0.15,
    "iou": 0.50,
}


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
    logger = logging.getLogger("best1_int8_static_qdq")
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
    log.warning("\n  ⚠ SHUTDOWN REQUESTED — finishing current image, saving checkpoint...")


import signal as sig
sig.signal(sig.SIGINT, _signal_handler)
sig.signal(sig.SIGTERM, _signal_handler)


def get_cpu_temp() -> float | None:
    try:
        thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
        if thermal_path.exists():
            return int(thermal_path.read_text().strip()) / 1000.0
    except Exception:
        pass
    return None


def thermal_guard(context: str = "") -> bool:
    global _shutdown_requested
    if _shutdown_requested:
        return False

    temp = get_cpu_temp()
    if temp is None:
        return True

    if temp >= TEMP_CRITICAL_C:
        log.warning(f"  🔴 CRITICAL TEMP: {temp:.1f}°C [{context}]. Cooling down to {TEMP_COOLDOWN_TARGET}°C...")
        while not _shutdown_requested:
            time.sleep(TEMP_CHECK_INTERVAL)
            t = get_cpu_temp()
            if t is None or t <= TEMP_COOLDOWN_TARGET:
                return True
        return False

    if temp >= TEMP_THRESHOLD_C:
        log.warning(f"  🟡 HIGH TEMP: {temp:.1f}°C [{context}]. Cooling down...")
        while not _shutdown_requested:
            time.sleep(TEMP_CHECK_INTERVAL)
            t = get_cpu_temp()
            if t is None or t <= TEMP_COOLDOWN_TARGET:
                break
    return not _shutdown_requested


def check_ram() -> tuple[bool, float]:
    avail_mb = psutil.virtual_memory().available / (1024 * 1024)
    return avail_mb >= MIN_RAM_MB, avail_mb


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            with CHECKPOINT_FILE.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            pass
    return {
        "completed_models": [],
        "in_progress_model": None,
        "in_progress_image_idx": 0,
        "in_progress_details": [],
        "summaries": [],
        "details": [],
    }


def save_checkpoint(checkpoint: dict) -> None:
    tmp = CHECKPOINT_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(checkpoint, handle, indent=2, default=str)
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
    tmp.rename(CHECKPOINT_FILE)


def find_model_path() -> Path:
    """Find the newest copy of the target ONNX model.

    The repository contains multiple edge-suite exports with the same filename.
    We select the most recently modified one so the script stays usable across
    different export batches without manual path edits.
    """
    candidates = sorted(MODELS_ROOT.rglob(MODEL_FILE_NAME), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"Could not find {MODEL_FILE_NAME} under {MODELS_ROOT}")
    return candidates[0]


def resolve_image_path(image_name: str) -> Path | None:
    """Resolve CSV image names against the local image folder.

    The Pi CSV commonly contains .jpg filenames, while this workspace also has
    .jpeg image copies. We try the exact name first, then swap the extension.
    """
    exact = IMAGES_DIR / image_name
    if exact.exists():
        return exact

    stem = Path(image_name).stem
    for ext in (".jpeg", ".jpg"):
        candidate = IMAGES_DIR / f"{stem}{ext}"
        if candidate.exists():
            return candidate

    return None


def load_ground_truth_count(image_name: str) -> int:
    """Load the colony count from the matching JSON annotation.

    The script supports the colony-count JSON schema used in this workspace:
    - colonies_number
    - annotations list fallback
    - objects list fallback
    """
    image_path = resolve_image_path(image_name)
    if image_path is None:
        raise FileNotFoundError(f"Missing image file for {image_name}")

    annotation_path = ANNOTATIONS_DIR / f"{image_path.stem}.json"
    if not annotation_path.exists():
        alt_path = image_path.with_suffix(".json")
        if alt_path.exists():
            annotation_path = alt_path
        else:
            raise FileNotFoundError(f"Missing annotation file for {image_name}")

    with annotation_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        if "colonies_number" in data:
            return int(data["colonies_number"])
        if isinstance(data.get("annotations"), list):
            return len(data["annotations"])
        if isinstance(data.get("objects"), list):
            return len(data["objects"])

    return 0


def load_dataset() -> list[dict[str, Any]]:
    if not CSV_REFERENCE.exists():
        raise FileNotFoundError(f"Missing reference CSV: {CSV_REFERENCE}")

    df = pd.read_csv(CSV_REFERENCE)
    if "image" not in df.columns:
        raise ValueError("Reference CSV must contain an 'image' column")

    unique_images = list(df["image"].dropna().unique())
    log.info(f"Found {len(unique_images)} unique images in {CSV_REFERENCE.name}")

    dataset: list[dict[str, Any]] = []
    missing = 0
    for image_name in unique_images:
        image_path = resolve_image_path(str(image_name))
        if image_path is None:
            log.warning(f"Missing image file: {image_name}")
            missing += 1
            continue

        try:
            gt_count = load_ground_truth_count(str(image_name))
            dataset.append(
                {
                    "image_name": str(image_name),
                    "image_path": str(image_path),
                    "gt_count": gt_count,
                }
            )
        except Exception as exc:
            log.warning(f"Could not load annotation for {image_name}: {exc}")
            missing += 1

    log.info(f"Loaded {len(dataset)} matching image/annotation pairs")
    if missing:
        log.warning(f"Missing files for {missing} images listed in CSV")

    return dataset


def locate_model_fallback(model_path: Path) -> Path | None:
    """Optional fallback for model-loading failures.

    This is only used if the ONNX file cannot be loaded directly. It keeps the
    script from failing hard when the export is present but the runtime backend
    is not compatible.
    """
    pt_candidates = [
        model_path.with_name("int8 (1).pt"),
        model_path.parent / "int8 (1).pt",
        Path(r"c:\Bacterial colony counter\rasp_test\int8 (1).pt"),
    ]
    for candidate in pt_candidates:
        if candidate.exists():
            return candidate
    return None


def load_model(model_path: Path):
    from ultralytics import YOLO

    try:
        return YOLO(str(model_path), task="detect"), "direct"
    except Exception as direct_err:
        fallback = locate_model_fallback(model_path)
        if fallback is None:
            raise direct_err

        log.warning(f"Direct ONNX load failed; falling back to {fallback.name}")
        return YOLO(str(fallback), task="detect"), f"fallback:{fallback.name}"


def benchmark_single_model(model_path: Path, dataset: list[dict[str, Any]]):
    global _shutdown_requested

    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)

    if not check_ram()[0] or not thermal_guard("pre-load"):
        raise RuntimeError("Insufficient RAM or thermal guard blocked startup")

    log.info(f"Loading {model_path.name}")
    start_load = time.perf_counter()
    model, load_mode = load_model(model_path)
    load_time_ms = (time.perf_counter() - start_load) * 1000.0
    log.info(f"Load mode: {load_mode}")
    log.info(
        f"Inference params: imgsz={MODEL_INFERENCE_PARAMS['imgsz']}, "
        f"conf={MODEL_INFERENCE_PARAMS['conf']}, iou={MODEL_INFERENCE_PARAMS['iou']}"
    )

    rows: list[BenchmarkRow] = []
    gt_values: list[int] = []
    pred_values: list[int] = []
    latencies: list[float] = []
    peak_ram_mb = mem_before
    checkpoint = load_checkpoint()
    start_idx = 0

    if checkpoint.get("in_progress_model") == model_path.name:
        start_idx = int(checkpoint.get("in_progress_image_idx", 0))
        rows = [BenchmarkRow(**row) for row in checkpoint.get("in_progress_details", [])]
        gt_values = [row.gt_count for row in rows]
        pred_values = [row.pred_count for row in rows]
        latencies = [row.latency_ms for row in rows]
        log.info(f"Resuming from image {start_idx}/{len(dataset)}")

    # Warmup keeps the first measured image from being skewed by graph/runtime init.
    if start_idx == 0:
        for sample in dataset[: min(WARMUP, len(dataset))]:
            try:
                model.predict(
                    sample["image_path"],
                    imgsz=MODEL_INFERENCE_PARAMS["imgsz"],
                    conf=MODEL_INFERENCE_PARAMS["conf"],
                    iou=MODEL_INFERENCE_PARAMS["iou"],
                    verbose=False,
                )
            except Exception:
                break

    for idx in range(start_idx, len(dataset)):
        sample = dataset[idx]

        if _shutdown_requested or not thermal_guard(f"img {idx + 1}"):
            checkpoint.update(
                {
                    "in_progress_model": model_path.name,
                    "in_progress_image_idx": idx,
                    "in_progress_details": [asdict(row) for row in rows],
                }
            )
            save_checkpoint(checkpoint)
            del model
            gc.collect()
            return None, []

        if idx > start_idx and idx % BATCH_SIZE == 0:
            log.info(f"Processed {idx}/{len(dataset)} images")
            time.sleep(COOLDOWN_BETWEEN_BATCH)

        start = time.perf_counter()
        results = model.predict(
            sample["image_path"],
            imgsz=MODEL_INFERENCE_PARAMS["imgsz"],
            conf=MODEL_INFERENCE_PARAMS["conf"],
            iou=MODEL_INFERENCE_PARAMS["iou"],
            verbose=False,
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        pred_count = int(len(results[0].boxes)) if results and len(results) > 0 else 0
        gt_count = int(sample["gt_count"])

        gt_values.append(gt_count)
        pred_values.append(pred_count)
        latencies.append(latency_ms)
        peak_ram_mb = max(peak_ram_mb, process.memory_info().rss / (1024 * 1024))

        rows.append(
            BenchmarkRow(
                model=model_path.name,
                image=sample["image_name"],
                gt_count=gt_count,
                pred_count=pred_count,
                error=pred_count - gt_count,
                abs_error=abs(pred_count - gt_count),
                latency_ms=latency_ms,
                ram_mb=peak_ram_mb,
            )
        )

        checkpoint.update(
            {
                "in_progress_model": model_path.name,
                "in_progress_image_idx": idx + 1,
                "in_progress_details": [asdict(row) for row in rows],
            }
        )
        save_checkpoint(checkpoint)

        time.sleep(COOLDOWN_BETWEEN_IMGS)

    y_true = np.array(gt_values)
    y_pred = np.array(pred_values)
    abs_err = np.abs(y_true - y_pred)
    sq_err = (y_true - y_pred) ** 2

    summary = {
        "model": model_path.name,
        "size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
        "load_mode": load_mode,
        "imgsz_used": MODEL_INFERENCE_PARAMS["imgsz"],
        "conf_used": MODEL_INFERENCE_PARAMS["conf"],
        "iou_used": MODEL_INFERENCE_PARAMS["iou"],
        "load_time_ms": load_time_ms,
        "samples": len(dataset),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mae_std": float(np.std(abs_err)),
        "mse": float(mean_squared_error(y_true, y_pred)),
        "mse_std": float(np.std(sq_err)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) >= 2 else None,
        "latency_avg_ms": float(np.mean(latencies)) if latencies else None,
        "latency_std_ms": float(np.std(latencies)) if latencies else None,
        "ram_delta_mb": max(0.0, peak_ram_mb - mem_before),
    }

    checkpoint.update(
        {
            "completed_models": sorted(set(checkpoint.get("completed_models", [])) | {model_path.name}),
            "in_progress_model": None,
            "in_progress_image_idx": 0,
            "in_progress_details": [],
        }
    )
    save_checkpoint(checkpoint)

    del model
    gc.collect()
    return summary, [asdict(row) for row in rows]


def main() -> None:
    log.info("Starting single-model benchmark for best1_int8_static_qdq.onnx")
    model_path = find_model_path()
    log.info(f"Using model: {model_path}")
    log.info(f"Checkpoint file: {CHECKPOINT_FILE}")
    log.info(f"Output directory: {OUTPUT_DIR}")

    dataset = load_dataset()
    if not dataset:
        raise RuntimeError("No usable images were loaded from the reference CSV")

    summary, rows = benchmark_single_model(model_path, dataset)

    summary_df = pd.DataFrame([summary])
    detail_df = pd.DataFrame(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "summary_best1_int8_static_qdq.csv"
    detail_path = OUTPUT_DIR / "per_image_best1_int8_static_qdq.csv"
    summary_df.to_csv(summary_path, index=False)
    detail_df.to_csv(detail_path, index=False)

    log.info("Benchmark complete")
    log.info(f"Summary saved to: {summary_path}")
    log.info(f"Per-image results saved to: {detail_path}")
    log.info(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()