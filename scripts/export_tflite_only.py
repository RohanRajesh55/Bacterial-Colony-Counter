"""Export TFLite only from the FP32 .pt model."""
import os
import shutil

OUT_DIR = r"C:\Bacterial colony counter\paper_assets\models\clean_suite_final"
FP32_PT = os.path.join(OUT_DIR, "best1_fp32.pt")

# Cleanup leftover temps from cancelled run
for item in os.listdir(OUT_DIR):
    full = os.path.join(OUT_DIR, item)
    if item.startswith("_tmp"):
        if os.path.isdir(full):
            shutil.rmtree(full, ignore_errors=True)
        else:
            os.remove(full)
        print(f"Cleaned up: {item}")

from ultralytics import YOLO

print("\nExporting TFLite...")
tmp = os.path.join(OUT_DIR, "_tfl_src.pt")
shutil.copy(FP32_PT, tmp)

model = YOLO(tmp)
model.export(format="tflite", half=True, imgsz=832)

# Find the .tflite file
tflite_found = None
for root, dirs, files in os.walk(OUT_DIR):
    for f in files:
        if f.endswith(".tflite"):
            tflite_found = os.path.join(root, f)
            break
    if tflite_found:
        break

if tflite_found:
    dst = os.path.join(OUT_DIR, "best1_fp16.tflite")
    shutil.copy(tflite_found, dst)
    print(f"\n✅ TFLite saved: {dst} ({os.path.getsize(dst)/1024/1024:.2f} MB)")
else:
    print("\n❌ No .tflite file found!")

# Cleanup
for item in os.listdir(OUT_DIR):
    full = os.path.join(OUT_DIR, item)
    if item.startswith("_tfl"):
        if os.path.isdir(full):
            shutil.rmtree(full, ignore_errors=True)
        elif not item.endswith(".tflite"):
            os.remove(full)

# Final listing
print("\n=== FINAL MODEL SUITE ===")
for f in sorted(os.listdir(OUT_DIR)):
    full = os.path.join(OUT_DIR, f)
    if os.path.isfile(full):
        print(f"  {f:40s}  {os.path.getsize(full)/1024/1024:8.2f} MB")
