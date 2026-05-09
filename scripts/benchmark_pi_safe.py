"""
Pi-Safe Model Benchmark Script v2 (Hardened)
==============================================
Evaluates YOLOv8 model variants (.pt, .onnx) on 100 bacterial colony images
with MAXIMUM thermal/hardware protection for Raspberry Pi.

Safety Features:
  1. Thermal Watchdog     — Checks temp EVERY image; pauses at 70°C, waits to 55°C
  2. Throttle Detection   — Detects Pi CPU throttling/undervoltage via vcgencmd
  3. Per-Image Checkpoint  — Saves progress after EVERY image (not just per-model);
                            on power cut, resumes from exact image it stopped at
  4. RAM Watchdog         — Checks available RAM before each model; skips if < 200MB
  5. Cooldown Intervals   — Forced sleep between images, batches, and models
  6. Memory Cleanup       — gc.collect() + model unload + del between each model
  7. Per-Image Timeout    — Skips image if inference > 120s (hung process protection)
  8. Graceful Shutdown    — Catches Ctrl+C, saves checkpoint before exiting
  9. Disk Space Check     — Ensures >= 100MB free before writing outputs
  10. Full Logging        — Writes timestamped log file for debugging

Usage on Raspberry Pi:
  python benchmark_pi_safe.py

  If power cuts, just re-run:
  python benchmark_pi_safe.py
  (It resumes from the exact image it stopped at)

Outputs (in ./benchmark_results/):
  - summary_metrics.csv
  - per_image_results.csv
  - summary_metrics.json
  - summary_report.md
  - quantization_efficiency.csv
  - benchmark.log
"""

from __future__ import annotations

import gc
import json
import logging
import os
import platform
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psutil
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ╔════════════════════════════════════════════════════════════════╗
# ║           CONFIGURATION — EDIT THESE PATHS BELOW             ║
# ║    Change these 3 paths to match your Raspberry Pi setup     ║
# ╚════════════════════════════════════════════════════════════════╝

# ┌─────────────────────────────────────────────────────────────┐
# │  PATH 1: Where the model files (.pt, .onnx) are stored     │
# │  Example (Pi):  /home/pi/models/clean_suite_final           │
# │  Example (Win): C:/Bacterial colony counter/paper_assets/...│
# └─────────────────────────────────────────────────────────────┘
MODELS_DIR = Path("paper_assets/models/clean_suite_final")

# ┌─────────────────────────────────────────────────────────────┐
# │  PATH 2: Where the 100 test images (.jpeg) are             │
# │  Example (Pi):  /home/pi/images                            │
# │  Example (Win): C:/Bacterial colony counter/images          │
# └─────────────────────────────────────────────────────────────┘
IMAGES_DIR = Path("images")

# ┌─────────────────────────────────────────────────────────────┐
# │  PATH 3: Where the annotation JSON files are               │
# │  Each JSON must have: {"colonies_number": <int>, ...}      │
# │  JSON filename must match image: agar_001.jpeg → agar_001.json│
# │  Set to same folder as IMAGES_DIR if they are together     │
# │  Example (Pi):  /home/pi/images     (same folder)          │
# │  Example (Pi):  /home/pi/annotations (separate folder)     │
# └─────────────────────────────────────────────────────────────┘
ANNOTATIONS_DIR = Path("images")   # ← Change if annotations are in a different folder

# ┌─────────────────────────────────────────────────────────────┐
# │  PATH 4: Where to save all output CSVs and reports         │
# │  Example (Pi):  /home/pi/benchmark_results                 │
# │  Example (Win): C:/Bacterial colony counter/benchmark_results│
# └─────────────────────────────────────────────────────────────┘
OUTPUT_DIR = Path("benchmark_results")

# ╔════════════════════════════════════════════════════════════════╗
# ║        INFERENCE SETTINGS — Usually no changes needed        ║
# ╚════════════════════════════════════════════════════════════════╝
CHECKPOINT_FILE = OUTPUT_DIR / "_checkpoint.json"
LOG_FILE        = OUTPUT_DIR / "benchmark.log"
IMGSZ   = 832
CONF    = 0.25
IOU     = 0.45
WARMUP  = 3

