# IntelliOptics: Kubernetes → Nginx-Based Edge Deployment

## Overview

Convert the current Kubernetes-based IntelliOptics deployment to a lightweight, nginx-based edge deployment with detector-centric architecture following the Groundlight design pattern.

## Engineering Diagrams Analysis

Based on the diagrams in `C:\Dev\IntelliOpticsDev\IntelliOptics-Edge-clean\images\`:

### Current K8s Architecture (Diagram 1 & 2):
- **nginx:30101** → Entry point with cloud fallback on 404
- **Edge Endpoint:8718** → Main orchestrator, decision logic
- **Status Monitor:8123** → Stats collection, uploads to cloud
- **Inference Model Updater** → Downloads models, creates K8s pods dynamically
- **Dynamic Inference Pods** → Separate pods per detector (Primary + OODD)

### Happy Path Flow (Diagram 3):
```
POST /image-queries →
  want_async? → Send to cloud
  require human review? → Send to cloud
  inference available? → 503 if No
  ✓ Do local inference (GREEN - Happy Path)
  confidence >= threshold? → Return local result immediately ✓
  confidence < threshold AND escalation allowed? → Escalate to central web app
  audit sample? → Async send to cloud (rare, for model improvement)
```

**Key Point**: Most images are processed on edge and returned directly. Only questionable results (confidence < threshold) are escalated for human review.

### Docker Compose Adaptation:
- **Keep**: nginx gateway, Edge Endpoint logic, confidence-based escalation
- **Replace**: Dynamic pod creation → Static inference service with model caching
- **Simplify**: Status Monitor can be integrated or separate container
- **Add**: Central web application for human escalation/review

## New Folder Structure

```
C:\Dev\intellioptics-edge-deploy\
├── edge\                          # Edge deployment
│   ├── docker-compose.yml         # Main edge compose file
│   ├── .env.template              # Template for edge env vars
│   ├── nginx\
│   │   ├── Dockerfile
│   │   └── nginx.conf             # Port 30101 gateway config
│   ├── edge-api\
│   │   ├── Dockerfile
│   │   ├── app\                   # Copied from IntelliOptics-Edge-clean/app
│   │   │   ├── main.py
│   │   │   ├── api\routes\image_queries.py
│   │   │   ├── core\edge_inference.py
│   │   │   └── streaming\rtsp_ingest.py
│   │   └── requirements.txt
│   ├── inference\
│   │   ├── Dockerfile
│   │   ├── inference_service.py   # Multi-detector ONNX service
│   │   └── requirements.txt
│   ├── config\
│   │   └── edge-config.yaml       # Detector configurations
│   └── scripts\
│       ├── deploy-edge.sh
│       └── init-models.sh
│
├── cloud\                          # Central web application
│   ├── docker-compose.yml
│   ├── .env.template
│   ├── backend\
│   │   ├── Dockerfile
│   │   ├── app\                   # Copied from intellioptics_platform_no_auth/backend
│   │   │   ├── main.py
│   │   │   ├── routers\
│   │   │   │   ├── detectors.py
│   │   │   │   ├── queries.py
│   │   │   │   └── escalations.py
│   │   │   └── utils\azure.py
│   │   └── requirements.txt
│   ├── frontend\                   # Web UI for human review
│   │   ├── Dockerfile
│   │   ├── src\
│   │   │   ├── pages\ReviewQueue.tsx
│   │   │   └── pages\Detectors.tsx
│   │   └── package.json
│   ├── worker\
│   │   ├── Dockerfile
│   │   └── inference_worker.py
│   └── nginx\
│       ├── Dockerfile
│       └── nginx.conf             # Routes to backend + frontend
│
└── apim\                           # Azure APIM backend only
    ├── docker-compose.yml
    ├── .env.template
    └── backend\
        ├── Dockerfile
        └── app\                    # Same as cloud/backend
```

## Architecture

### Target: Docker Compose Edge Deployment (matches diagrams)

```
┌─────────────────────────────────────────────────────────┐
│                  Edge Device                            │
│                                                         │
│  Client → nginx:30101 ──┬─ Success → edge-api:8718    │
│                         └─ 404 → Central Web App       │
│                                                         │
│  edge-api:8718 (Edge Endpoint)                         │
│    ↓                                                    │
│  inference:8001 (Multi-detector ONNX)                  │
│    ├─ Primary models                                   │
│    └─ OODD models                                      │
│                                                         │
│  postgres:5432 (optional - detector metadata)          │
│                                                         │
│  Volumes:                                              │
│   - /opt/intellioptics/models  (ONNX .buf files)      │
│   - /opt/intellioptics/config  (edge-config.yaml)     │
└─────────────────────────────────────────────────────────┘
         │
         │ (Escalation: low confidence, human review)
         ↓
