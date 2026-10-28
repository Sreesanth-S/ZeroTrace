"""
ZeroTrace Authoritative FastAPI Backend Application
Main application entrypoint.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path so 'backend' is resolvable from any working directory
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from backend.app.core.config import settings
from backend.app.core.errors import ZeroTraceException, zerotrace_exception_handler
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.wipe_evidence import router as evidence_router
from backend.app.api.v1.certificates import router as certificates_router
from backend.app.api.v1.verification import router as verification_router
from backend.app.api.v1.auth import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("zerotrace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ZeroTrace Authoritative Backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Public Key Pinned: {bool(settings.SIGNING_PUBLIC_KEY_PEM)}")
    logger.info(f"Private Key Configured: {bool(settings.SIGNING_PRIVATE_KEY_PEM)}")
    yield
    logger.info("Shutting down ZeroTrace Authoritative Backend...")


app = FastAPI(
    title="ZeroTrace Authoritative Backend API",
    description=(
        "Sole authority for device wipe evidence validation, cryptographic signing, "
        "Supabase certificate storage, and dual-anchor public verification."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Error Handlers
app.add_exception_handler(ZeroTraceException, zerotrace_exception_handler)

# Include API Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(health_router)  # Also mount /health at root
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(certificates_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "ZeroTrace Authoritative Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