# ╔════════════════════════════════════════════════════════════════╗
# ║        THERMAL SAFETY — Tuned for Raspberry Pi 4/5           ║
# ╚════════════════════════════════════════════════════════════════╝
TEMP_THRESHOLD_C      = 70.0    # Pause if CPU temp >= this
TEMP_CRITICAL_C       = 78.0    # Extended cooldown if temp >= this
TEMP_COOLDOWN_TARGET  = 55.0    # Resume only when temp drops to this
TEMP_CHECK_INTERVAL   = 5       # Seconds between temp polls during cooldown

# ╔════════════════════════════════════════════════════════════════╗
# ║        COOLDOWN INTERVALS                                    ║
# ╚════════════════════════════════════════════════════════════════╝
COOLDOWN_BETWEEN_IMGS  = 1.0    # Seconds sleep between EACH image
COOLDOWN_BETWEEN_BATCH = 15     # Seconds sleep every BATCH_SIZE images
COOLDOWN_BETWEEN_MODEL = 45     # Seconds sleep between models
BATCH_SIZE             = 10     # Thermal check + cooldown every N images

# ╔════════════════════════════════════════════════════════════════╗
# ║        RESOURCE LIMITS                                       ║
# ╚════════════════════════════════════════════════════════════════╝
MIN_RAM_MB             = 200    # Skip model if available RAM < this
MIN_DISK_MB            = 100    # Don't write outputs if free disk < this
IMAGE_TIMEOUT_SEC      = 120    # Skip image if inference takes > this

# ╔════════════════════════════════════════════════════════════════╗
# ║        MODEL LIST — All models to benchmark                  ║
# ╚════════════════════════════════════════════════════════════════╝
MODEL_FILES = [
    "best1_fp32.pt",
    "best1_fp16.pt",
    "best1_int8.pt",           # Custom quantized — size only (not YOLO-loadable)
    "best1_pruned_25.pt",
    "best1_fp32.onnx",
    "best1_fp16.onnx",
    "best1_int8.onnx",
]

SKIP_INFERENCE = {"best1_int8.pt"}


# ════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ════════════════════════════════════════════════════════════════

_shutdown_requested = False


# ════════════════════════════════════════════════════════════════
# LOGGING
# ════════════════════════════════════════════════════════════════

