from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import pnr, health

app = FastAPI(
    title="PNRConfirm API",
    description="AI-powered Indian Railways PNR confirmation predictor",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(pnr.router, prefix="/api/pnr", tags=["pnr"])

@app.get("/")
def root():
    return {"message": "PNRConfirm API is running 🚂"}