┌─────────────────────────────────────────────────────────┐
│         Central Web Application (Cloud/APIM)           │
│                                                         │
│  nginx:80/443 → backend:8000 (API)                     │
│              → frontend:3000 (React UI)                │
│                                                         │
│  backend:8000 (FastAPI)                                │
│    ├─ /detectors  (CRUD)                               │
│    ├─ /queries    (Submit, Get)                        │
│    ├─ /escalations (Review queue)                      │
│    └─ /hubs       (Edge device management)             │
│                                                         │
│  frontend:3000 (React)                                 │
│    ├─ Review Queue (Human labeling)                    │
│    ├─ Detector Management                              │
│    └─ Edge Device Dashboard                            │
│                                                         │
│  worker:8001 (Inference worker for cloud-side)         │
│                                                         │
│  postgres:5432 (Central database)                      │
│    ├─ users, detectors, queries                        │
│    ├─ escalations (review queue)                       │
│    └─ hubs (edge devices)                              │
│                                                         │
│  Azure Integrations:                                   │
│    ├─ Blob Storage (images, models)                    │
│    ├─ Service Bus (optional queuing)                   │
│    └─ APIM (optional API gateway)                      │
└─────────────────────────────────────────────────────────┘
```

### Key Principles (from API Doc/Groundlight Design):

1. **Detector-Centric**: Detectors are the main control object
2. **Confidence-Based Escalation**: High confidence → edge; Low confidence → cloud/human
3. **Continuous Learning**: Escalated cases retrain models, pushed to edge
4. **Edge Efficiency**: Small models, low latency, reduced cost

## EXECUTION PLAN: IntelliOptics 2.0 Clean Build

**IMPORTANT**: Copy files to new folder first, then edit copies (never overwrite originals)

### Step 1: Create Clean Folder Structure

```bash
# Create IntelliOptics 2.0 root
mkdir "C:\Dev\IntelliOptics 2.0"

# Create main structure
mkdir "C:\Dev\IntelliOptics 2.0\edge"
mkdir "C:\Dev\IntelliOptics 2.0\cloud"
mkdir "C:\Dev\IntelliOptics 2.0\hrm-training"
mkdir "C:\Dev\IntelliOptics 2.0\docs"

# Edge structure
mkdir "C:\Dev\IntelliOptics 2.0\edge\nginx"
mkdir "C:\Dev\IntelliOptics 2.0\edge\edge-api"
mkdir "C:\Dev\IntelliOptics 2.0\edge\edge-api\app"
mkdir "C:\Dev\IntelliOptics 2.0\edge\inference"
mkdir "C:\Dev\IntelliOptics 2.0\edge\config"
mkdir "C:\Dev\IntelliOptics 2.0\edge\scripts"

# Cloud structure
mkdir "C:\Dev\IntelliOptics 2.0\cloud\backend"
mkdir "C:\Dev\IntelliOptics 2.0\cloud\backend\app"
mkdir "C:\Dev\IntelliOptics 2.0\cloud\frontend"
mkdir "C:\Dev\IntelliOptics 2.0\cloud\worker"
mkdir "C:\Dev\IntelliOptics 2.0\cloud\nginx"

# HRM training structure
mkdir "C:\Dev\IntelliOptics 2.0\hrm-training\dataset"
mkdir "C:\Dev\IntelliOptics 2.0\hrm-training\scripts"
mkdir "C:\Dev\IntelliOptics 2.0\hrm-training\models"
```

### Step 2: Copy Source Files (No Overwriting)

```bash
# Copy Edge API source (from existing codebase)
cp -r "C:\Dev\IntelliOpticsDev\IntelliOptics-Edge-clean\app" "C:\Dev\IntelliOptics 2.0\edge\edge-api\"

# Copy Cloud Backend source
cp -r "C:\Dev\intellioptics_platform_no_auth\backend\app" "C:\Dev\IntelliOptics 2.0\cloud\backend\"

# Copy Cloud Frontend source
cp -r "C:\Dev\intellioptics_platform_no_auth\frontend" "C:\Dev\IntelliOptics 2.0\cloud\"

