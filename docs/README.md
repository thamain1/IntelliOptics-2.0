# IntelliOptics 2.0

**Lightweight, Nginx-Based Edge AI Quality Inspection Platform**

---

## Overview

IntelliOptics 2.0 is a complete rebuild of the IntelliOptics platform with a focus on:

- **Edge-First Architecture**: Process images on-device with Primary + OODD ground truth models
- **Confidence-Based Escalation**: Only questionable images (confidence < threshold) escalate to human review
- **Detector-Centric**: Detectors control AI engagement, thresholds, and escalation logic
- **No Kubernetes**: Simple Docker Compose deployment for stability and ease of use
- **HRM AI Ready**: Explainable AI with hierarchical reasoning (Phase 2)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Edge Device                            │
│                                                         │
│  Client → nginx:30101 ──┬─ Success → edge-api:8718      │ 
│                         └─ 404 → Central Web App        │
│                                                         │
│  edge-api:8718 (Edge Endpoint)                          │
│    ↓                                                    │
│  inference:8001 (Multi-detector ONNX)                   │
│    ├─ Primary models                                    │
│    └─ OODD models (ground truth)                        │
│                                                         │
│  postgres:5432 (optional - detector metadata)           │
└─────────────────────────────────────────────────────────┘
         │
         │ (Escalation: low confidence, human review)
         ↓
┌─────────────────────────────────────────────────────────┐
│         Central Web Application (Cloud)                 │
│                                                         │
│  nginx:80/443 → backend:8000 (API)                      │
│              → frontend:3000 (React UI)                 │
│                                                         │
│  backend:8000 (FastAPI)                                 │
│    ├─ /detectors  (CRUD)                                │
│    ├─ /queries    (Submit, Get)                         │
│    ├─ /escalations (Review queue)                       │
│    └─ /hubs       (Edge device management)              │
│                                                         │
│  frontend:3000 (React)                                  │
│    ├─ Review Queue (Human labeling)                     │
│    ├─ Detector Management                               │
│    └─ Edge Device Dashboard                             │
│                                                         │
│  worker:8001 (Inference worker for cloud-side)          │
│  postgres:5432 (Central database)                       │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- **Docker** & **Docker Compose** installed
- **Models**: ONNX models for your detectors (Primary + OODD)
- **API Token**: IntelliOptics API token for cloud integration (optional)

### Step 1: Deploy Edge

```bash
# Navigate to edge deployment
cd "C:\Dev\IntelliOptics 2.0\edge"

# Create environment file
cp .env.template .env

# Edit .env with your configuration
# - INTELLIOPTICS_API_TOKEN=<your-token>
# - POSTGRES_PASSWORD=<secure-password>
# - SENDGRID_API_KEY=<your-sendgrid-key>

# Create model directory
mkdir -p /opt/intellioptics/models

# (Optional) Copy your ONNX models to /opt/intellioptics/models
# Example structure:
# /opt/intellioptics/models/
# ├── det_abc123/
# │   ├── primary/
# │   │   └── 1/
# │   │       └── model.buf
# │   └── oodd/
# │       └── 1/
# │           └── model.buf

# Deploy edge services
docker-compose up -d

# Verify deployment
curl http://localhost:30101/health
```

### Step 2: Deploy Central Web App (Cloud)

```bash
# Navigate to cloud deployment
cd "C:\Dev\IntelliOptics 2.0\cloud"

# Create environment file
cp .env.template .env

# Edit .env with your configuration
# - POSTGRES_PASSWORD=<secure-password>
# - AZURE_STORAGE_CONNECTION_STRING=<azure-storage>
# - SENDGRID_API_KEY=<your-sendgrid-key>

# Deploy cloud services
docker-compose up -d

# Verify deployment
curl http://localhost:8000/health
```

### Step 3: Configure Detectors

Edit `edge/config/edge-config.yaml` to configure your detectors:

```yaml
detectors:
  det_quality_check_001:
    detector_id: det_quality_check_001
    name: "Quality Check - Main Line"
    edge_inference_config: default
    confidence_threshold: 0.85  # Escalate if confidence < 0.85
    mode: BINARY
    class_names: ["pass", "defect"]
```

Restart edge deployment:

```bash
cd "C:\Dev\IntelliOptics 2.0\edge"
docker-compose restart edge-api
```

---

## Key Features

### 1. Confidence-Based Escalation

- **High confidence** (>= threshold): Return edge result immediately
- **Low confidence** (< threshold): Escalate to central web app for human review
- **OODD ground truth**: Out-of-domain images automatically escalated

### 2. Detector-Centric Configuration

Each detector controls:
- Confidence threshold
- Escalation behavior
- Mode (BINARY, MULTICLASS, COUNTING, etc.)
- RTSP camera streams
- HRM AI reasoning (Phase 2)

### 3. Alerts

Automatic email alerts for escalations:
- Configurable recipient list
- Batch alerts (every N escalations or M minutes)
- Rich HTML emails with reasoning chains

### 4. RTSP Camera Integration

Continuous monitoring of production lines:
- Multiple cameras per edge device
- Frame sampling intervals
- Direct edge inference or REST API submission
- Auto-reconnect on stream failure

### 5. Offline Mode

Run without cloud connectivity:
- Set `edge_inference_config: offline` for detectors
- All inference on edge
- Queue escalations for later sync

---

## Deployment Scenarios

### Scenario 1: Single Edge Device + Cloud

**Use Case**: One production line with cloud-based human review

```bash
# Deploy edge at production site
cd "C:\Dev\IntelliOptics 2.0\edge"
docker-compose up -d

# Deploy cloud in Azure/AWS
cd "C:\Dev\IntelliOptics 2.0\cloud"
# Deploy to Azure Container Instances, ECS, or VM
```

