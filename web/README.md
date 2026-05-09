# Bacterial Colony Counter Web Application

AI-powered web application for bacterial colony detection, counting, and classification using deep learning.

## 🧫 Features

- **Dual Model Support**: Choose between CNN (count + classification) or YOLO (object detection)
- **7 Bacterial Classes**: B.subtilis, C.albicans, E.coli, P.aeruginosa, S.aureus, Contamination, Defect
- **Bounding Box Visualization**: Toggle detection boxes for YOLO results
- **Modern UI**: Dark theme with responsive design
- **Docker Ready**: Easy deployment with Docker Compose

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Model weights (see below)

### 1. Set Up Model Weights

Copy your trained model files to the `models/` directory:

```bash
mkdir -p web/models/cnn web/models/yolo

# Copy your trained models
cp final_best.pth web/models/cnn/
cp best.pt web/models/yolo/
```

### 2. Run with Docker

```bash
cd web
docker-compose up --build
```

The application will be available at:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📁 Project Structure

```
web/
├── backend/                 # FastAPI backend
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration settings
│   ├── models/              # ML model wrappers
│   │   ├── cnn_model.py     # CNN inference
│   │   └── yolo_model.py    # YOLO inference
│   ├── routers/             # API endpoints
│   └── services/            # Business logic
│
├── frontend/                # React frontend
│   ├── src/
│   │   ├── App.jsx          # Main component
│   │   └── components/      # UI components
│   └── index.html
│
├── models/                  # Model weights (create this)
│   ├── cnn/final_best.pth
│   └── yolo/best.pt
│
├── docker-compose.yml       # Standard deployment
└── docker-compose.pi.yml    # Raspberry Pi deployment
```

## 🔧 Development

### Local Backend (without Docker)

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python main.py
```

### Local Frontend

```bash
cd frontend
npm install
npm run dev
```

## 🍓 Raspberry Pi Deployment

For Raspberry Pi 4 (ARM64):

```bash
cd web
docker-compose -f docker-compose.pi.yml up --build
```

**Note**: Pi deployment uses reduced image size (640px) for better performance.

## 📡 API Endpoints

| Method | Endpoint       | Description                |
| ------ | -------------- | -------------------------- |
| POST   | `/api/predict` | Analyze image for colonies |
| GET    | `/health`      | Health check               |
| GET    | `/docs`        | Swagger documentation      |

### Example Request

```bash
curl -X POST "http://localhost:8000/api/predict" \
  -F "image=@petri_dish.jpg" \
  -F "model_type=yolo" \
  -F "show_boxes=true"
```

## 🎨 Class Colors

| Class         | Color  |
| ------------- | ------ |
| B.subtilis    | Blue   |
| C.albicans    | Green  |
| E.coli        | Cyan   |
| P.aeruginosa  | Purple |
| S.aureus      | Yellow |
| Contamination | Red    |
| Defect        | Gray   |

## 📝 License

MIT License
