from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from contextlib import asynccontextmanager

from .config import settings
from .database import engine, get_db, SessionLocal, Base
from .seed import seed_database
# Import models to ensure they are registered with SQLAlchemy
from .models import *

from .api import auth
from .api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if they don't exist (useful for testing, though we use init.sql for docker)
    # Base.metadata.create_all(bind=engine)
    
    # Run seed script
    db = SessionLocal()
    try:
        seed_database(db)
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="SIH26034 LMPC Verification API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    health_status = {"status": "ok", "db": "disconnected", "redis": "disconnected"}
    
    # Check DB
    try:
        db.execute(text("SELECT 1"))
        health_status["db"] = "connected"
    except Exception as e:
        health_status["status"] = "error"
        health_status["db"] = f"error: {str(e)}"
        
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["status"] = "error"
        health_status["redis"] = f"error: {str(e)}"
        
    if health_status["status"] == "error":
        raise HTTPException(status_code=503, detail=health_status)
        
    return health_status

app.include_router(api_router)
