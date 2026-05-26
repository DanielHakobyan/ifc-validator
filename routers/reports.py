import io
import json
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List
from services.report_generator import generate_pdf, generate_excel, generate_bcf

router = APIRouter()


class ReportRequest(BaseModel):
    issues: List[dict]
    summary: dict
    format: str


@router.post("/download")
async def download_report(req: ReportRequest):
    today = datetime.now().strftime("%Y%m%d")
    filename_base = f"tim_inspector_{today}"

    if req.format == "json":
        data = json.dumps({"summary": req.summary, "issues": req.issues}, ensure_ascii=False, indent=2)
        return StreamingResponse(
            io.BytesIO(data.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.json"},
        )

    elif req.format == "pdf":
        pdf_bytes = generate_pdf(req.summary, req.issues)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.pdf"},
        )

    elif req.format == "excel":
        excel_bytes = generate_excel(req.summary, req.issues)
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.xlsx"},
        )

    elif req.format == "bcf":
        bcf_content = generate_bcf(req.issues)
        return StreamingResponse(
            io.BytesIO(bcf_content.encode("utf-8")),
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.bcf"},
        )

    return JSONResponse({"error": "Неизвестный формат"}, status_code=400)