def setup_logging():
    """Configure dual logging: console + file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("benchmark")
    logger.setLevel(logging.DEBUG)

    # File handler — full debug log
    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    # Console handler — info and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    return logger


log = setup_logging()


# ════════════════════════════════════════════════════════════════
# GRACEFUL SHUTDOWN (Ctrl+C / SIGTERM)
# ════════════════════════════════════════════════════════════════

def _signal_handler(signum, frame):
    """Catch Ctrl+C and set shutdown flag instead of crashing."""
    global _shutdown_requested
    _shutdown_requested = True
    log.warning("\n  ⚠ SHUTDOWN REQUESTED — finishing current image, saving checkpoint...")


# Register signal handlers
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ════════════════════════════════════════════════════════════════
# THERMAL MONITORING
# ════════════════════════════════════════════════════════════════

def get_cpu_temp() -> float | None:
    """Read CPU temperature. Works on Raspberry Pi, returns None on Windows."""
    # vcgencmd (Raspberry Pi OS)
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            temp_str = result.stdout.strip().replace("temp=", "").replace("'C", "")
            return float(temp_str)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass

    # Linux thermal zone
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if thermal_path.exists():
        try:
            return int(thermal_path.read_text().strip()) / 1000.0
        except (ValueError, IOError):
            pass

    # psutil sensors
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for _, entries in temps.items():
                if entries:
                    return entries[0].current
    except (AttributeError, Exception):
        pass

    return None


def get_throttle_status() -> dict:
    """Check Pi throttle/undervoltage status via vcgencmd.
    Returns dict with boolean flags for each issue."""
    status = {
        "under_voltage": False,
        "freq_capped": False,
        "currently_throttled": False,
        "soft_temp_limit": False,
        "raw": "N/A",
    }
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Output: throttled=0x50005
            hex_str = result.stdout.strip().split("=")[-1]
            val = int(hex_str, 16)
            status["raw"] = hex_str
            status["under_voltage"]       = bool(val & 0x1)
            status["freq_capped"]         = bool(val & 0x2)
            status["currently_throttled"] = bool(val & 0x4)
            status["soft_temp_limit"]     = bool(val & 0x8)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return status


def thermal_guard(context: str = "") -> bool:
    """Check CPU temp. Pause if hot, wait for cooldown. Returns False if shutdown requested."""
    global _shutdown_requested
    if _shutdown_requested:
        return False

    temp = get_cpu_temp()
    if temp is None:
        return True

    if temp >= TEMP_CRITICAL_C:
        log.warning(f"  🔴 CRITICAL TEMP: {temp:.1f}°C [{context}]")
        log.warning(f"     Waiting for cooldown to {TEMP_COOLDOWN_TARGET}°C...")
        while not _shutdown_requested:
            time.sleep(TEMP_CHECK_INTERVAL)
            temp = get_cpu_temp()
            if temp is None or temp <= TEMP_COOLDOWN_TARGET:
                log.info(f"  🟢 Cooled to {temp:.1f}°C. Resuming.")
                return True
        return False

    if temp >= TEMP_THRESHOLD_C:
        log.warning(f"  🟡 HIGH TEMP: {temp:.1f}°C [{context}]. Cooling down...")
        while not _shutdown_requested:
            time.sleep(TEMP_CHECK_INTERVAL)
            temp = get_cpu_temp()
            if temp is None or temp <= TEMP_COOLDOWN_TARGET:
                log.info(f"  🟢 Cooled to {temp:.1f}°C. Resuming.")
                break

    return not _shutdown_requested


# ════════════════════════════════════════════════════════════════
# RESOURCE CHECKS
# ════════════════════════════════════════════════════════════════

def check_ram() -> tuple[bool, float]:
    """Check available RAM. Returns (is_safe, available_mb)."""
    mem = psutil.virtual_memory()
    avail_mb = mem.available / (1024 * 1024)
    return avail_mb >= MIN_RAM_MB, avail_mb


def check_disk() -> tuple[bool, float]:
    """Check free disk space. Returns (is_safe, free_mb)."""
    try:
        usage = psutil.disk_usage(str(OUTPUT_DIR.resolve()))
        free_mb = usage.free / (1024 * 1024)
        return free_mb >= MIN_DISK_MB, free_mb
    except Exception:
        return True, 9999.0


def log_system_status():
    """Log current system resource status."""
    temp = get_cpu_temp()
    temp_str = f"{temp:.1f}°C" if temp else "N/A"
    _, ram_mb = check_ram()
    _, disk_mb = check_disk()
    throttle = get_throttle_status()

    log.info(f"  CPU Temp:      {temp_str}")
    log.info(f"  Available RAM: {ram_mb:.0f} MB")
    log.info(f"  Free Disk:     {disk_mb:.0f} MB")

    if throttle["raw"] != "N/A":
        issues = []
        if throttle["under_voltage"]:   issues.append("UNDERVOLTAGE")
        if throttle["freq_capped"]:     issues.append("FREQ CAPPED")
        if throttle["currently_throttled"]: issues.append("THROTTLED")
        if throttle["soft_temp_limit"]: issues.append("SOFT TEMP LIMIT")
        if issues:
            log.warning(f"  ⚠ THROTTLE FLAGS: {', '.join(issues)} (raw: {throttle['raw']})")
        else:
            log.info(f"  Throttle:      None (raw: {throttle['raw']})")


# ════════════════════════════════════════════════════════════════
# CHECKPOINT / RESUME (Per-Image Granularity)
# ════════════════════════════════════════════════════════════════

def load_checkpoint() -> dict:
    """Load progress from checkpoint file."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                data = json.load(f)
            # Validate structure
            if isinstance(data, dict) and "completed_models" in data:
                return data
        except (json.JSONDecodeError, IOError) as e:
            log.warning(f"  Corrupt checkpoint file, starting fresh: {e}")
    return {
        "completed_models": [],
        "in_progress_model": None,
        "in_progress_image_idx": 0,
        "in_progress_details": [],
        "summaries": [],
        "details": [],
    }