### Scenario 2: Multiple Edge Devices + Central Cloud

**Use Case**: Multiple factories, central quality team

```bash
# Deploy edge at each factory
# Factory A, B, C...
cd "C:\Dev\IntelliOptics 2.0\edge"
docker-compose up -d

# Deploy single cloud instance
cd "C:\Dev\IntelliOptics 2.0\cloud"
# Deploy to cloud region
```

### Scenario 3: Offline Edge Only

**Use Case**: No internet connectivity, periodic sync

```bash
# Deploy edge with offline config
cd "C:\Dev\IntelliOptics 2.0\edge"

# Edit edge-config.yaml:
# detectors:
#   det_offline_003:
#     edge_inference_config: offline

docker-compose up -d

# No cloud deployment needed
```

---

## API Endpoints

### Edge API (port 8718)

- `POST /v1/image-queries?detector_id=det_abc123` - Submit image for inspection
- `GET /v1/detectors` - List available detectors
- `GET /health` - Health check
- `GET /status` - Service status

### Central Web App Backend (port 8000)

- `GET /detectors` - List all detectors
- `POST /detectors` - Create new detector
- `GET /escalations` - Review queue
- `POST /escalations/{id}/resolve` - Resolve escalation with human label
- `GET /hubs` - List edge devices

---

## Model Management

### Model Directory Structure

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
│   └── oodd/                  # Out-of-Domain Detection (ground truth)
│       └── 1/
│           └── model.buf
```

### Adding a New Detector

1. Create model directories:
```bash
mkdir -p /opt/intellioptics/models/det_new_detector/primary/1
mkdir -p /opt/intellioptics/models/det_new_detector/oodd/1
```

2. Copy ONNX models:
```bash
cp primary_model.onnx /opt/intellioptics/models/det_new_detector/primary/1/model.buf
cp oodd_model.onnx /opt/intellioptics/models/det_new_detector/oodd/1/model.buf
```

3. Add to `edge-config.yaml`:
```yaml
detectors:
  det_new_detector:
    detector_id: det_new_detector
    name: "New Quality Check"
    edge_inference_config: default
    confidence_threshold: 0.85
    mode: BINARY
    class_names: ["pass", "fail"]
```

4. Restart edge API:
```bash
docker-compose restart edge-api
```

---

## Monitoring

### View Logs

```bash
# Edge logs
cd "C:\Dev\IntelliOptics 2.0\edge"
docker-compose logs -f edge-api
docker-compose logs -f inference

# Cloud logs
cd "C:\Dev\IntelliOptics 2.0\cloud"
docker-compose logs -f backend
docker-compose logs -f worker
```

### Check Service Health

```bash
# Edge health
curl http://localhost:30101/health
curl http://localhost:8718/health
curl http://localhost:8001/health

# Cloud health
curl http://localhost:8000/health
```

### Model Cache Status

```bash
# Check loaded models
curl http://localhost:8001/models
```

---

## Troubleshooting

### Issue: Models Not Loading

**Solution**:
1. Check model directory permissions:
   ```bash
   ls -la /opt/intellioptics/models
   ```
2. Verify model file exists:
   ```bash
   ls -la /opt/intellioptics/models/det_abc123/primary/1/model.buf
   ```
3. Check inference logs:
   ```bash
   docker-compose logs inference
   ```

### Issue: Edge API Returns 503

**Cause**: Inference service not ready

**Solution**:
```bash
# Check inference service health
curl http://localhost:8001/health

# Restart if needed
docker-compose restart inference
```

### Issue: Escalations Not Working

**Solution**:
1. Check cloud connectivity:
   ```bash
   curl https://central-web-app.example.com/health
   ```
2. Verify API token in `.env`
3. Check edge-api logs for escalation attempts:
   ```bash
   docker-compose logs edge-api | grep escalation
   ```

---

## Phase 2: HRM AI Integration

### Overview

**Phase 2** adds Hierarchical Reasoning Model (HRM) for:
- **Explainable AI**: Reasoning chains explaining why an image is defective
- **Few-Shot Learning**: Train new detectors with just 1000 samples
- **Intelligent Escalation**: HRM decides when/why to escalate

### Training Guide

See `docs/HRM-TRAINING.md` for complete HRM training guide.

### Quick Start

1. Collect 1000+ escalated images from Phase 1 deployment
2. Generate reasoning chains (using VLM like Claude 3.7 Sonnet)
3. Train HRM model (~10 hours on RTX 4070)
4. Export to ONNX
5. Add HRM inference service to edge deployment

---

## Documentation

### Getting Started
- **[Detector Creation Guide](docs/DETECTOR-CREATION-GUIDE.md)** ⭐ - Complete guide to creating and configuring detectors
- **[Web Interface Guide](docs/WEB-INTERFACE-GUIDE.md)** ⭐ - Using the centralized management dashboard
- **[Camera Health Monitoring](docs/CAMERA-HEALTH-MONITORING.md)** ⭐ - Image quality and tampering detection

### Architecture & Testing
- **Architecture**: `docs/ARCHITECTURE.md` - Full system design (from plan file)
- **[APIM Backend Test Results](APIM-BACKEND-TEST-RESULTS.md)** - Verification of cloud backend functionality

### Advanced Topics
- **HRM Training**: `docs/HRM-TRAINING.md` - HRM AI training guide
- **API Reference**: See engineering diagrams in `docs/images/`

---

## Support

For issues, questions, or feature requests:
1. Check existing documentation in `docs/`
2. Review deployment logs
3. Consult architecture diagrams

---

## License

Proprietary - IntelliOptics 2.0 is a Product of 4wardmotion Solutions, Inc. All rights to the technology, name, brand, and associated IP are the property of this same entity.  
