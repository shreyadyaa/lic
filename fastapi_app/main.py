import os
import json
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi_app.models import UploadResponse  # Ensure models.py is inside fastapi_app

app = FastAPI(title="LIC Receipt Processor", version="1.0.0")

# Define paths
INPUT_DIR = Path("airflow/dags/input")
PDF_PATH = INPUT_DIR / "lic_receipt.pdf"
METADATA_PATH = INPUT_DIR / "metadata.json"

# Ensure input directory exists
INPUT_DIR.mkdir(parents=True, exist_ok=True)

@app.on_event("startup")
async def startup_event():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created input directory: {INPUT_DIR}")

@app.get("/")
async def root():
    return {"message": "LIC Receipt Processor API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/upload", response_model=UploadResponse)
async def upload_lic_receipt(
    file: UploadFile = File(..., description="PDF file of LIC receipt"),
    financial_year: str = Form(..., description="Financial year (e.g., 2023-24)")
):
    try:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        if not financial_year or len(financial_year) != 7 or financial_year[4] != '-':
            raise HTTPException(status_code=400, detail="Financial year must be in format YYYY-YY")
        
        with open(PDF_PATH, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        metadata = {
            "financial_year": financial_year,
            "upload_timestamp": datetime.now().isoformat(),
            "original_filename": file.filename,
            "file_size": os.path.getsize(PDF_PATH)
        }
        
        with open(METADATA_PATH, "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"File saved to: {PDF_PATH}")
        print(f"Metadata saved to: {METADATA_PATH}")
        
        return UploadResponse(
            message="File uploaded successfully",
            filename=file.filename or "lic_receipt.pdf",
            financial_year=financial_year,
            status="success"
        )
        
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/status")
async def get_processing_status():
    pdf_exists = PDF_PATH.exists()
    metadata_exists = METADATA_PATH.exists()
    
    status = {
        "pdf_file_exists": pdf_exists,
        "metadata_exists": metadata_exists,
        "ready_for_processing": pdf_exists and metadata_exists,
        "timestamp": datetime.now().isoformat()
    }
    
    if metadata_exists:
        try:
            with open(METADATA_PATH, "r") as f:
                metadata = json.load(f)
            status["metadata"] = metadata
        except Exception as e:
            status["metadata_error"] = str(e)
    
    return status

@app.delete("/clear")
async def clear_input_files():
    try:
        files_deleted = []
        if PDF_PATH.exists():
            PDF_PATH.unlink()
            files_deleted.append("lic_receipt.pdf")
        if METADATA_PATH.exists():
            METADATA_PATH.unlink()
            files_deleted.append("metadata.json")
        return {"message": "Files cleared", "deleted_files": files_deleted, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
