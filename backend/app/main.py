from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import services, pricing, estimate

app = FastAPI(title="AWS Cost Estimator API")

origins = [
    "http://localhost:3000",
    "http://localhost:5173", # Vite default
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(services.router, prefix="/api/services", tags=["Services"])
app.include_router(pricing.router, prefix="/api/pricing", tags=["Pricing"])
app.include_router(estimate.router, prefix="/api/estimate", tags=["Estimate"])

@app.get("/")
def read_root():
    return {"message": "AWS Cost Estimator API is running"}
