# CFU-Counter: Automated Colony Counting SaaS

A deep learning-powered web application for automatic bacterial colony counting from petri dish images. Built for research labs and QC teams who need fast, reliable colony counting.

```
  Upload Image ──> ML Model ──> Colony Count + Annotated Image
       |              |                    |
   [Frontend]    [Backend]           [Results]
    React        FastAPI            Bounding boxes
                 RT-DETR            CSV export
```

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Current Status](#current-status)
4. [Tech Stack](#tech-stack)
5. [Directory Structure](#directory-structure)
6. [Setup Guide](#setup-guide)
7. [API Reference](#api-reference)
8. [Database Schema](#database-schema)
9. [ML Models](#ml-models)
10. [Research Background](#research-background)
11. [Development Workflow](#development-workflow)
12. [License Compliance](#license-compliance)

---

## Project Overview

### What It Does

CFU-Counter automates the tedious task of counting bacterial colonies on agar plates. Instead of manually counting hundreds of tiny dots under a microscope, you:

1. Take a photo of your petri dish
2. Upload it to the web app
3. Get an accurate colony count in seconds

### Why It Matters

Manual colony counting is:
- **Slow**: 5-10 minutes per plate
- **Error-prone**: Human fatigue causes miscounts
- **Inconsistent**: Different people count differently

Automated counting is:
- **Fast**: 2-3 seconds per image
- **Consistent**: Same algorithm, same results
- **Scalable**: Process hundreds of plates per hour

### Target Users

- University microbiology labs
- Food safety testing facilities
- Pharmaceutical QC departments
- Environmental monitoring labs

---

## Architecture

### High-Level System Design

```
+------------------+     HTTP/REST     +------------------+
|                  |                   |                  |
|    Frontend      | <--------------> |    Backend       |
|    (React)       |                   |    (FastAPI)     |
|    Port 3000     |                   |    Port 8000     |
|                  |                   |                  |
+------------------+                   +--------+---------+
                                               |
                    +-------------+------------+------------+
                    |             |            |            |
                    v             v            v            v
              +---------+   +---------+  +----------+  +---------+
              | RT-DETR |   | Postgres|  |  MinIO   |  |  SMTP   |
              | (Model) |   |  (DB)   |  | (Storage)|  | (Email) |
              +---------+   +---------+  +----------+  +---------+
                  GPU         :5432        :9000       Optional
```

### Request Flow: Image Upload to Results

```
User                Frontend              Backend                 Services
 |                     |                     |                       |
 |  1. Select image    |                     |                       |
 |-------------------->|                     |                       |
 |                     |  2. POST /api/predict                       |
 |                     |-------------------->|                       |
 |                     |                     |  3. Load image        |
 |                     |                     |---------------------->|
 |                     |                     |  4. RT-DETR inference |
 |                     |                     |<----------------------|
 |                     |                     |  5. Save to MinIO     |
 |                     |                     |---------------------->|
 |                     |                     |  6. Save to Postgres  |
 |                     |                     |---------------------->|
 |                     |  7. JSON response   |                       |
 |                     |<--------------------|                       |
 |  8. Display results |                     |                       |
 |<--------------------|                     |                       |
```

### Frontend Architecture

```
src/
+-- App.jsx                 # Root component, routing
+-- main.jsx                # Entry point
|
+-- pages/
|   +-- HomePage.jsx        # Main upload interface
|   +-- LoginPage.jsx       # User authentication
|   +-- RegisterPage.jsx    # Account creation
|   +-- HistoryPage.jsx     # Past predictions
|   +-- AccountPage.jsx     # Settings + API keys
|   +-- CorrectionPage.jsx  # Full-page correction editor (Phase 2)
|
+-- components/
|   +-- ImageUpload.jsx     # Drag-and-drop upload
|   +-- ResultsDisplay.jsx  # Count + annotated image
|   +-- FeedbackButton.jsx  # User correction input
|   +-- PredictionHistory.jsx   # Paginated history grid
|   +-- AccountSettings.jsx     # Password change form
|   +-- APIKeyManager.jsx       # Create/revoke API keys
|   +-- ProtectedRoute.jsx      # Auth guard for routes
|   +-- CorrectionCanvas.jsx    # Interactive canvas with box editing
|   +-- CanvasToolbar.jsx       # Tool selection, undo/redo, save
|   +-- MiniMap.jsx             # Thumbnail navigation when zoomed
|   +-- ConfidencePanel.jsx     # Low-confidence detection guidance
|
+-- hooks/
|   +-- useViewport.js          # Canvas zoom/pan/coordinate transforms
|   +-- useCorrectionState.js   # Correction actions + undo/redo stack
|
+-- context/
|   +-- AuthContext.jsx     # Global auth state
|
+-- services/
|   +-- api.js              # API client functions
|
+-- utils/
    +-- csvExport.js        # Generate CSV downloads
    +-- imageDownload.js    # Download annotated images
```

### Backend Architecture

```
api/
+-- main.py                 # FastAPI app, lifespan, CORS
+-- config.py               # Settings (env vars)
+-- state.py                # Shared ML model state
|
+-- routers/
|   +-- health.py           # GET /health
|   +-- predict.py          # POST /api/predict (returns detections with boxes)
|   +-- corrections.py      # POST/GET /api/corrections (user edits)
|   +-- feedback.py         # POST /api/feedback
|   +-- history.py          # GET /api/history
|   +-- account.py          # PUT /api/account/password
|   +-- api_keys.py         # CRUD /api/api-keys
|
+-- auth/
|   +-- router.py           # /api/auth/* endpoints
|   +-- dependencies.py     # get_current_user, etc.
|   +-- security.py         # JWT, password hashing
|   +-- email.py            # Password reset emails
|   +-- schemas.py          # Pydantic models
|
+-- db/
|   +-- models.py           # SQLAlchemy ORM models
|   +-- session.py          # Async session factory
|   +-- base.py             # Declarative base
|
+-- services/
|   +-- rtdetr_service.py   # Model loading + inference
|
+-- storage/
|   +-- s3_client.py        # MinIO/S3 operations
|
+-- schemas/
    +-- history.py          # Response schemas
    +-- api_keys.py         # API key schemas
```

---

## Current Status

### Development Progress

**SaaS Platform (Complete)**

Phases 1-8 built the full-stack web application: API, frontend, auth, persistence, export.

**Model Fine-Tuning (Complete)**

D-FINE (RT-DETRv4, HGNetv2-X backbone) fine-tuned on AGAR dataset for single-class colony detection:

| Metric | YOLOv8 Baseline | D-FINE Result |
|--------|-----------------|---------------|
| mAP@0.5:0.95 | 0.622 | 0.639 (+2.7%) |

Trained 50 epochs on 4x A40 GPUs, batch size 24, AMP enabled. Weights on Google Drive (see below).

**Interactive Correction UI (75% Complete)**

```
Phase 1: Model Foundation       [##########] Complete
Phase 2: Interactive Correction [########  ] 75% (3/4 plans)
Phase 3: Audit & Export         [          ] Not Started
Phase 4: Production Scale       [          ] Not Started
```

Phase 2 has API endpoints for corrections, a canvas editor with zoom/pan, and correction tools (add/remove/adjust/split with undo/redo). Remaining: wire the correction page into the app with TNTC warnings, confidence guidance, mini-map, and export.

### What Works Right Now

| Feature | Status | Notes |
|---------|--------|-------|
| Image upload via web UI | Working | Drag-and-drop or click to select |
| Colony detection | Working | Fine-tuned D-FINE model (mAP 0.639) |
| Bounding box visualization | Working | Green boxes with confidence scores |
| Detection coordinates API | Working | Individual box coordinates + confidence |
| Corrections API | Working | Persist add/remove/adjust/split actions |
| Interactive canvas editor | Working | Zoom/pan, tool palette, keyboard shortcuts |
| Correction tools | Working | Add, remove, adjust, split with undo/redo |
| CSV export | Working | Filename, count, timestamp, model |
| Image download | Working | Annotated image as JPEG |
| User registration | Working | Email + password |
| User login/logout | Working | JWT in HttpOnly cookie |
| Password reset | Working | Email-based reset flow |
| Prediction history | Working | Paginated, per-user |
| API key management | Working | Create, list, revoke |
| Feedback collection | Working | User corrections stored |

### What Needs Work

| Gap | Impact | Priority |
|-----|--------|----------|
| Wire correction page into app | Final step of Phase 2 | High |
| No Docker setup | Manual installation required | High |
| No test suite | No pytest or Jest tests | Medium |
| No rate limiting | Vulnerable to abuse | Medium |
| No email verification | Users can register fake emails | Low |

### Known Issues

1. **PostgreSQL required**: Database must be running before the API starts.

2. **MinIO required**: Object storage must be running for image uploads to work.

3. **Model weights not in repo**: The .pth files are too large for git (957 MB). Download from [Google Drive](https://drive.google.com/open?id=1Ke3eAYalUU4NAxsqJ6wSWT1xtUHZH2qx).

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.115+ | Web framework |
| Uvicorn | 0.30+ | ASGI server |
| SQLAlchemy | 2.0+ | ORM (async) |
| Alembic | 1.13+ | Database migrations |
| PostgreSQL | 15+ | Primary database |
| MinIO | Latest | S3-compatible object storage |
| PyTorch | 2.0+ | Deep learning framework |
| Transformers | 4.50+ | HuggingFace model hub |
| Pillow | 10.0+ | Image processing |
| pwdlib | 0.2+ | Argon2 password hashing |
| PyJWT | 2.8+ | JWT tokens |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2 | UI framework |
| Vite | 5.0 | Build tool |
| React Router | 7.13 | Client-side routing |

### ML Model

| Model | Source | License |
|-------|--------|---------|
| RT-DETRv4 (D-FINE) | RT-DETRs/RT-DETRv4 | Apache 2.0 |
| RT-DETR v2 | PekingU/rtdetr_r101vd | Apache 2.0 |

---

## Directory Structure

```
CFU-Counter/
|
+-- api/                        # Backend (FastAPI)
|   +-- main.py                 # App entry point
|   +-- config.py               # Environment settings
|   +-- routers/                # API endpoints
|   +-- auth/                   # Authentication module
|   +-- db/                     # Database models
|   +-- services/               # ML inference
|   +-- storage/                # S3/MinIO client
|   +-- schemas/                # Pydantic models
|   +-- requirements.txt        # Python dependencies
|
+-- frontend/                   # Frontend (React)
|   +-- src/
|   |   +-- App.jsx             # Root component
|   |   +-- pages/              # Page components
|   |   +-- components/         # Reusable components
|   |   +-- context/            # React context
|   |   +-- services/           # API client
|   |   +-- utils/              # Helper functions
|   +-- package.json            # Node dependencies
|   +-- vite.config.js          # Vite configuration
|
+-- research/                   # Archived experiments (not for production)
|   +-- cnn/                    # CNN regression model
|   +-- yolo/                   # YOLOv8 experiments (AGPL)
|   +-- rtdetr_v2/              # RT-DETR v2 fine-tuning (HuggingFace-based)
|
+-- rtdetr_v4/                  # RT-DETRv4 official implementation (current focus)
|   +-- configs/                # Model and dataset configs
|   |   +-- dfine/              # D-FINE model configs (inc. AGAR single-class)
|   |   +-- dataset/            # Dataset configs (COCO, AGAR)
|   +-- engine/                 # Core training engine
|   +-- tools/                  # Training and evaluation utilities
|   |   +-- convert_agar_to_coco.py     # AGAR to COCO format converter
|   |   +-- evaluate_count_accuracy.py  # Count accuracy evaluation
|   |   +-- train_yolov8_baseline.py    # YOLOv8 baseline (research only)
|   |   +-- runpod_train.sh             # End-to-end RunPod training workflow
|   |   +-- restage_single_class.sh     # Re-stage data for single-class
|   |   +-- stage_agar_data.sh          # Stage data for RunPod upload
|   +-- train.py                # Main training script
|   +-- requirements.txt        # Dependencies
|
+-- shared/                     # Shared utilities
|   +-- dataset.py              # Dataset loading
|   +-- constants.py            # Class definitions
|
+-- alembic/                    # Database migrations
|   +-- versions/               # Migration files
|
+-- dataset/                    # Training data (not in repo)
|   +-- images/
|   +-- annotations/
|
+-- .env                        # Environment variables
+-- alembic.ini                 # Alembic config
+-- LICENSES.md                 # License compliance
+-- CLAUDE.md                   # AI assistant instructions
```

---

## Setup Guide

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- PostgreSQL 15 or higher
- MinIO (or AWS S3)
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/AnirudhDesai777/CFU-Counter.git
cd CFU-Counter
```

### Step 2: Set Up PostgreSQL

Option A: Using Docker (recommended)

```bash
docker run -d \
  --name cfu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=cfu_counter \
  -p 5432:5432 \
  postgres:15
```

Option B: Local installation

```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb cfu_counter
```

### Step 3: Set Up MinIO

```bash
docker run -d \
  --name cfu-minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

Access MinIO console at http://localhost:9001 (minioadmin/minioadmin)

### Step 4: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r api/requirements.txt
```

### Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```env
# All variables require CFU_ prefix (see api/config.py)

# Database
CFU_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cfu_counter

# Object Storage
CFU_S3_ENDPOINT_URL=http://localhost:9000
CFU_S3_ACCESS_KEY=minioadmin
CFU_S3_SECRET_KEY=minioadmin

# Authentication
CFU_JWT_SECRET_KEY=your-super-secret-key-change-in-production

# Optional: Email (for password reset)
CFU_MAIL_USERNAME=your-email@gmail.com
CFU_MAIL_PASSWORD=your-app-password
CFU_MAIL_FROM=your-email@gmail.com
CFU_MAIL_SERVER=smtp.gmail.com
CFU_MAIL_PORT=587
```

### Step 6: Run Database Migrations

```bash
# From project root
alembic upgrade head
```

This creates the following tables:
- `users` - User accounts
- `predictions` - Prediction metadata
- `feedback` - User corrections (legacy count feedback)
- `corrections` - User correction actions (add/remove/adjust/split with box coordinates)
- `api_keys` - API key management

### Step 7: Set Up Frontend

```bash
cd frontend
npm install
```

### Step 8: Start the Services

Terminal 1 - Backend:
```bash
# From project root, with venv activated
python -m api.main
# or
uvicorn api.main:app --reload --port 8000
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

### Step 9: Access the Application

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

---

## API Reference

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_device": "mps"
}
```

### Authentication

#### Register
```
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

#### Login
```
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

Sets HttpOnly cookie with JWT token.

#### Logout
```
POST /api/auth/logout
```

Clears the authentication cookie.

#### Forgot Password
```
POST /api/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### Reset Password
```
POST /api/auth/reset-password
Content-Type: application/json

{
  "token": "reset-token-from-email",
  "new_password": "newpassword123"
}
```

### Colony Detection

#### Predict
```
POST /api/predict
Content-Type: multipart/form-data

image: [binary file]
confidence_threshold: 0.5 (optional, default 0.5)
```

Response:
```json
{
  "prediction_id": 42,
  "count": 127,
  "detections": [
    {
      "box": [100.5, 200.3, 150.2, 250.8],
      "confidence": 0.95
    }
  ],
  "annotated_image": "data:image/jpeg;base64,/9j/4AAQ...",
  "model_used": "rtdetr",
  "processing_time_ms": 1250
}
```

### Corrections

#### Save Corrections
```
POST /api/corrections
Content-Type: application/json

{
  "prediction_id": 42,
  "actions": [
    {"action_type": "add", "box": [100, 200, 130, 230]},
    {"action_type": "remove", "original_box": [50, 60, 80, 90]},
    {"action_type": "adjust", "original_box": [10, 20, 40, 50], "box": [12, 22, 42, 52]},
    {"action_type": "split", "original_box": [100, 100, 200, 200]}
  ]
}
```

Response:
```json
{
  "corrected_count": 128
}
```

#### Get Correction Summary
```
GET /api/corrections/{prediction_id}
```

Response:
```json
{
  "prediction_id": 42,
  "original_count": 127,
  "corrected_count": 128,
  "actions": {"add": 3, "remove": 1, "adjust": 2, "split": 1}
}
```

### User History

#### Get Prediction History
```
GET /api/history?page=1&size=10
Authorization: (via cookie)
```

Response:
```json
{
  "items": [
    {
      "id": 42,
      "total_count": 127,
      "model_type": "rtdetr",
      "created_at": "2025-01-25T10:30:00Z",
      "original_image_url": "https://...",
      "annotated_image_url": "https://..."
    }
  ],
  "total": 50,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

### Feedback

#### Submit Feedback
```
POST /api/feedback
Content-Type: application/json

{
  "prediction_id": 42,
  "actual_count": 125,
  "comments": "Missed 2 colonies in the corner"
}
```

### Account Management

#### Change Password
```
PUT /api/account/password
Content-Type: application/json
Authorization: (via cookie)

{
  "current_password": "oldpassword",
  "new_password": "newpassword123"
}
```

### API Keys

#### Create API Key
```
POST /api/api-keys
Content-Type: application/json
Authorization: (via cookie)

{
  "name": "My Script"
}
```

Response:
```json
{
  "id": 1,
  "name": "My Script",
  "key": "cfu_a1b2c3d4...full_key_shown_once",
  "prefix": "cfu_a1b2c3d4",
  "created_at": "2025-01-25T10:30:00Z"
}
```

#### List API Keys
```
GET /api/api-keys
Authorization: (via cookie)
```

#### Revoke API Key
```
DELETE /api/api-keys/{key_id}
Authorization: (via cookie)
```

---

## Database Schema

### Entity Relationship Diagram

```
+----------------+       +------------------+       +-------------+
|     users      |       |   predictions    |       |  feedback   |
+----------------+       +------------------+       +-------------+
| id (PK)        |<--+   | id (PK)          |<------| id (PK)     |
| email          |   |   | user_id (FK)?    |       | prediction_id (FK)
| hashed_password|   +-->| image_hash       |       | actual_count|
| is_active      |       | colony_count     |       | comments    |
| is_verified    |       | confidence_thresh|       | created_at  |
| created_at     |       | model_used       |       +-------------+
+-------+--------+       | original_image_key
        |                | annotated_image_key
        |                | created_at       |
        |                +------------------+
        |
        |            +----------------+
        +----------->|   api_keys     |
                     +----------------+
                     | id (PK)        |
                     | user_id (FK)   |
                     | key_hash       |
                     | name           |
                     | prefix         |
                     | is_active      |
                     | last_used_at   |
                     | created_at     |
                     +----------------+
```

### Table Details

#### users
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Unique identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login email |
| hashed_password | VARCHAR(255) | NOT NULL | Argon2 hash |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| is_verified | BOOLEAN | DEFAULT FALSE | Email verified |
| created_at | TIMESTAMP | NOT NULL | Registration time |

#### predictions
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Unique identifier |
| user_id | INTEGER | FK(users), NULL | Owner (nullable for anonymous) |
| image_hash | VARCHAR(64) | INDEX | SHA256 of original image |
| colony_count | INTEGER | NOT NULL | Detected count |
| confidence_threshold | FLOAT | NOT NULL | Detection threshold used |
| model_used | VARCHAR(50) | NOT NULL | Model identifier |
| original_image_key | VARCHAR(255) | NOT NULL | S3 key for original |
| annotated_image_key | VARCHAR(255) | NULL | S3 key for annotated |
| created_at | TIMESTAMP | NOT NULL | Prediction time |

#### feedback
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Unique identifier |
| prediction_id | INTEGER | FK(predictions), CASCADE | Related prediction |
| actual_count | INTEGER | NOT NULL | User-corrected count |
| comments | VARCHAR(500) | NULL | User notes |
| created_at | TIMESTAMP | NOT NULL | Feedback time |

#### api_keys
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Unique identifier |
| user_id | INTEGER | FK(users), CASCADE | Owner |
| key_hash | VARCHAR(64) | UNIQUE | SHA256 of full key |
| name | VARCHAR(100) | NOT NULL | User-provided name |
| prefix | VARCHAR(20) | NOT NULL | First 12 chars (cfu_xxxxxxxx) |
| is_active | BOOLEAN | DEFAULT TRUE | Key status |
| last_used_at | TIMESTAMP | NULL | Last API call |
| created_at | TIMESTAMP | NOT NULL | Creation time |

---

## ML Models

### Model Tracks

This project uses a dual-track model strategy to comply with licensing requirements:

```
+------------------------+     +---------------------------+
|    RESEARCH TRACK      |     |    COMMERCIAL TRACK       |
+------------------------+     +---------------------------+
| Purpose: Benchmarking  |     | Purpose: Production       |
| License: AGPL/CC BY-NC |     | License: Apache 2.0       |
+------------------------+     +---------------------------+
|                        |     |                           |
| - YOLOv8 (Ultralytics) |     | - RT-DETR                 |
| - AGAR dataset         |     | - CC BY 4.0 datasets only |
| - CNN experiments      |     | - Fine-tuned weights      |
|                        |     |                           |
+------------------------+     +---------------------------+
        |                              |
        v                              v
  Internal use only            Production deployment
  Cannot serve over network    Safe for SaaS
```

### Current Model Status

| Model | Integration | Training | Production Ready |
|-------|-------------|----------|------------------|
| RT-DETRv4 (D-FINE) | Complete | Fine-tuned, mAP 0.639 | Research only (CC BY-NC data) |
| RT-DETR v2 | Archived | Scripts available | No (needs fine-tuning) |
| YOLOv8 | Research only | Complete | No (AGPL) |
| CNN | Research only | Complete | No |

**Note:** Models trained on AGAR dataset are for research use only due to CC BY-NC 2.0 license. For production, retrain on CC BY 4.0 licensed data.

### RT-DETRv4 D-FINE (Fine-Tuned)

**What it is:** D-FINE is a state-of-the-art real-time object detector from the RT-DETRv4 family using HGNetv2 backbone. It achieves 57.0 AP on COCO at 78 FPS.

**Training results:** D-FINE HGNetv2-X fine-tuned on AGAR dataset with single-class "colony" detection (all 7 species merged into 1 class). Trained on 4x A40 GPUs via RunPod.

| Metric | YOLOv8 | D-FINE |
|--------|--------|--------|
| mAP@0.5:0.95 | 0.622 | 0.639 |
| Training time | N/A | ~2 hours (4x A40) |
| Batch size | N/A | 24 (total across GPUs) |

**Google Drive assets:** [CFU-counter-training folder](https://drive.google.com/open?id=1Ke3eAYalUU4NAxsqJ6wSWT1xtUHZH2qx)

| Asset | Size | Direct Link |
|-------|------|-------------|
| Training data (`cfu_training_data.tar`) | 12.45 GB | In folder above |
| Best weights (`dfine_hgnetv2_x_agar_1cls_best.pth`) | 957 MB | [Download](https://drive.google.com/open?id=1DphRoTFaEnzK-xKYYufNZZQNvLj4XDKC) |

Place weights in `rtdetr_v4/weights/` after downloading.

**Re-training (if needed):**

```bash
cd rtdetr_v4

# Single GPU
python train.py -c configs/dfine/dfine_hgnetv2_x_agar.yml \
    -t pretrain/dfine_hgnetv2_x_coco.pth

# Multi-GPU DDP (4x GPUs) -- note the NCCL env vars for RunPod
NCCL_P2P_DISABLE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
torchrun --nproc_per_node=4 train.py \
    -c configs/dfine/dfine_hgnetv2_x_agar.yml \
    -t pretrain/dfine_hgnetv2_x_coco.pth
```

**Key configuration notes:**
- Uses `epoches` (intentional typo in the framework), NOT `epochs`
- `total_batch_size` is total across all GPUs, NOT per-GPU
- `num_classes: 1` must be set in 3 places: DFINETransformer, RTv4Criterion, agar_detection.yml
- `remap_mscoco_category: False` for 0-indexed category IDs
- `NCCL_P2P_DISABLE=1` required on RunPod A40 pods (NUMA topology causes DDP hang)
- Batch size 24 is safe for 4x A40 at 1024px with AMP; 32 causes OOM

See `CLAUDE.md` for full configuration details.

### YOLOv8 (Research Baseline)

**Performance on AGAR dataset:**

| Metric | Score |
|--------|-------|
| mAP@.5:.95 | 0.622 |
| Precision | 0.981 |
| Recall | 0.966 |
| Exact count accuracy | 69.49% |
| Count accuracy within 5% | 88.73% |

**Why not in production:** AGPL-3.0 license requires open-sourcing the entire application if used in a network service.

### CNN (Research Model)

**Architecture:**
```
Input (224x224 RGB)
    |
    v
[Conv Block x5] --> BatchNorm --> ReLU --> MaxPool
    |
    v
[Flatten]
    |
    +---> [Regression Head] --> Colony Count (MSE loss)
    |
    +---> [Classification Head] --> Species (CrossEntropy loss)
```

**Use case:** Lightweight counting without per-colony localization.

---

## Research Background

### The Problem

Colony Forming Unit (CFU) counting is fundamental in microbiology:
- Antibiotic susceptibility testing
- Water quality monitoring
- Food safety testing
- Pharmaceutical quality control

Traditional counting is done manually, which is:
- Time-consuming (5-10 min per plate)
- Subjective (inter-observer variability)
- Fatiguing (hundreds of plates per day)

### Dataset: AGAR

The AGAR dataset (Annotated Germs for Automated Recognition) contains:

| Statistic | Value |
|-----------|-------|
| Total images | 18,000 |
| Total colonies | 336,442 |
| Species classes | 7 |
| License | CC BY-NC 2.0 |

**Classes:**
1. *B. subtilis* (Bacillus subtilis)
2. *C. albicans* (Candida albicans)
3. *E. coli* (Escherichia coli)
4. *P. aeruginosa* (Pseudomonas aeruginosa)
5. *S. aureus* (Staphylococcus aureus)
6. Contamination
7. Defect

**Annotation format:**
```json
{
  "colonies_number": 127,
  "classes": ["E.coli"],
  "labels": [
    {
      "x": 100, "y": 200,
      "width": 50, "height": 50,
      "class": "E.coli"
    }
  ]
}
```

### Approaches

**Regression (CNN):** Predict total count directly from image. Simple but no localization.

**Object Detection (YOLO, RT-DETR):** Detect each colony as a bounding box. Count = number of detections. Provides localization and handles mixed cultures.

### Error Sources

| Error Type | Cause | Mitigation |
|------------|-------|------------|
| Confluence | Overlapping colonies merge | Higher resolution, segmentation |
| Low contrast | Colonies blend with agar | Better lighting, preprocessing |
| Edge artifacts | Petri dish rim reflections | Dish masking |
| Class imbalance | Rare species underrepresented | Focal loss, oversampling |

---

## Development Workflow

### Running Tests

```bash
# Backend (when tests exist)
pytest api/tests/

# Frontend (when tests exist)
cd frontend && npm test
```

### Code Style

Backend:
```bash
# Format
black api/
ruff format api/

# Lint
ruff check api/
```

Frontend:
```bash
cd frontend
npm run lint
```

### Database Migrations

Creating a new migration:
```bash
alembic revision -m "describe_your_change"
```

Applying migrations:
```bash
alembic upgrade head
```

Rolling back:
```bash
alembic downgrade -1
```

### Adding a New API Endpoint

1. Create router in `api/routers/newfeature.py`
2. Add Pydantic schemas in `api/schemas/`
3. Register router in `api/main.py`
4. Update this README

### Git Workflow

```bash
# Feature branch
git checkout -b feature/description

# Make changes, commit atomically
git add specific_file.py
git commit -m "feat: add specific feature"

# Push and create PR
git push -u origin feature/description
```

Commit prefixes:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code restructuring
- `test:` Adding tests
- `chore:` Maintenance

---

## License Compliance

### Summary

| Track | Components | License | Restrictions |
|-------|------------|---------|--------------|
| Research | YOLOv8, AGAR dataset | AGPL-3.0, CC BY-NC 2.0 | No production use |
| Commercial | RT-DETR, FastAPI, React | Apache 2.0, MIT | Attribution required |

### Key Rules

1. **Never import `ultralytics` in production code** - AGPL requires open-sourcing
2. **Never train production models on AGAR** - CC BY-NC prohibits commercial use
3. **Include attribution notices** for Apache 2.0 and MIT libraries
4. **Use CC BY 4.0 datasets** for production model training (e.g., Veterinary dataset)

See [LICENSES.md](./LICENSES.md) for full details.

---

## Troubleshooting

### "Model not loaded" error

The D-FINE model weights must be in `rtdetr_v4/weights/`. Download from [Google Drive](https://drive.google.com/open?id=1DphRoTFaEnzK-xKYYufNZZQNvLj4XDKC) and place as `rtdetr_v4/weights/dfine_hgnetv2_x_agar_1cls_best.pth`.

### Database connection refused

Ensure PostgreSQL is running:
```bash
# Docker
docker ps | grep postgres

# Local
pg_isready -h localhost -p 5432
```

### MinIO bucket not found

The API creates the bucket automatically on startup. If issues persist:
```bash
# Access MinIO console at http://localhost:9001
# Login: minioadmin / minioadmin
# Create bucket manually: cfu-counter
```

### CORS errors in browser

Check that backend CORS settings include frontend origin:
```python
# api/config.py
CORS_ORIGINS = ["http://localhost:3000"]
```

### JWT token errors

Ensure `JWT_SECRET_KEY` is set in `.env`. Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with atomic commits
4. Ensure code passes linting
5. Submit a pull request

---

## Citation

If you use this project in research, please cite:

```bibtex
@software{cfu_counter,
  title = {CFU-Counter: Automated Colony Counting},
  year = {2025},
  url = {https://github.com/AnirudhDesai777/CFU-Counter}
}
```

And the AGAR dataset:

```bibtex
@article{majchrowska2021agar,
  title={AGAR a microbial colony dataset for deep learning detection},
  author={Majchrowska, Sylwia and others},
  journal={Scientific Data},
  year={2021}
}
```

---

## Acknowledgments

- AGAR dataset by NeuroSYS
- RT-DETR by Peking University
- YOLOv8 by Ultralytics

---

*Last updated: 2026-02-15*
