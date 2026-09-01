from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health import router as health_router
from app.routes.upload import router as upload_router

app = FastAPI(
    title="DoCA Onion Quality Assessment API",
    description="Backend for the Onion Grading system",
    version="0.1.0"
)

# Expand CORS origins to support Vite's dynamic local ports
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the routers under the /api prefix
app.include_router(health_router, prefix="/api", tags=["System"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])