# Copy Inference Worker source
cp -r "C:\Dev\IntelliOpticsDev\IntelliOptics-Edge-clean\backend\worker" "C:\Dev\IntelliOptics 2.0\cloud\"

# Copy nginx config template
cp "C:\Dev\IntelliOpticsDev\IntelliOptics-Edge-clean\deploy\helm\intellioptics-edge-endpoint\intellioptics-edge-endpoint\files\nginx.conf" "C:\Dev\IntelliOptics 2.0\edge\nginx\"

# Copy docs
cp "C:\Users\ThaMain1\.claude\plans\snazzy-stirring-dahl.md" "C:\Dev\IntelliOptics 2.0\docs\ARCHITECTURE.md"
cp "C:\Users\ThaMain1\.claude\plans\HRM-Training-Guide.md" "C:\Dev\IntelliOptics 2.0\docs\HRM-TRAINING.md"
```

### Step 3: Modify Copied Files (Safe - Won't Touch Originals)

### Phase 2: Edge Services

#### 2.1 Create docker-compose.yml (Edge)
- Services: nginx, edge-api, inference, postgres (optional)
- Networks: edge-net (bridge)
- Volumes: models, edge_data, postgres_data, nginx_logs
- Health checks for all services
- **File location**: `C:\dev\docker-compose.edge.yml`

#### 1.2 Build Edge API Container
- **Base code**: `C:\dev\IntelliOpticsDev\IntelliOptics-Edge-clean\app\`
- **Key files to modify**:
  - `app/api/routes/image_queries.py` - Update inference URLs from K8s to `http://inference:8001`
  - `app/core/edge_inference.py` - Replace K8s service discovery with static URLs
  - `app/main.py` - Remove K8s scheduler, simplify startup
- **Remove**: `app/core/kubernetes_management.py`
- **Config**: Load from `/config/edge-config.yaml` (volume-mounted)
- **Dockerfile**: `C:\dev\edge-api\Dockerfile`

#### 1.3 Build Inference Service
- **Base code**: `C:\dev\IntelliOpticsDev\IntelliOptics-Edge-clean\backend\worker\onnx_worker.py`
- **Modifications needed**:
  - Add `detector_id` query parameter routing
  - Implement model caching (LRU, 5 models max)
  - Load models from `/models/{detector_id}/primary/{version}/model.buf`
  - Add health endpoint on port 8081
- **API**: `POST /infer?detector_id=det_abc123` with image bytes
- **Response**: `{confidence, label, rois, text, ...}`
- **Dockerfile**: `C:\dev\inference\Dockerfile`

#### 1.4 Configure nginx
- **Base template**: `C:\dev\IntelliOpticsDev\IntelliOptics-Edge-clean\deploy\helm\intellioptics-edge-endpoint\intellioptics-edge-endpoint\files\nginx.conf`
- **Routing**:
  - `/v1/*` → edge-api:8000
  - Error codes 404, 422, 503 → @cloud_fallback
  - @cloud_fallback → https://intellioptics-api-37558.azurewebsites.net
- **Config file**: `C:\dev\nginx\nginx.conf`

#### 1.5 Create Edge Configuration
- **File**: `C:\dev\config\edge-config.yaml`
- **Contents**:
  - global_config (refresh_rate, audit_rate)
  - edge_inference_configs (default, offline)
  - detectors (detector_id, edge_inference_config)
  - streams (RTSP camera configurations)
- **Example detector**:
  ```yaml
  detectors:
    det_abc123:
      detector_id: det_abc123
      edge_inference_config: default
      confidence_threshold: 0.85
      mode: BINARY
  ```

### Phase 2: APIM Backend

#### 2.1 Create docker-compose.apim.yml
- Services: apim-backend, apim-db, apim-worker
- Networks: apim-net
- Volumes: apim_db_data
- **File location**: `C:\dev\docker-compose.apim.yml`