def save_checkpoint(checkpoint: dict) -> None:
    """Save progress to checkpoint file (atomic write to prevent corruption on power cut)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CHECKPOINT_FILE.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(checkpoint, f, indent=2, default=str)
        # Atomic rename — prevents half-written files on power cut
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
        tmp.rename(CHECKPOINT_FILE)
    except IOError as e:
        log.error(f"  Failed to save checkpoint: {e}")


# ════════════════════════════════════════════════════════════════
# DATASET LOADING
# ════════════════════════════════════════════════════════════════

def load_dataset(images_dir: Path, annotations_dir: Path, max_samples: int = 100) -> list[dict[str, Any]]:
    """Load images from images_dir and ground truth from annotations_dir.
    
    Each image (e.g. agar_001.jpeg) needs a matching JSON annotation
    (e.g. agar_001.json) containing: {"colonies_number": <int>, ...}
    
    The JSON can be in the same folder as images or a separate folder.
    """
    rows = []
    image_paths = sorted(images_dir.glob("*.jpeg"))
    
    if not image_paths:
        # Also try .jpg and .png
        image_paths = sorted(images_dir.glob("*.jpg"))
    if not image_paths:
        image_paths = sorted(images_dir.glob("*.png"))

    matched = 0
    missing_ann = 0
    
    for img_path in image_paths:
        # Look for annotation JSON in annotations_dir
        json_name = img_path.stem + ".json"  # e.g. agar_001.json
        json_path = annotations_dir / json_name
        
        if not json_path.exists():
            # Fallback: check if JSON is next to the image
            json_path_fallback = img_path.with_suffix(".json")
            if json_path_fallback.exists():
                json_path = json_path_fallback
            else:
                missing_ann += 1
                continue
        
        try:
            with json_path.open("r", encoding="utf-8") as f:
                ann = json.load(f)
            
            gt_count = int(ann.get("colonies_number", 0))
            
            rows.append({
                "image_path": str(img_path),
                "image_name": img_path.name,
                "gt_count": gt_count,
                "annotation_path": str(json_path),
            })
            matched += 1
        except Exception as e:
            log.warning(f"  Skipping {img_path.name}: {e}")

    log.info(f"  Images found: {len(image_paths)}")
    log.info(f"  Annotations matched: {matched}")
    if missing_ann > 0:
        log.warning(f"  Missing annotations: {missing_ann}")

    if max_samples > 0 and len(rows) > max_samples:
        idx = np.linspace(0, len(rows) - 1, max_samples, dtype=int)
        rows = [rows[i] for i in idx]

    return rows


# ════════════════════════════════════════════════════════════════
# METRICS
# ════════════════════════════════════════════════════════════════

def safe_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def pctl(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.array(values, dtype=np.float64), q))


# ════════════════════════════════════════════════════════════════
# MODEL EVALUATION (with all safeguards)
# ════════════════════════════════════════════════════════════════

def evaluate_model(
    model_path: Path,
    dataset: list[dict[str, Any]],
    checkpoint: dict,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run evaluation with per-image checkpointing and full thermal protection."""
    global _shutdown_requested
    from ultralytics import YOLO

    model_name = model_path.name
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)

    # ── RAM check ──
    ram_ok, ram_avail = check_ram()
    if not ram_ok:
        log.error(f"  ❌ Insufficient RAM: {ram_avail:.0f} MB available (need {MIN_RAM_MB} MB)")
        log.error(f"     Skipping {model_name}. Free up memory and re-run.")
        return None, []

    log.info(f"  RAM available: {ram_avail:.0f} MB")

    # ── Thermal check before loading ──
    if not thermal_guard(f"pre-load {model_name}"):
        return None, []

    # ── Load model ──
    log.info(f"  Loading model...")
    start_load = time.perf_counter()
    try:
        model = YOLO(str(model_path), task="detect")
    except Exception as e:
        log.error(f"  ❌ Failed to load model: {e}")
        return None, []
    load_ms = (time.perf_counter() - start_load) * 1000.0
    log.info(f"  Loaded in {load_ms:.0f} ms")

    # ── Check for resume: skip already processed images ──
    start_idx = 0
    detail_rows = []
    if (checkpoint.get("in_progress_model") == model_name
            and checkpoint.get("in_progress_details")):
        start_idx = checkpoint.get("in_progress_image_idx", 0)
        detail_rows = list(checkpoint.get("in_progress_details", []))
        log.info(f"  📋 Resuming from image {start_idx}/{len(dataset)} "
                 f"({len(detail_rows)} images already done)")

    # ── Warmup (only if starting fresh) ──
    if start_idx == 0:
        log.info(f"  Warmup ({WARMUP} images)...")
        for i in range(min(WARMUP, len(dataset))):
            if not thermal_guard(f"warmup {i+1}"):
                del model; gc.collect()
                return None, []
            try:
                _ = model.predict(
                    dataset[i]["image_path"],
                    imgsz=IMGSZ, conf=CONF, iou=IOU, verbose=False
                )
            except Exception as e:
                log.warning(f"  Warmup image {i} failed: {e}")
            time.sleep(COOLDOWN_BETWEEN_IMGS)

    # ── Main inference loop (with per-image checkpoint) ──
    pred_counts = [r["pred_count"] for r in detail_rows]
    gt_counts   = [r["gt_count"] for r in detail_rows]
    latencies   = [r["latency_ms"] for r in detail_rows]
    peak_mem    = mem_before

    total = len(dataset)
    for idx in range(start_idx, total):
        sample = dataset[idx]

        # ── Shutdown check ──
        if _shutdown_requested:
            log.warning(f"  Shutdown requested at image {idx}/{total}")
            checkpoint["in_progress_model"] = model_name
            checkpoint["in_progress_image_idx"] = idx
            checkpoint["in_progress_details"] = detail_rows
            save_checkpoint(checkpoint)
            del model; gc.collect()
            return None, []

        # ── Thermal check every image ──
        if not thermal_guard(f"img {idx+1}/{total} of {model_name}"):
            checkpoint["in_progress_model"] = model_name
            checkpoint["in_progress_image_idx"] = idx
            checkpoint["in_progress_details"] = detail_rows
            save_checkpoint(checkpoint)
            del model; gc.collect()
            return None, []

        # ── Batch cooldown + status ──
        if idx > start_idx and idx % BATCH_SIZE == 0:
            temp = get_cpu_temp()
            temp_str = f" (CPU: {temp:.1f}°C)" if temp else ""
            log.info(f"  Progress: {idx}/{total}{temp_str}")

            # Check throttle status
            throttle = get_throttle_status()
            if throttle["currently_throttled"] or throttle["under_voltage"]:
                log.warning(f"  ⚠ Pi is throttled/undervoltage! Extended cooldown...")
                time.sleep(COOLDOWN_BETWEEN_BATCH * 2)
            else:
                time.sleep(COOLDOWN_BETWEEN_BATCH)

        # ── Single image inference with timeout protection ──
        try:
            t0 = time.perf_counter()
            results = model.predict(
                sample["image_path"],
                imgsz=IMGSZ, conf=CONF, iou=IOU, verbose=False
            )
            dt_ms = (time.perf_counter() - t0) * 1000.0

            # Timeout check (post-hoc — Python can't preempt threads easily)
            if dt_ms > IMAGE_TIMEOUT_SEC * 1000:
                log.warning(f"  ⏰ Image {sample['image_name']} took {dt_ms/1000:.1f}s "
                            f"(>{IMAGE_TIMEOUT_SEC}s), marking as timeout")
                pred = 0
                dt_ms = IMAGE_TIMEOUT_SEC * 1000
            else:
                pred = int(len(results[0].boxes)) if results and len(results) > 0 else 0

        except Exception as e:
            log.error(f"  ❌ Inference failed on {sample['image_name']}: {e}")
            pred = 0
            dt_ms = 0.0

        gt = int(sample["gt_count"])
        err = pred - gt

        pred_counts.append(pred)
        gt_counts.append(gt)
        latencies.append(dt_ms)

        cur_mem = process.memory_info().rss / (1024 * 1024)
        peak_mem = max(peak_mem, cur_mem)

        detail_rows.append({
            "model":      model_name,
            "image":      sample["image_name"],
            "gt_count":   gt,
            "pred_count": pred,
            "error":      err,
            "abs_error":  abs(err),
            "latency_ms": round(dt_ms, 2),
        })

        # ── Per-image checkpoint (every BATCH_SIZE images) ──
        if (idx + 1) % BATCH_SIZE == 0:
            checkpoint["in_progress_model"] = model_name
            checkpoint["in_progress_image_idx"] = idx + 1
            checkpoint["in_progress_details"] = detail_rows
            save_checkpoint(checkpoint)
            log.debug(f"  Checkpoint saved at image {idx+1}")

        # Brief cooldown
        time.sleep(COOLDOWN_BETWEEN_IMGS)

    # ── Compute metrics ──
    y_true  = np.array(gt_counts, dtype=np.float64)
    y_pred  = np.array(pred_counts, dtype=np.float64)
    abs_err = np.abs(y_true - y_pred)
    lat_arr = np.array(latencies, dtype=np.float64)

    mae     = float(mean_absolute_error(y_true, y_pred))
    mse     = float(mean_squared_error(y_true, y_pred))
    rmse    = float(np.sqrt(mse))
    medae   = float(np.median(abs_err))
    p90ae   = pctl(abs_err.tolist(), 90)
    mape    = safe_mape(y_true, y_pred)
    bias    = float(np.mean(y_pred - y_true))

    # ± Standard Deviations (Professor's requirement)
    mae_std = float(np.std(abs_err))
    lat_std = float(np.std(lat_arr))

    within_1  = float(np.mean(abs_err <= 1) * 100.0)
    within_5  = float(np.mean(abs_err <= 5) * 100.0)
    within_10 = float(np.mean(abs_err <= 10) * 100.0)

    try:
        r2 = float(r2_score(y_true, y_pred))
    except Exception:
        r2 = 0.0

    avg_lat = float(np.mean(lat_arr))
    p50_lat = pctl(latencies, 50)
    p95_lat = pctl(latencies, 95)
    fps     = float(1000.0 / avg_lat) if avg_lat > 0 else 0.0

    summary = {
        "model":            model_name,
        "size_mb":          round(model_path.stat().st_size / (1024 * 1024), 2),
        "mae":              round(mae, 4),
        "mae_std":          round(mae_std, 4),
        "mse":              round(mse, 4),
        "rmse":             round(rmse, 4),
        "mape":             round(mape, 4),
        "r2":               round(r2, 6),
        "latency_avg_ms":   round(avg_lat, 2),
        "latency_std_ms":   round(lat_std, 2),
        "fps":              round(fps, 4),
        "ram_peak_mb":      round(peak_mem, 2),
        "ram_delta_mb":     round(max(0.0, peak_mem - mem_before), 2),
        "load_time_ms":     round(load_ms, 2),
        "medae":            round(medae, 4),
        "p90ae":            round(p90ae, 4),
        "bias":             round(bias, 4),
        "within_1_pct":     round(within_1, 2),
        "within_5_pct":     round(within_5, 2),
        "within_10_pct":    round(within_10, 2),
        "latency_p50_ms":   round(p50_lat, 2),
        "latency_p95_ms":   round(p95_lat, 2),
        "samples":          len(dataset),
    }

    # Free memory
    del model
    gc.collect()

    return summary, detail_rows


