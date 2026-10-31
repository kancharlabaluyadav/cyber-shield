import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.database.database import init_db
from backend.services.prediction_service import get_artifacts
from backend.routes import prediction, moderation, analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    print("[INIT] Initializing SQLite database...")
    init_db()
    
    print("[INIT] Loading NLP Model artifacts...")
    try:
        get_artifacts()
        print("[INIT] Model artifacts loaded successfully.")
    except Exception as e:
        print(f"[WARNING] Model loading failed: {e}. Please ensure train_model.py has executed.")
        
    yield
    print("[SHUTDOWN] Server shutting down...")

app = FastAPI(
    title="CyberShield AI - Comment Moderation Engine",
    description="Production-Grade Social Media Cyberbullying & Abuse Moderation API powered by NLP and FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(prediction.router)
app.include_router(moderation.router)
app.include_router(analytics.router)

# Mount Frontend Static Directory if available
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Professional error response without exposing Python stack traces
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred. Please try again later."}
    )

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "CyberShield AI Backend"}