#### 2.2 Build APIM Backend Container
- **Base code**: `C:\dev\intellioptics_platform_no_auth\backend\`
- **Reuse as-is**:
  - `app/routers/detectors.py` - Detector CRUD
  - `app/routers/queries.py` - Image query processing
  - `app/routers/escalations.py` - Escalation handling
  - `app/utils/azure.py` - Blob Storage, Service Bus
- **Dockerfile**: `C:\dev\apim-backend\Dockerfile`
- **Endpoints**: `/detectors`, `/queries`, `/escalations`, `/hubs`

#### 2.3 Database Schema
- **Base**: `C:\dev\intellioptics_platform_no_auth\backend\app\models.py`
- **Tables**: users, detectors, queries, escalations, hubs, feedback
- **Auto-create on startup**: Alembic migrations or SQLAlchemy `create_all()`

### Phase 3: Detector-Centric Flow (from Diagram 3)

#### 3.1 Image Query Processing - Happy Path
**Flow** (matches engineering diagram):
1. Request: `POST /v1/image-queries?detector_id=det_abc123`
2. nginx:30101 → edge-api:8718
3. edge-api decision tree:
   - **want_async?** → Yes: Send to central web app, return async
   - **require human review?** → Yes: Send to central web app, return sync
   - **inference server available?** → No: Return 503 error
   - ✅ **Do local inference** (call inference:8001)
     - **Run Primary model** → Get label + raw_confidence
     - **Run OODD model** (ground truth) → Detect if image is in-domain or out-of-domain
     - **Adjust confidence** based on OODD:
       - If OODD says "in-domain" → Use raw_confidence
       - If OODD says "out-of-domain" → Reduce confidence (or set to 0) → **Triggers escalation**
     - **Final confidence** = Primary confidence × OODD in-domain score
   - **confidence >= threshold?** → **Yes: Return local result immediately** (DONE - most common case)
   - **confidence < threshold AND escalation allowed?** → Yes: Escalate to central web app
     - Out-of-domain images automatically escalated (low confidence after OODD adjustment)
   - **audit sample?** → Yes: Async send to central web app (rare, for model improvement)

**OODD Ground Truth**: The OODD model acts as a "gatekeeper" - if it detects the image is out-of-domain (e.g., different lighting, new object type, unexpected scenario), it forces escalation even if the Primary model was confident.

#### 3.2 Escalation Workflow (only for questionable images)
**Trigger**: `confidence < detector.confidence_threshold AND escalation_allowed = true`

**Steps**:
1. Upload image to Azure Blob or central web app storage
2. Send escalation request:
   - HTTP: `POST https://central-web-app.example.com/api/v1/escalations`
   - Include: detector_id, image_url, edge_result, confidence
3. Central web app:
   - Adds to human review queue
   - Notifies reviewers
   - Human labels the image
   - Stores labeled result in database
4. Model retraining (periodic, cloud-side):
   - Collect all human-labeled escalations
   - Retrain detector model
   - Create new model version
   - Edge devices download new model on next refresh (60s interval)
5. Edge device receives updated result (optional):
   - Webhook callback from central web app
   - Or edge polls for updates on escalated queries

#### 3.2 Escalation Workflow
**Trigger**: `confidence < detector.confidence_threshold`

**Steps**:
1. Upload image to Azure Blob (generate SAS URL)
2. Send escalation message:
   - HTTP: `POST https://intellioptics-api-37558.azurewebsites.net/v1/image-queries`
   - Service Bus: Send to `image-queries` queue
3. Cloud processes:
   - Run full model or send to human review
   - Return result via webhook or polling
4. Model retraining (cloud-side):
   - Add escalated case to training dataset
   - Retrain model, create new version
   - Edge devices download new model on next refresh

#### 3.3 Model Management (Primary + OODD per detector)
**Directory structure** (from Diagram 2):
```
/opt/intellioptics/models/
├── det_abc123/
│   ├── primary/               # Main detection model
│   │   ├── 1/
│   │   │   ├── model.buf      # ONNX model file
│   │   │   ├── pipeline_config.yaml
│   │   │   ├── predictor_metadata.json
│   │   │   └── model_id.txt
│   │   └── 2/ (newer version)
│   └── oodd/                  # Out-of-Domain Detection model (ground truth)
│       └── 1/
│           ├── model.buf
│           ├── pipeline_config.yaml
│           └── predictor_metadata.json
└── det_xyz456/...
```

