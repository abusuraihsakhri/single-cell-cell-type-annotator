"""
FastAPI REST API Server for Single Cell Cell Type Annotator.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from celltype_annotator.annotation import annotate_clusters
from .base import SecurityException
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Single Cell Cell Type Annotator API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


class AnnotationRequest(BaseModel):
    cluster_markers: Dict[str, List[str]]
    references: Dict[str, List[str]]
    universe: List[str]
    alpha: float = 0.05
    min_overlap: int = 1


_web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/web", StaticFiles(directory=str(_web_dir)), name="web")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(_web_dir / "index.html")


@app.post("/api/annotate")
def api_annotate(payload: AnnotationRequest):
    total_rows = sum(map(len, payload.cluster_markers.values())) + sum(map(len, payload.references.values()))
    if (len(payload.universe) > 200_000 or total_rows > 20_000
            or len(payload.cluster_markers) > 500 or len(payload.references) > 500):
        raise HTTPException(status_code=413, detail="Annotation input exceeds size limits")
    try:
        return {"results": annotate_clusters(payload.cluster_markers, payload.references, payload.universe,
                                              alpha=payload.alpha, min_overlap=payload.min_overlap)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "single-cell-cell-type-annotator", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Request contains a potentially sensitive identifier") from exc


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
