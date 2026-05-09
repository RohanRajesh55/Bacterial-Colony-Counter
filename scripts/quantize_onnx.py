from onnxruntime.quantization import quantize_dynamic, QuantType
import os

fp32_onnx_path = r"C:\Bacterial colony counter\paper_assets\models\clean_suite_20260416\best1_fp32.onnx"
int8_onnx_path = r"C:\Bacterial colony counter\paper_assets\models\clean_suite_20260416\best1_int8.onnx"

print(f"Quantizing {fp32_onnx_path} to {int8_onnx_path}...")
try:
    quantize_dynamic(
        model_input=fp32_onnx_path,
        model_output=int8_onnx_path,
        weight_type=QuantType.QUInt8
    )
    print(f"Success! Saved as Size: {os.path.getsize(int8_onnx_path)/1024/1024:.2f} MB")
except Exception as e:
    print(f"Failed: {e}")