**Inference service logic**:
```python
# inference_service.py handles both models per request

async def infer(detector_id: str, image_bytes: bytes):
    # 1. Load Primary model
    primary_model = load_model(f"/models/{detector_id}/primary/latest/model.buf")

    # 2. Load OODD model (ground truth)
    oodd_model = load_model(f"/models/{detector_id}/oodd/latest/model.buf")

    # 3. Run Primary inference
    primary_result = primary_model.predict(image_bytes)
    raw_confidence = primary_result.confidence
    label = primary_result.label

    # 4. Run OODD inference (ground truth check)
    oodd_result = oodd_model.predict(image_bytes)
    in_domain_score = oodd_result.in_domain_confidence  # 0.0 to 1.0

    # 5. Adjust confidence based on OODD ground truth
    final_confidence = raw_confidence * in_domain_score

    return {
        "label": label,
        "confidence": final_confidence,
        "raw_primary_confidence": raw_confidence,
        "oodd_in_domain_score": in_domain_score,
        "is_out_of_domain": in_domain_score < 0.5  # Flag for escalation
    }
```

**Loading strategy**:
1. **Startup**: Check `/opt/intellioptics/models/` for existing models
2. **On-demand**: If detector_id requested but model missing:
   - Call cloud API: `/edge-api/v1/fetch-model-urls/{detector_id}`
   - Download model.buf + config files
   - Save to `/models/{detector_id}/primary/{version}/`
3. **Periodic refresh**: Check for updates every 60 seconds
4. **Caching**: Keep up to 5 models in memory (LRU)

### Phase 4: Deployment

#### 4.1 Edge Deployment
```bash
# Setup
cd C:\dev
cp .env.edge.template .env.edge
# Edit .env.edge with INTELLIOPTICS_API_TOKEN, etc.

# Create volumes
mkdir -p /opt/intellioptics/models
mkdir -p /opt/intellioptics/config

# Deploy
docker-compose -f docker-compose.edge.yml up -d

# Verify
curl http://localhost:30101/health
curl http://localhost:30101/v1/detectors
```

#### 4.2 APIM Backend Deployment
```bash
cd C:\dev
cp .env.apim.template .env.apim
# Edit .env.apim with Azure credentials

docker-compose -f docker-compose.apim.yml up -d

# Verify
curl http://localhost:8000/health
curl http://localhost:8000/detectors
```

## Critical Files

### To Modify:
1. `C:\dev\IntelliOpticsDev\IntelliOptics-Edge-clean\app\api\routes\image_queries.py`
2. `C:\dev\IntelliOpticsDev\IntelliOptics-Edge-clean\app\core\edge_inference.py`
3. `C:\dev\IntelliOpticsDev\IntelliOptics-Edge-clean\backend\worker\onnx_worker.py`

### To Create:
1. `C:\dev\docker-compose.edge.yml`
2. `C:\dev\docker-compose.apim.yml`
3. `C:\dev\nginx\nginx.conf`
4. `C:\dev\config\edge-config.yaml`
5. `C:\dev\edge-api\Dockerfile`
6. `C:\dev\inference\Dockerfile`
7. `C:\dev\apim-backend\Dockerfile`

### To Reuse:
1. `C:\dev\intellioptics_platform_no_auth\backend\` (APIM backend)
2. `C:\dev\IntelliOpticsDev\IntelliOptics-Edge-clean\app\streaming\rtsp_ingest.py` (RTSP)
3. `C:\dev\IntelliOpticsDev\IntelliOptics-Edge-clean\app\core\configs.py` (Pydantic models)

## Technology Stack

- **Container Orchestration**: Docker Compose
- **Reverse Proxy**: nginx 1.25-alpine
- **Edge API**: FastAPI (Python 3.11)
- **Inference**: ONNX Runtime (CPU/GPU)
- **Database**: PostgreSQL 15
- **Configuration**: YAML + Pydantic
- **Cloud Integration**: Azure Blob Storage, Service Bus, APIM

## HRM AI Integration (Advanced Differentiator)

### What is HRM:
**Hierarchical Reasoning Model** from `C:\Users\ThaMain1\HRM`:
- Novel recurrent architecture for complex reasoning
- Only **27M parameters** (very lightweight)
- **1000 training samples** for near-perfect accuracy (vs. 10,000+ for traditional models)
- Two-level hierarchy: High-level planning + Low-level computation
- Trained on: Sudoku, mazes, ARC (AGI benchmark)

### Why HRM Separates from Competition:

1. **Explainable AI** (Unique):
   - Provides reasoning chains, not just labels
   - Example: "Defect because: (1) Crack pattern, (2) Outside tolerance, (3) Similar to critical failures"

2. **Few-Shot Learning** (10x cost savings):
   - Train new detectors with 1000 samples vs. 10,000+
   - Rapid deployment of new inspection tasks

3. **Complex Reasoning** (Beyond detection):
   - Multi-step workflows: "Worker + No Helmet + Near Machinery" = Safety violation
   - Context-aware decisions

4. **Edge-Optimized** (Smaller than YOLO):
   - 27M params vs. 100M+ for YOLO
   - Runs on edge GPUs (Jetson, etc.)

### Integration Strategy:

**Option A: Three-Layer Pipeline** (Recommended)
```
Image → Primary Model (YOLO/ONNX) → Object detection
      → OODD Model → In-domain check (ground truth)
      → HRM Model → Reasoning layer (context, severity, action)
