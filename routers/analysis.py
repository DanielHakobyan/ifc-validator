from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from services.ifc_checker import run_checks

router = APIRouter()


class AnalysisRequest(BaseModel):
    filename: str
    selected_checks: List[str]
    ids_files: List[str] = []


@router.post("/run")
async def run_analysis(req: AnalysisRequest):
    results = run_checks(req.selected_checks)
    return JSONResponse(results)
