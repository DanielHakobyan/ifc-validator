import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from services.ifc_checker import run_checks

router = APIRouter()

UPLOAD_DIR = "/tmp/uploads"


class AnalysisRequest(BaseModel):
    filename: str
    selected_checks: List[str]
    ids_files: List[str] = []


@router.post("/run")
async def run_analysis(req: AnalysisRequest):
    ifc_path = os.path.join(UPLOAD_DIR, req.filename)

    if not os.path.exists(ifc_path):
        return JSONResponse(
            status_code=404,
            content={"error": f"IFC файл не найден: {req.filename}"}
        )

    # Use the first IDS file if provided
    ids_path = None
    if req.ids_files:
        ids_path = os.path.join(UPLOAD_DIR, req.ids_files[0])
        if not os.path.exists(ids_path):
            ids_path = None

    results = run_checks(ifc_path, req.selected_checks, ids_path=ids_path)
    return JSONResponse(results)