```

**Option B: Escalation Reasoning** (High-value use case)
- HRM decides: "Should this escalate? Why?"
- Learns patterns from historical escalations
- Provides explanations to human reviewers

**Option C: Few-Shot Detector Training** (Competitive advantage)
- Use HRM for rapid training of new detectors (1000 samples)
- Deploy new inspection tasks in hours vs. weeks

### Implementation Path:

**Phase 1** (Current): Deploy nginx-based edge with Primary + OODD (proven, production-ready)

**Phase 2** (Future): Add HRM as optional reasoning layer for:
- Complex multi-step inspection workflows
- Explainable escalation decisions
- Few-shot training of new detectors

### Technical Requirements for HRM:
- **GPU**: CUDA 12.6 + FlashAttention (not CPU-compatible)
- **Retraining**: Adapt HRM for computer vision (currently trained on puzzles)
- **Integration**: Add HRM inference service alongside ONNX service
- **Model**: 27M parameters, PyTorch-based

### HRM Retraining Plan for Computer Vision:

**Challenge**: HRM is trained on discrete grid-based puzzles (Sudoku, mazes), not continuous images.

**Solution**: Vision-to-Grid Encoding + HRM Reasoning

#### Step 1: Data Preparation (1000+ samples needed)
1. **Source**: Escalated images from Phase 1 deployment
   - Images with low confidence
   - Human-labeled ground truth
   - Includes diverse defect types, lighting, angles

2. **Annotation Requirements**:
   - **Image**: Raw inspection image
   - **Ground Truth**: Defect label (binary, multiclass, or bounding box)
   - **Reasoning Chain** (NEW): Why is this a defect?
     - Example: "Defect because: (1) Crack visible at coordinates (x,y), (2) Width exceeds 0.5mm threshold, (3) Located in critical zone"

3. **Data Format Conversion**:
   ```python
   # Convert image to grid representation
   def image_to_grid(image, patch_size=32):
       # Option A: Patch embeddings (like ViT)
       patches = divide_into_patches(image, patch_size)
       grid = encode_patches_to_discrete_tokens(patches)
       return grid  # Shape: (H/patch_size, W/patch_size, token_id)

   # Build dataset
   dataset = {
       "input_grid": grid,  # Encoded image patches
       "target": defect_label,
       "reasoning_steps": [step1, step2, step3]  # Hierarchical reasoning
   }
   ```

#### Step 2: Architecture Adaptation
1. **Add Vision Encoder** (before HRM):
   ```python
   # models/vision_hrm.py
   class VisionHRM(nn.Module):
       def __init__(self):
           self.vision_encoder = ResNet50()  # or EfficientNet, ViT
           self.hrm = HierarchicalReasoningModel()

       def forward(self, image):
           # 1. Extract visual features
           features = self.vision_encoder(image)  # (batch, 2048, H', W')

           # 2. Convert to grid tokens
           grid_tokens = self.feature_to_tokens(features)  # (batch, H', W', vocab_size)

           # 3. HRM reasoning
           reasoning_output = self.hrm(grid_tokens)

           return reasoning_output
   ```

2. **Reasoning Output Adaptation**:
   - HRM outputs: Sequential reasoning steps
   - Map to: Defect classification + Explanation
   ```python
   reasoning_output = {
       "label": "defect",
       "confidence": 0.92,
       "reasoning": [
           "Step 1: Detected anomaly in patch (5,7)",
           "Step 2: Anomaly matches crack pattern",
           "Step 3: Crack exceeds severity threshold"
       ]
   }
   ```

#### Step 3: Training Process (using existing HRM codebase)

**Location**: `C:\Users\ThaMain1\HRM\`

1. **Create Vision Dataset Loader**:
   ```bash
   # New file: C:\Users\ThaMain1\HRM\dataset\build_vision_dataset.py
   python dataset/build_vision_dataset.py \
       --input-dir C:/dev/intellioptics-edge-deploy/data/escalations \
       --output-dir data/intellioptics-inspection-1k \
       --subsample-size 1000
   ```

2. **Adapt Configuration**:
   ```yaml
   # config/arch/vision_hrm.yaml
   input_size: [640, 640]  # Image size
   patch_size: 32  # Grid granularity
   vocab_size: 512  # Discrete tokens for patches
   num_classes: 2  # Binary: defect/no-defect
   reasoning_depth: 3  # Multi-step reasoning
   ```

3. **Run Training** (10 hours on RTX 4070):
   ```bash
   cd C:\Users\ThaMain1\HRM

   OMP_NUM_THREADS=8 python pretrain.py \
       data_path=data/intellioptics-inspection-1k \
       epochs=20000 \
       eval_interval=2000 \
       global_batch_size=384 \
       lr=7e-5 \
       arch=vision_hrm
   ```

4. **Evaluation**:
   ```bash
   python evaluate.py \
       checkpoint=checkpoints/vision_hrm_epoch_20000.pt \
       data_path=data/intellioptics-inspection-1k/test
   ```

#### Step 4: Export to ONNX for Edge Deployment

```python
# Export trained VisionHRM to ONNX
import torch

