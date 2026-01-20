"""Entry point for the FastAPI application."""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .routers import (
    detectors,
    queries,
    escalations,
    hubs,
    settings as settings_router,
    deployments,
    inspection_config,
    camera_inspection,
    detector_alerts,
    demo_streams,
    annotations
)
from . import auth # Import the new auth module


logger = logging.getLogger(__name__)

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(name)s - %(message)s'
)

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="IntelliOptics API", version="1.0.0")
    
    # Configure CORS to allow frontend to access the API
    origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Create database tables if they don't exist
    Base.metadata.create_all(bind=engine)
    # Include routers
    app.include_router(auth.router) # Add the new auth router for /token
    app.include_router(detectors.router)
    app.include_router(queries.router)
    app.include_router(escalations.router)
    app.include_router(hubs.router)
    app.include_router(settings_router.router)
    app.include_router(deployments.router)
    app.include_router(inspection_config.router)  # Camera inspection config
    app.include_router(camera_inspection.router)  # Camera inspection dashboard
    app.include_router(detector_alerts.router)  # Detector-based alerts
    app.include_router(demo_streams.router)  # YouTube demo streams
    app.include_router(annotations.router)  # Image annotations
    from .routers import users, data_management
    app.include_router(users.router)
    app.include_router(data_management.router)  # Data retention & training export

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