def add_size_only_entry(model_path: Path) -> dict[str, Any]:
    """For models that can't be loaded by YOLO (e.g., custom INT8 .pt)."""
    return {
        "model":          model_path.name,
        "size_mb":        round(model_path.stat().st_size / (1024 * 1024), 2),
        "mae":            None, "mae_std": None, "mse": None, "rmse": None,
        "mape":           None, "r2": None,
        "latency_avg_ms": None, "latency_std_ms": None, "fps": None,
        "ram_peak_mb":    None, "ram_delta_mb": None, "load_time_ms": None,
        "medae":          None, "p90ae": None, "bias": None,
        "within_1_pct":   None, "within_5_pct": None, "within_10_pct": None,
        "latency_p50_ms": None, "latency_p95_ms": None,
        "samples":        0,
        "note":           "Custom INT8 format — size only (use best1_int8.onnx for inference)",
    }


# ════════════════════════════════════════════════════════════════
# OUTPUT WRITERS
# ════════════════════════════════════════════════════════════════

def write_outputs(summaries: list[dict], details: list[dict]) -> None:
    """Write all output files."""
    # Disk space check
    disk_ok, disk_mb = check_disk()
    if not disk_ok:
        log.error(f"  ❌ Low disk space: {disk_mb:.0f} MB free. Cannot write outputs!")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame(summaries)
    detail_df  = pd.DataFrame(details)

    summary_df.to_csv(OUTPUT_DIR / "summary_metrics.csv", index=False)
    detail_df.to_csv(OUTPUT_DIR / "per_image_results.csv", index=False)
    summary_df.to_json(OUTPUT_DIR / "summary_metrics.json", orient="records", indent=2)

    # Markdown report
    lines = [
        "# Benchmark Results (Pi-Safe v2)",
        "",
        f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Models evaluated: {len(summary_df)}",
        f"- Total per-image records: {len(detail_df)}",
        "",
    ]
    runnable = summary_df.dropna(subset=["mae"])
    if not runnable.empty:
        best_mae = runnable.sort_values("mae").iloc[0]
        best_lat = runnable.sort_values("latency_avg_ms").iloc[0]
        lines.append("## Highlights")
        lines.append(f"- Best accuracy: **{best_mae['model']}** "
                     f"(MAE={best_mae['mae']:.3f} +/- {best_mae.get('mae_std', 0):.3f})")
        lines.append(f"- Fastest: **{best_lat['model']}** "
                     f"({best_lat['latency_avg_ms']:.2f} +/- {best_lat.get('latency_std_ms', 0):.2f} ms)")
        lines.append("")
        lines.append("## Full Summary")
        lines.append(summary_df.to_markdown(index=False))

    (OUTPUT_DIR / "summary_report.md").write_text("\n".join(lines), encoding="utf-8")

    # Quantization efficiency table
    if not runnable.empty:
        baseline = runnable[runnable["model"].str.contains("fp32", case=False)]
        base_mae = float(baseline.iloc[0]["mae"]) if not baseline.empty else float(runnable.iloc[0]["mae"])

        rows = []
        for _, row in summary_df.iterrows():
            mae_val = row.get("mae")
            if mae_val is not None and base_mae > 0:
                retention = min((base_mae / float(mae_val)) * 100.0, 100.0)
            else:
                retention = None

            rows.append({
                "Model":            row["model"],
                "MAE":              row.get("mae"),
                "MAE_SD":           row.get("mae_std"),
                "MSE":              row.get("mse"),
                "RMSE":             row.get("rmse"),
                "MAPE (%)":         row.get("mape"),
                "R2":               row.get("r2"),
                "Latency (ms)":     row.get("latency_avg_ms"),
                "Latency_SD (ms)":  row.get("latency_std_ms"),
                "Size (MB)":        row.get("size_mb"),
                "RAM Cost (MB)":    row.get("ram_delta_mb"),
                "Acc Retention (%)": round(retention, 2) if retention else None,
            })
        pd.DataFrame(rows).to_csv(OUTPUT_DIR / "quantization_efficiency.csv", index=False)

    log.info(f"\n  All outputs saved to: {OUTPUT_DIR.resolve()}")


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

