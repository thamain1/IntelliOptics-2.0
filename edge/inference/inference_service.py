"""
IntelliOptics 2.0 - Inference Service
Multi-detector ONNX inference with Primary + OODD ground truth models
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from cachetools import LRUCache

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, File, UploadFile, Query, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from PIL import Image
import io

# Configuration
MODEL_REPOSITORY = os.getenv("MODEL_REPOSITORY", "/models")
CACHE_MAX_MODELS = 5
IMG_SIZE = int(os.getenv("IO_IMG_SIZE", "640"))
CONF_THRESH = float(os.getenv("IO_CONF_THRESH", "0.5"))
NMS_IOU = float(os.getenv("IO_NMS_IOU", "0.45"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8081"))

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Model cache (LRU - keeps 5 most recently used models)
model_cache: LRUCache = LRUCache(maxsize=CACHE_MAX_MODELS)

app = FastAPI(title="IntelliOptics Inference Service", version="2.0")

# ====================
# Model Loading
# ====================

def load_onnx_model(model_path: str) -> ort.InferenceSession:
    """Load ONNX model with CPU/GPU support"""
    providers = ["CPUExecutionProvider"]

    # Check for CUDA
    if "CUDAExecutionProvider" in ort.get_available_providers():
        providers.insert(0, "CUDAExecutionProvider")
        logger.info("CUDA available - using GPU inference")

    session = ort.InferenceSession(model_path, providers=providers)
    logger.info(f"Loaded model: {model_path} with providers: {providers}")
    return session


def get_model_paths(detector_id: str) -> Tuple[Optional[Path], Optional[Path]]:
    """Get paths to Primary and OODD models for a detector"""
    base_path = Path(MODEL_REPOSITORY) / detector_id

    # Find latest version for Primary model
    primary_path = base_path / "primary"
    primary_model = None
    if primary_path.exists():
        versions = sorted([d for d in primary_path.iterdir() if d.is_dir()], reverse=True)
        if versions:
            model_file = versions[0] / "model.buf"
            if model_file.exists():
                primary_model = model_file

    # Find latest version for OODD model
    oodd_path = base_path / "oodd"
    oodd_model = None
    if oodd_path.exists():
        versions = sorted([d for d in oodd_path.iterdir() if d.is_dir()], reverse=True)
        if versions:
            model_file = versions[0] / "model.buf"
            if model_file.exists():
                oodd_model = model_file

    return primary_model, oodd_model


def load_detector_models(detector_id: str) -> Tuple[Optional[ort.InferenceSession], Optional[ort.InferenceSession]]:
    """Load Primary and OODD models for a detector (with caching)"""
    cache_key = detector_id

    if cache_key in model_cache:
        logger.debug(f"Cache hit for detector: {detector_id}")
        return model_cache[cache_key]

    primary_path, oodd_path = get_model_paths(detector_id)

    primary_session = None
    oodd_session = None

    if primary_path:
        try:
            primary_session = load_onnx_model(str(primary_path))
        except Exception as e:
            logger.error(f"Failed to load primary model for {detector_id}: {e}")

    if oodd_path:
        try:
            oodd_session = load_onnx_model(str(oodd_path))
        except Exception as e:
            logger.error(f"Failed to load OODD model for {detector_id}: {e}")

    # Cache the models
    model_cache[cache_key] = (primary_session, oodd_session)

    return primary_session, oodd_session


# ====================
# Image Preprocessing
# ====================

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Preprocess image for ONNX model input"""
    # Load image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Resize to model input size
    image = image.resize((IMG_SIZE, IMG_SIZE))

    # Convert to numpy array (CHW format)
    image_array = np.array(image).astype(np.float32)
    image_array = image_array.transpose(2, 0, 1)  # HWC -> CHW

    # Normalize (0-255 -> 0-1)
    image_array /= 255.0

    # Add batch dimension
    image_array = np.expand_dims(image_array, axis=0)

    return image_array


# ====================
# Inference
# ====================

def run_primary_inference(session: ort.InferenceSession, image: np.ndarray) -> Dict:
    """Run primary model inference"""
    # Get input name
    input_name = session.get_inputs()[0].name

    # Run inference
    outputs = session.run(None, {input_name: image})

    # Parse output (assumes YOLO-style output)
    # TODO: Adapt based on your actual model output format
    predictions = outputs[0]  # Shape: (batch, num_detections, 5+num_classes)

    # Extract best prediction
    if len(predictions.shape) == 3:
        predictions = predictions[0]  # Remove batch dimension

    if len(predictions) > 0:
        # Get highest confidence detection
        best_idx = np.argmax(predictions[:, 4])  # Confidence score at index 4
        best_detection = predictions[best_idx]

        confidence = float(best_detection[4])
        class_id = int(np.argmax(best_detection[5:]))  # Class scores start at index 5

        return {
            "label": class_id,
            "confidence": confidence,
            "bbox": best_detection[:4].tolist() if len(best_detection) >= 4 else None
        }
    else:
        return {"label": 0, "confidence": 0.0, "bbox": None}


def run_oodd_inference(session: ort.InferenceSession, image: np.ndarray) -> float:
    """Run OODD model inference to get in-domain score"""
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: image})

    # OODD output is in-domain confidence (0.0 to 1.0)
    in_domain_score = float(outputs[0][0])  # Assumes single output value

    return in_domain_score


# ====================
# API Endpoints
# ====================

