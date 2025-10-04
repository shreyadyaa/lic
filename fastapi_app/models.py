from pydantic import BaseModel
from typing import Optional

class UploadResponse(BaseModel):
    message: str
    filename: str
    financial_year: str
    status: str

class ProcessingStatus(BaseModel):
    dag_id: str
    execution_date: str
    state: Optional[str] = None