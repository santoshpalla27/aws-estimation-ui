from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi.responses import JSONResponse, FileResponse
import tempfile
import os
import json
from fpdf import FPDF
from datetime import datetime

router = APIRouter()

class EstimateItem(BaseModel):
    service: str
    region: str
    details: str
    cost: float

class ExportRequest(BaseModel):
    items: List[EstimateItem]

@router.post("/json")
def export_json(req: ExportRequest):
    # Just echo back nicely formatted or wrapped
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_cost": sum(i.cost for i in req.items),
        "items": [i.dict() for i in req.items]
    }
    
    # Create temp file
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, 'w') as tmp:
        json.dump(report, tmp, indent=2)
    
    return FileResponse(path, filename="cost_analysis.json", media_type="application/json")

@router.post("/pdf")
def export_pdf(req: ExportRequest):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, txt="AWS Cost Estimate Report", ln=1, align='C')
    
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 10, txt=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1, align='C')
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 10, "Service", 1)
    pdf.cell(40, 10, "Region", 1)
    pdf.cell(80, 10, "Details", 1)
    pdf.cell(30, 10, "Cost ($)", 1)
    pdf.ln()
    
    # Items
    pdf.set_font("Helvetica", size=10)
    total = 0
    for item in req.items:
        pdf.cell(40, 10, item.service[:20], 1)
        pdf.cell(40, 10, item.region, 1)
        pdf.cell(80, 10, item.details[:45], 1) # simple truncate
        pdf.cell(30, 10, f"{item.cost:.2f}", 1)
        pdf.ln()
        total += item.cost
        
    # Total
    pdf.set_font("Helvetica", 'B', 12)
    pdf.ln(5)
    pdf.cell(160, 10, "Total Monthly Estimate:", 0, 0, 'R')
    pdf.cell(30, 10, f"${total:.2f}", 0, 1, 'L')
    
    fd, path = tempfile.mkstemp(suffix=".pdf")
    pdf.output(path)
    
    return FileResponse(path, filename="cost_analysis.pdf", media_type="application/pdf")
