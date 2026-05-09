import torch
import torch.quantization
from ultralytics import YOLO
import os
import sys

def convert_models():
    # Paths
    model_path = r"C:\Bacterial colony counter\best1.pt"
    output_dir = r"C:\Bacterial colony counter\test_output\models"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading original model from {model_path}...")
    # Load as YOLO model
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        return

    # 1. Save locally as Baseline (TorchScript or just copy .pt for consistency in sizing)
    # Actually YOLO .pt is just a checkpoint. Let's export to TorchScript as "Baseline" for fair comparison 
    # or just keep the .pt file. The user wants 'original'.
    # We'll stick to .pt for original.
    baseline_path = os.path.join(output_dir, "best1_original.pt")
    # Just copying the file for isolation
    with open(model_path, 'rb') as src, open(baseline_path, 'wb') as dst:
        dst.write(src.read())
    print(f"saved Original: {baseline_path}")

    # 2. FP16 (Half Precision) - TorchScript
    # Note: On CPU, half=True is ignored by Ultralytics for TorchScript.
    print("Converting to TorchScript (Baseline/FP32 on CPU)...")
    try:
        # Ultralytics export
        fs_file = model.export(format="torchscript", half=False, optimize=False, int8=False)
        
        # Robust move
        import shutil
        import time
        if isinstance(fs_file, str) and os.path.exists(fs_file):
             dest = os.path.join(output_dir, "best1_torchscript.pt")
             # Retry loop for permission errors
             for _ in range(3):
                 try:
                     if os.path.exists(dest): os.remove(dest)
                     shutil.move(fs_file, dest)
                     print(f"saved TorchScript: {dest}")
                     break
                 except PermissionError:
                     time.sleep(1)
                 except Exception as e:
                     print(f"Move failed: {e}")
                     break
    except Exception as e:
        print(f"Error creating TorchScript: {e}")


    # 3. ONNX (FP16)
    print("Converting to ONNX (FP16)...")
    try:
        # Export with simplify=False to avoid onnxslim install
        # half=True works for ONNX on CPU (casts weights)
        onnx_file = model.export(format="onnx", half=True, dynamic=True, simplify=False) 
        
        if isinstance(onnx_file, str) and os.path.exists(onnx_file):
             dest = os.path.join(output_dir, "best1_fp16.onnx")
             if os.path.exists(dest): os.remove(dest)
             os.rename(onnx_file, dest)
             print(f"saved ONNX: {dest}")
    except Exception as e:
        print(f"Error creating ONNX: {e}")

    # 4. INT8 (Dynamic Quantization)
    # PyTorch Dynamic Quantization works best on nn.Linear/LSTM. YOLO is mostly Conv2d.
    # Conv2d dynamic quant is not really supported well in standard torch.quantization.quantize_dynamic (it only does Linear/RNN).
    # However, we can try Post-training static quantization with dummy data if we really wanted, 
    # BUT user said "no sampledata" and "no original data".
    # So we will try "Int8 TorchScript" export from Ultralytics if available (often requires data).
    # If not, we will attempt ONNX Quantization specifically (Dynamic).
    
    print("Converting to INT8 (ONNX Dynamic)...")
    # We will use onnxruntime to quantize the ONNX model we just made.
    try:
        import onnx
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        onnx_input = os.path.join(output_dir, "best1_fp16.onnx") # Use the fp16 or create a fp32 onnx for int8? 
        # Usually better to quantize from FP32.
        
        # generate fp32 onnx first
        onnx_fp32 = model.export(format="onnx", half=False, dynamic=True)
        if isinstance(onnx_fp32, str) and os.path.exists(onnx_fp32):
             onnx_fp32_path = os.path.join(output_dir, "best1_fp32_temp.onnx")
             if os.path.exists(onnx_fp32_path): os.remove(onnx_fp32_path)
             os.rename(onnx_fp32, onnx_fp32_path)
             
             onnx_int8_path = os.path.join(output_dir, "best1_int8_dynamic.onnx")
             quantize_dynamic(
                 onnx_fp32_path,
                 onnx_int8_path,
                 weight_type=QuantType.QUInt8
             )
             print(f"saved ONNX INT8 (Dynamic): {onnx_int8_path}")
             
             # cleanup temp
             if os.path.exists(onnx_fp32_path):
                 os.remove(onnx_fp32_path)
                 
    except ImportError:
        print("onnxruntime or onnx not installed. Skipping INT8 ONNX.")
    except Exception as e:
        print(f"Error creating INT8 ONNX: {e}")

if __name__ == "__main__":
    convert_models()
