"""
CIRCE Intel Desk — Schemas Pydantic para Document (RF-007).

Sprint 01-B — Sub-passo B8.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    case_id: int
    original_filename: str
    stored_path: str
    file_format: str
    file_size: int
    sha256_hash: str
    title: Optional[str] = None
    notes: Optional[str] = None
    imported_at: datetime


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    original_filename: str
    stored_path: str
    file_format: str
    file_size: int
    sha256_hash: str
    title: Optional[str]
    notes: Optional[str]
    imported_at: datetime
    created_at: datetime
    updated_at: datetime