@app.post("/infer")
async def infer(
    detector_id: str = Query(..., description="Detector ID"),
    image: UploadFile = File(..., description="Image file"),
    class_names: str = Query(None, description="Comma-separated class names for label mapping")
):
    """
    Run inference for a detector with Primary + OODD ground truth check

    Returns:
        - label: Detection class (name if class_names provided, otherwise numeric ID)
        - confidence: Final confidence (Primary × OODD in-domain score)
        - raw_primary_confidence: Original Primary model confidence
        - oodd_in_domain_score: OODD ground truth score
        - is_out_of_domain: True if OODD score < 0.5
    """
    try:
        # Load models
        primary_session, oodd_session = load_detector_models(detector_id)

        if not primary_session:
            raise HTTPException(status_code=404, detail=f"Primary model not found for detector: {detector_id}")

        # Read image
        image_bytes = await image.read()

        # Preprocess
        preprocessed_image = preprocess_image(image_bytes)

        # Run Primary model
        primary_result = run_primary_inference(primary_session, preprocessed_image)
        raw_confidence = primary_result["confidence"]
        class_id = primary_result["label"]

        # Map class_id to class name if class_names provided
        if class_names:
            names_list = [n.strip() for n in class_names.split(',')]
            label = names_list[class_id] if class_id < len(names_list) else f"class_{class_id}"
        else:
            label = f"class_{class_id}"

        # Run OODD model (ground truth check)
        oodd_in_domain_score = 1.0  # Default to in-domain if no OODD model
        if oodd_session:
            oodd_in_domain_score = run_oodd_inference(oodd_session, preprocessed_image)
        else:
            logger.warning(f"No OODD model for detector: {detector_id}")

        # Adjust confidence based on OODD ground truth
        final_confidence = raw_confidence * oodd_in_domain_score

        logger.info(f"🎯 Detector {detector_id}: {label} ({final_confidence:.2%})")

        return JSONResponse({
            "label": label,
            "class_id": class_id,
            "confidence": final_confidence,
            "raw_primary_confidence": raw_confidence,
            "oodd_in_domain_score": oodd_in_domain_score,
            "is_out_of_domain": oodd_in_domain_score < 0.5,
            "bbox": primary_result.get("bbox")
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inference error for {detector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================
# YOLOWorld Open-Vocabulary Detection
# ====================

# YOLOWorld model (lazy loaded)
yoloworld_model = None

def get_yoloworld_model():
    """Load YOLOWorld model (lazy initialization)"""
    global yoloworld_model
    if yoloworld_model is None:
        try:
            import torch

            # Patch torch.load to use weights_only=False for ultralytics models
            # This is needed for PyTorch 2.6+ compatibility with older model weights
            original_torch_load = torch.load

            def patched_torch_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_torch_load(*args, **kwargs)

            torch.load = patched_torch_load

            from ultralytics import YOLO
            logger.info("Loading YOLOWorld model (downloading if needed)...")
            # Use model name to download the correct version from ultralytics hub
            yoloworld_model = YOLO("yolov8s-world.pt")
            logger.info("YOLOWorld model loaded successfully")

            # Restore original torch.load
            torch.load = original_torch_load
        except Exception as e:
            logger.error(f"Failed to load YOLOWorld model: {e}")
            raise
    return yoloworld_model


@app.post("/yoloworld")
async def yoloworld_inference(
    image: UploadFile = File(..., description="Image file"),
    prompts: str = Query(..., description="Comma-separated list of objects to detect")
):
    """
    Run YOLOWorld open-vocabulary detection.

    Args:
        image: Image file to analyze
        prompts: Comma-separated list of things to detect (e.g., "person, car, fire")

    Returns:
        - detections: List of detected objects with labels and confidence
    """
    try:
        # Parse prompts
        prompt_list = [p.strip() for p in prompts.split(',') if p.strip()]
        if not prompt_list:
            raise HTTPException(status_code=400, detail="No valid prompts provided")

        logger.info(f"YOLOWorld inference with prompts: {prompt_list}")

        # Load model
        model = get_yoloworld_model()

        # Set the classes to detect
        model.set_classes(prompt_list)

        # Read image
        image_bytes = await image.read()

        # Save to temp file (ultralytics requires file path or numpy array)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            # Run inference
            results = model.predict(tmp_path, conf=CONF_THRESH, iou=NMS_IOU, verbose=False)

            # Parse results
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for i in range(len(boxes)):
                        box = boxes[i]
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].tolist()

                        # Get class name from prompt list
                        label = prompt_list[cls_id] if cls_id < len(prompt_list) else f"class_{cls_id}"

                        detections.append({
                            "label": label,
                            "confidence": conf,
                            "bbox": xyxy
                        })

            logger.info(f"YOLOWorld detected {len(detections)} objects")

            return JSONResponse({
                "detections": detections,
                "prompts_used": prompt_list
            })

        finally:
            # Clean up temp file
            import os
            os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YOLOWorld inference error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "cached_models": len(model_cache), "yoloworld_loaded": yoloworld_model is not None}


@app.get("/models")
async def list_models():
    """List available models"""
    model_repo = Path(MODEL_REPOSITORY)
    if not model_repo.exists():
        return {"models": []}

    detectors = []
    for detector_dir in model_repo.iterdir():
        if detector_dir.is_dir():
            primary_path, oodd_path = get_model_paths(detector_dir.name)
            detectors.append({
                "detector_id": detector_dir.name,
                "has_primary": primary_path is not None,
                "has_oodd": oodd_path is not None,
                "cached": detector_dir.name in model_cache
            })

    return {"models": detectors}


# ====================
# Main
# ====================

if __name__ == "__main__":
    # Run main inference service
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level=LOG_LEVEL.lower()
    )
