from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import estimate_router, pricing_router, registry
import json
import os

app = FastAPI(title="AWS Cost Estimation Platform")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus & Logging Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import make_asgi_app, Counter, Histogram
import time
import uuid

# Metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency in seconds", ["method", "endpoint"])

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        # Attach to request state/scope if needed, or just log
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Labels
        method = request.method
        path = request.url.path
        status_code = str(response.status_code)
        
        # Observe
        REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(process_time)
        
        # Add X-Request-ID
        response.headers["X-Request-ID"] = request_id
        
        # Structured Log (Simplified)
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "method": method,
            "path": path,
            "status": status_code,
            "duration_s": round(process_time, 4)
        }
        # In prod, use json.dumps(log_entry) via logging handler
        if path != "/metrics": # Reduce noise
           logger.info(json.dumps(log_entry))
           
        return response

app.add_middleware(MetricsMiddleware)

# Expose Metrics Endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
from datetime import datetime # Ensure import if not present

# Routes
app.include_router(estimate_router.router, prefix="/api/estimate", tags=["Estimate"])
app.include_router(pricing_router.router, prefix="/api/pricing", tags=["Pricing"])
from .api import export
app.include_router(export.router, prefix="/api/export", tags=["Export"])

@app.get("/api/services")
async def list_services():
    return registry.registry.get_all_services()

@app.get("/api/services/{service_id}/metadata")
async def get_service_metadata(service_id: str):
    # This should return the metadata from service_metadata.json filtered by service
    # Or prompt the service metadata module?
    # "GET /api/services/{service}/metadata"
    # "Metadata engine ... Save to service_metadata.json"
    
    # Let's read service_metadata.json
    from backend.app.core.paths import METADATA_FILE
    
    if not METADATA_FILE.exists():
        return {}
        
    with open(meta_path, 'r') as f:
        data = json.load(f)
        
    return data.get(service_id, {})

@app.get("/")
async def root():
    return {"message": "AWS Cost Estimation API is running"}
