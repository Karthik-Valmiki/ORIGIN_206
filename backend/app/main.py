from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
from app.api.v1 import auth, inspections, setup, admin
from app.config import settings
from app.database import engine

from fastapi.responses import RedirectResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print("\n" + "=" * 50)
    print(" LMPC Backend is running!")
    print(" Interactive Swagger UI: http://localhost:8000/docs")
    print("  Health Check:           http://localhost:8000/health")
    print("=" * 50 + "\n")
    yield
    await engine.dispose()


app = FastAPI(
    title="LMPC Verification System Prototype",
    description="Backend API for OCR and CV processing (SIH 2026)",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(inspections.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """Automatically redirect root requests to Swagger UI documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
