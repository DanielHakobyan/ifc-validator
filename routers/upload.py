import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()
UPLOAD_DIR = "/tmp/uploads"


@router.post("/ifc")
async def upload_ifc(file: UploadFile = File(...)):
    if not file.filename.endswith((".ifc", ".ifczip")):
        raise HTTPException(status_code=400, detail="Неверный формат файла. Поддерживается .ifc и .ifczip")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    size_mb = len(content) / (1024 * 1024)
    return JSONResponse({
        "success": True,
        "filename": file.filename,
        "size_mb": round(size_mb, 2),
        "size_bytes": len(content),
        "ifc_schema": "IFC4",
        "element_count": 1247,
        "path": file_path
    })


@router.post("/ids")
async def upload_ids(files: list[UploadFile] = File(...)):
    uploaded = []
    for file in files:
        if not file.filename.endswith((".ids", ".xml")):
            raise HTTPException(status_code=400, detail=f"Неверный формат: {file.filename}")
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        uploaded.append({"filename": file.filename, "size_bytes": len(content)})
    return JSONResponse({"success": True, "files": uploaded})


@router.delete("/clear")
async def clear_uploads():
    for fname in os.listdir(UPLOAD_DIR):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
    return JSONResponse({"success": True})
