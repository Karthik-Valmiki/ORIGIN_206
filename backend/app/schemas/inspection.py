import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ── Inspection ────────────────────────────────────────────────────────────────

class InspectionCreate(BaseModel):
    product_category_id: uuid.UUID


class CategoryOut(BaseModel):
    id: uuid.UUID
    category_name: str
    description: str | None

    model_config = {"from_attributes": True}


class ImageStatusOut(BaseModel):
    id: uuid.UUID
    file_path: str
    preprocessing_status: str
    ocr_status: str
    blur_score: float | None
    glare_score: float | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ExtractedFieldOut(BaseModel):
    id: uuid.UUID
    field_type: str
    raw_value: str | None
    normalized_value: str | None
    unit: str | None
    is_validated: bool

    model_config = {"from_attributes": True}


class FindingOut(BaseModel):
    id: uuid.UUID
    finding_type: str
    status: str   # PASS | FAIL | AMBIGUOUS
    details: dict[str, Any] | None

    model_config = {"from_attributes": True}


class ReviewOut(BaseModel):
    id: uuid.UUID
    action: str
    comments: str | None
    reviewed_at: datetime

    model_config = {"from_attributes": True}


class InspectionOut(BaseModel):
    id: uuid.UUID
    inspection_number: str | None
    status: str
    product_category: CategoryOut
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InspectionDetailOut(InspectionOut):
    images: list[ImageStatusOut]
    extracted_fields: list[ExtractedFieldOut]
    findings: list[FindingOut]
    reviews: list[ReviewOut]

    model_config = {"from_attributes": True}


# ── Review ────────────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    action: str   # ACCEPT | OVERRIDE | REQUEST_REINSPECTION
    comments: str | None = None


# ── Image upload response ─────────────────────────────────────────────────────

class ImageUploadResponse(BaseModel):
    image_id: uuid.UUID
    status: str
    message: str


# ── Rules Management ──────────────────────────────────────────────────────────

class RuleOut(BaseModel):
    id: uuid.UUID
    rule_version_id: uuid.UUID
    rule_code: str
    check_type: str
    description: str | None
    parameters: dict[str, Any] | None

    model_config = {"from_attributes": True}


class RuleCreate(BaseModel):
    rule_code: str
    check_type: str  # PRESENCE, VALUE, FORMAT, UNIT, PLACEMENT, LEGIBILITY, VISUAL, DECLARATION
    description: str | None = None
    is_mandatory: bool = True
    field: str | None = None
    rule_ref: str | None = None


class RuleUpdate(BaseModel):
    check_type: str | None = None
    description: str | None = None
    is_mandatory: bool | None = None
    field: str | None = None
    rule_ref: str | None = None


class RuleVersionOut(BaseModel):
    id: uuid.UUID
    rule_set_id: uuid.UUID
    version_number: str
    is_active: bool
    effective_from: datetime
    rules: list[RuleOut] = []

    model_config = {"from_attributes": True}


class RuleVersionCreate(BaseModel):
    version_number: str
    clone_from_active: bool = True

