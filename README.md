# Bacterial Colony Counter & Intelligence Platform

An advanced, end-to-end solution for automated bacterial colony detection, counting, and classification. This platform leverages state-of-the-art Deep Learning models optimized for both cloud and edge deployment (Raspberry Pi).

## 🚀 Key Features

- **High-Precision Detection**: Optimized YOLOv8 models for counting dense colony clusters.
- **Advanced Classification**: Custom CNN architectures for species/morphology classification.
- **Robust Preprocessing**: V1.0.0 pipeline featuring LAB color space normalization, bilateral filtering, and dynamic Petri dish isolation.
- **Edge-Optimized**: Support for INT8 Quantization, Structured Pruning, and ONNX runtime for real-time performance on low-power devices.
- **Cross-Platform Ecosystem**:
  - **Web Dashboard**: Full management console for data analysis and reporting.
  - **Mobile App**: Smartphone-based field counting via Expo/React Native.
  - **Backend API**: Scalable Node.js/Express backend for data persistence and model serving.

## 📂 Project Structure

```text
├── core/                   # V1.0.0 Preprocessing & Core Utilities
├── cnn/                    # CNN Training and Testing Implementations
├── yolo/                   # YOLOv8 Detection and Counting Logic
├── web/                    # React-based Web Dashboard (Frontend/Backend)
├── mobile/                 # Expo/React Native Mobile Application
├── cfu-counter-backend/    # Main Mobile App Backend API
├── scripts/                # Optimization (Pruning, Quantization, ONNX)
└── requirements.txt        # Core Dependencies
```

## 🛠️ Tech Stack

- **ML/CV**: PyTorch, OpenCV, YOLOv8, ONNX, Albumentations.
- **Frontend**: React (Web), React Native/Expo (Mobile).
- **Backend**: Node.js, Express, Python (FastAPI/Flask).
- **Optimization**: TensorRT, TFLite, INT8 Static/Dynamic Quantization.

## 🏁 Getting Started

### Preprocessing
To use the advanced preprocessing pipeline:
```python
from core.preprocessing import PreprocessingPipeline
pipeline = PreprocessingPipeline(output_dir='processed_results')
pipeline.process_directory('path/to/images')
```

### Installation
```bash
pip install -r requirements.txt
```

## 📈 Performance & Optimization
This repository includes specialized scripts for model compression:
- `scripts/prune_model.py`: Structured and Unstructured pruning logic.
- `scripts/quantize_onnx.py`: Static INT8 quantization for ONNX models.
- `scripts/benchmark_pi_safe.py`: Real-time benchmarking on Raspberry Pi 4/5.

---
*Note: Large model weights (.pt, .pb) are excluded from this repository for efficiency. Please refer to the documentation for model download links.*