model = VisionHRM.load_from_checkpoint("checkpoints/vision_hrm_epoch_20000.pt")
model.eval()

dummy_input = torch.randn(1, 3, 640, 640)
torch.onnx.export(
    model,
    dummy_input,
    "models/vision_hrm.onnx",
    input_names=["image"],
    output_names=["label", "confidence", "reasoning"],
    dynamic_axes={"image": {0: "batch_size"}}
)
```

#### Step 5: Integration into IntelliOptics Edge

1. **Add HRM Inference Service**:
   ```yaml
   # C:\Dev\intellioptics-edge-deploy\edge\docker-compose.yml
   services:
     hrm-inference:
       build: ./hrm-inference
       environment:
         - MODEL_PATH=/models/vision_hrm.onnx
         - CUDA_VISIBLE_DEVICES=0
       volumes:
         - ./models:/models
       ports:
         - "8002:8002"
   ```

2. **Update Edge API to call HRM**:
   ```python
   # edge-api/app/core/edge_inference.py

   async def run_inference_with_reasoning(detector_id, image_bytes):
       # 1. Primary model
       primary_result = await call_inference_service(detector_id, image_bytes)

       # 2. OODD model
       oodd_result = await call_oodd_service(detector_id, image_bytes)

       # 3. HRM reasoning (NEW)
       if detector.hrm_enabled:
           hrm_result = await call_hrm_service(image_bytes)
           return {
               "label": primary_result.label,
               "confidence": primary_result.confidence * oodd_result.in_domain_score,
               "reasoning": hrm_result.reasoning,  # NEW: Explanation
               "should_escalate": hrm_result.should_escalate  # NEW: Intelligent escalation
           }
   ```

#### Expected Results:

**Training Time**: ~10 hours on RTX 4070 (1000 samples)
**Accuracy**: >95% on defect detection (based on HRM's performance on similar tasks)
**Benefit**: Explainable AI + Few-shot learning + Intelligent escalation

#### Data Requirements Summary:

| Phase | Samples Needed | Source |
|-------|----------------|--------|
| **Phase 1** | 0 (use pre-trained YOLO/OODD) | - |
| **Phase 2** | 1000+ escalated images | Phase 1 deployment escalations |
| **Continuous** | +100/month | Ongoing escalations for retraining |

**Key Insight**: Phase 1 deployment generates the training data for Phase 2 HRM integration!

## Success Criteria

**Phase 1** (nginx-based edge deployment):
1. Edge deployment runs without Kubernetes
2. Detectors control inference routing (Primary + OODD)
3. Confidence-based escalation works (high → edge, low → cloud)
4. nginx fallback to cloud on errors
5. Models load on-demand and cache
6. Central web app for human escalation functional
7. RTSP camera integration supported
8. Offline mode supported (disable_cloud_escalation=true)

**Phase 2** (HRM AI integration - optional):
9. HRM reasoning layer provides explanations for detections
10. Few-shot training achieves >95% accuracy with 1000 samples
11. Escalation reasoning reduces false escalations by 30%+