def main() -> None:
    global _shutdown_requested

    log.info("=" * 60)
    log.info("  Pi-Safe Model Benchmark v2 (Hardened)")
    log.info("=" * 60)
    log.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"  Platform: {platform.machine()} / {platform.system()}")
    log.info(f"  Models:   {MODELS_DIR.resolve()}")
    log.info(f"  Images:   {IMAGES_DIR.resolve()}")
    log.info(f"  Labels:   {ANNOTATIONS_DIR.resolve()}")
    log.info(f"  Output:   {OUTPUT_DIR.resolve()}")
    log.info("")
    log.info("  System Status:")
    log_system_status()

    # ── Load checkpoint ──
    checkpoint = load_checkpoint()
    completed = set(checkpoint.get("completed_models", []))
    if completed:
        log.info(f"\n  📋 Resuming! Already completed: {list(completed)}")

    in_progress = checkpoint.get("in_progress_model")
    if in_progress:
        ip_idx = checkpoint.get("in_progress_image_idx", 0)
        log.info(f"  📋 In-progress model: {in_progress} (stopped at image {ip_idx})")

    # ── Validate model files ──
    models_to_run = []
    for mf in MODEL_FILES:
        mp = MODELS_DIR / mf
        if not mp.exists():
            log.warning(f"  ⚠ Model not found, skipping: {mp}")
            continue
        if mf in completed and mf != in_progress:
            log.info(f"  ✓ Already completed: {mf}")
            continue
        models_to_run.append(mp)

    if not models_to_run and not completed:
        log.error("\n  ❌ No models found! Check MODELS_DIR path.")
        sys.exit(1)

    # ── Load dataset ──
    dataset = load_dataset(IMAGES_DIR, ANNOTATIONS_DIR, max_samples=100)
    if not dataset:
        log.error("\n  ❌ No image/json pairs found! Check IMAGES_DIR path.")
        sys.exit(1)
    log.info(f"\n  Dataset: {len(dataset)} images loaded")

    # ── Evaluate each model ──
    summaries = checkpoint.get("summaries", [])
    details   = checkpoint.get("details", [])

    for i, model_path in enumerate(models_to_run):
        if _shutdown_requested:
            break

        model_name = model_path.name
        log.info(f"\n{'─' * 60}")
        log.info(f"  [{i+1}/{len(models_to_run)}] Evaluating: {model_name}")
        log.info(f"  Size: {model_path.stat().st_size / 1024 / 1024:.2f} MB")
        log.info(f"{'─' * 60}")

        # ── Pre-model cooldown ──
        if i > 0:
            log.info(f"  ⏱ Cooling down for {COOLDOWN_BETWEEN_MODEL}s between models...")
            time.sleep(COOLDOWN_BETWEEN_MODEL)

        log.info("  Pre-model system status:")
        log_system_status()

        if not thermal_guard(f"pre-model {model_name}"):
            break

        try:
            if model_name in SKIP_INFERENCE:
                log.info(f"  ⚠ {model_name}: custom INT8 format — recording size only.")
                summary = add_size_only_entry(model_path)
                rows = []
            else:
                summary, rows = evaluate_model(model_path, dataset, checkpoint)

                if summary is None:
                    # Model was interrupted (shutdown or thermal)
                    log.warning(f"  Model {model_name} interrupted. Progress saved.")
                    break

            summaries.append(summary)
            details.extend(rows)

            if summary.get("mae") is not None:
                log.info(f"\n  📊 Results for {model_name}:")
                log.info(f"     MAE  = {summary['mae']:.3f} ± {summary['mae_std']:.3f}")
                log.info(f"     MSE  = {summary['mse']:.2f}")
                log.info(f"     RMSE = {summary['rmse']:.3f}")
                log.info(f"     R²   = {summary['r2']:.4f}")
                log.info(f"     Latency = {summary['latency_avg_ms']:.2f} "
                         f"± {summary['latency_std_ms']:.2f} ms")
                log.info(f"     FPS  = {summary['fps']:.2f}")
                log.info(f"     RAM Δ = {summary['ram_delta_mb']:.1f} MB")

        except Exception as exc:
            log.error(f"  ❌ FAILED: {exc}")
            log.debug(traceback.format_exc())
            summaries.append({
                "model":   model_name,
                "size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
                "status":  f"failed: {exc}",
            })

        # ── Save checkpoint (model complete) ──
        completed.add(model_name)
        checkpoint = {
            "completed_models": list(completed),
            "in_progress_model": None,
            "in_progress_image_idx": 0,
            "in_progress_details": [],
            "summaries": summaries,
            "details": details,
        }
        save_checkpoint(checkpoint)
        log.info(f"  💾 Checkpoint saved ({len(completed)} models complete)")

        # Force memory cleanup
        gc.collect()
        log.debug(f"  Memory cleaned up. RSS: "
                  f"{psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024:.0f} MB")

    # ── Write final outputs ──
    if not _shutdown_requested:
        log.info(f"\n{'=' * 60}")
        log.info("  Writing final outputs...")
        log.info(f"{'=' * 60}")
        write_outputs(summaries, details)

        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
            log.info("  🗑 Checkpoint file removed (all models complete)")

        log.info(f"\n  🎉 Benchmark complete! {len(summaries)} models evaluated.")
        log.info(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        log.warning("\n  ⚠ Benchmark interrupted. Progress saved to checkpoint.")
        log.warning("     Re-run this script to continue from where you left off.")
        # Still write partial outputs
        if summaries:
            write_outputs(summaries, details)
            log.info("  Partial results saved.")


if __name__ == "__main__":
    main()
