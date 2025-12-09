from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from backend.app.core.estimator_logic import calculate_estimate
import logging
import io
from datetime import datetime

# ReportLab imports
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
except ImportError:
    pass # Handle gracefully if missing, though we added to requirements

router = APIRouter()
logger = logging.getLogger(__name__)

class ExportNode(BaseModel):
    id: str
    service: str
    config: Dict[str, Any]

class ExportPayload(BaseModel):
    nodes: List[ExportNode]

async def process_estimates(nodes: List[ExportNode]) -> Dict[str, Any]:
    results = []
    total_cost = 0.0
    
    for node in nodes:
        try:
            # We call the core logic. 
            # Note: payload for estimate is the 'config'.
            estimate = await calculate_estimate(node.service, node.config)
            
            # Estimate usually returns {"total_cost": float, "breakdown": ...}
            cost = estimate.get("total_cost", 0.0)
            total_cost += cost
            
            results.append({
                "id": node.id,
                "service": node.service,
                "config": node.config,
                "estimate": estimate
            })
        except Exception as e:
            logger.error(f"Failed to calculate for node {node.id}: {e}")
            results.append({
                "id": node.id,
                "service": node.service,
                "error": str(e)
            })
            
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_monthly_cost": total_cost,
        "items": results,
        "metadata": {
            "version": "1.0",
            "currency": "USD"
        }
    }

@router.post("/json")
async def export_json(payload: ExportPayload):
    data = await process_estimates(payload.nodes)
    return data

@router.post("/pdf")
async def export_pdf(payload: ExportPayload):
    data = await process_estimates(payload.nodes)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("AWS Cost Estimation Report", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Meta
    story.append(Paragraph(f"Generated At: {data['generated_at']}", styles['Normal']))
    story.append(Paragraph(f"Total Monthly Cost: ${data['total_monthly_cost']:.2f}", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    # Table data
    table_data = [["ID", "Service", "Cost ($)", "Details"]]
    
    for item in data['items']:
        if 'error' in item:
            row = [
                item['id'], 
                item['service'], 
                "ERROR", 
                item['error'][:50]
            ]
        else:
            est = item['estimate']
            cost = est.get('total_cost', 0.0)
            # Format some details
            details = f"{len(item['config'])} params"
            
            row = [
                item['id'],
                item['service'],
                f"${cost:.2f}",
                details
            ]
        table_data.append(row)
        
    # Create Table
    t = Table(table_data, colWidths=[100, 80, 80, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(t)
    doc.build(story)
    
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type="application/pdf", headers={
        "Content-Disposition": "attachment; filename=estimation_report.pdf"
    })
