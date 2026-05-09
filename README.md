# Bacterial Colony Counting and Classification on Edge Devices

An advanced, end-to-end solution for automated bacterial colony detection, counting, and classification. This platform leverages deep learning models optimized for both cloud and edge deployment, specifically targeting Raspberry Pi environments.

## Dataset

This project utilizes the **AGAR (Annotated Germs for Automated Recognition)** dataset developed by NeuroSYS. It contains 18,000 photos of microbial colonies with over 336,000 annotations.

- **Official Dataset Link:** [https://agar.neurosys.com/](https://agar.neurosys.com/)

## Project Structure

```text
├── core/                   # V1.0.0 Preprocessing and Core Utilities
├── cnn/                    # CNN Training and Testing Implementations
├── yolo/                   # YOLOv8 Detection and Counting Logic
├── web/                    # React-based Web Dashboard (Frontend and Backend)
├── mobile/                 # Expo/React Native Mobile Application
├── cfu-counter-backend/    # Main Mobile App Backend API
├── scripts/                # Optimization (Pruning, Quantization, ONNX)
└── requirements.txt        # Core Dependencies
```

## Getting Started

### 1. Installation

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

### 2. Preprocessing

The preprocessing pipeline isolates the Petri dish and normalizes lighting conditions to ensure consistent model performance across different agar types.

```python
from core.preprocessing import PreprocessingPipeline

# Initialize the pipeline
pipeline = PreprocessingPipeline(output_dir='processed_output')

# Process a directory of raw images
pipeline.process_directory('path/to/raw_images', num_workers=4)
```

### 3. Model Training

#### CNN Classification

To train the custom CNN classifier:

```bash
python cnn/cnn_train.py --data path/to/processed_data --epochs 50
```

#### YOLOv8 Detection

To train the YOLOv8 detection and counting model:

```bash
python yolo/yolo_train.py --data yolo/data.yaml --epochs 100 --imgsze 640
```

### 4. Model Compression

Optimize models for edge deployment using pruning and quantization.

#### Pruning

Use the pruning script to remove redundant parameters:

```bash
python scripts/prune_model.py --model path/to/model.pt --amount 0.3
```

#### Quantization

Convert models to INT8 ONNX format for faster inference on CPUs:

```bash
python scripts/quantize_onnx.py --input model.onnx --output model_int8.onnx
```

### 5. Edge Deployment (Raspberry Pi)

The platform is designed to run efficiently on Raspberry Pi 4/5 using ONNX Runtime.

1.  Transfer the quantized model to the Pi.
2.  Run the benchmark script to verify performance:

```bash
python scripts/benchmark_pi_safe.py --model model_int8.onnx --image test.jpg
```

### 6. Website and Dashboard

The web dashboard provides a management console for viewing results and managing datasets.

1.  **Backend Setup**:
    ```bash
    cd web/backend
    npm install
    npm start
    ```
2.  **Frontend Setup**:
    ```bash
    cd web/frontend
    npm install
    npm run dev
    ```

### 7. Mobile Application

The mobile app allows for field counting using a smartphone camera.

1.  **Mobile App Setup**:
    ```bash
    cd mobile
    npm install
    npx expo start
    ```
2.  **Mobile Backend Setup**:
    ```bash
    cd cfu-counter-backend
    npm install
    npm start
    ```

---

_Note: Large model weights (.pt, .pb) are excluded from this repository. Users should train their own models or download pre-trained weights separately._

## Citation

If you use the AGAR dataset or this platform in your research, please cite the original AGAR paper:

```bibtex
@misc{majchrowska2021agar,
  title={AGAR a microbial colony dataset for deep learning detection},
  author={Sylwia Majchrowska and Jaros{\l}aw Paw{\l}owski and Grzegorz Gu{\l}a and Tomasz Bonus and Agata Hanas and Adam Loch and Agnieszka Pawlak and Justyna Roszkowiak and Tomasz Golan and Zuzanna Drulis-Kawa},
  year={2021},
  eprint={2108.01234},
  archivePrefix={arXiv},
  primaryClass={cs.CV}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
