import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Rules hierarchy (needed for FK refs; logic is pure-Python) ──────────────

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class RuleSet(Base):
    __tablename__ = "rule_sets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    versions: Mapped[list["RuleVersion"]] = relationship("RuleVersion", back_populates="rule_set")


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rule_set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rule_sets.id", ondelete="CASCADE"))
    version_number: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    rule_set: Mapped[RuleSet] = relationship("RuleSet", back_populates="versions")
    rules: Mapped[list["Rule"]] = relationship("Rule", back_populates="rule_version")


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rule_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rule_versions.id", ondelete="CASCADE")
    )
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parameters: Mapped[dict | None] = mapped_column(JSONB)

    rule_version: Mapped[RuleVersion] = relationship("RuleVersion", back_populates="rules")


# ── Core inspection entities ─────────────────────────────────────────────────

class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inspection_number: Mapped[str | None] = mapped_column(String(50), unique=True)
    officer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    product_category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_categories.id", ondelete="RESTRICT"), nullable=False
    )
    rule_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rule_versions.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    officer: Mapped["User | None"] = relationship("User", back_populates="inspections")  # noqa: F821
    product_category: Mapped[ProductCategory] = relationship("ProductCategory")
    rule_version: Mapped[RuleVersion] = relationship("RuleVersion")
    images: Mapped[list["Image"]] = relationship(
        "Image", back_populates="inspection", cascade="all, delete-orphan"
    )
    ocr_results: Mapped[list["OcrResult"]] = relationship("OcrResult", back_populates="inspection")
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        "ExtractedField", back_populates="inspection"
    )
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="inspection")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="inspection")


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_valid_file: Mapped[bool] = mapped_column(Boolean, default=True)
    resolution_width: Mapped[int | None] = mapped_column(Integer)
    resolution_height: Mapped[int | None] = mapped_column(Integer)
    blur_score: Mapped[float | None] = mapped_column(Float)
    glare_score: Mapped[float | None] = mapped_column(Float)
    reflection_score: Mapped[float | None] = mapped_column(Float)
    orientation_angle: Mapped[int | None] = mapped_column(Integer)
    preprocessing_status: Mapped[str] = mapped_column(String(50), default="UNPROCESSED")
    ocr_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    inspection: Mapped[Inspection] = relationship("Inspection", back_populates="images")


class OcrResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("images.id", ondelete="CASCADE"), nullable=False
    )
    detected_text: Mapped[str] = mapped_column(Text, nullable=False)
    bounding_box: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    language: Mapped[str] = mapped_column(String(20), default="en")

    inspection: Mapped[Inspection] = relationship("Inspection", back_populates="ocr_results")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    ocr_result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ocr_results.id", ondelete="SET NULL")
    )
    field_type: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(30))
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)

    inspection: Mapped[Inspection] = relationship("Inspection", back_populates="extracted_fields")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rules.id", ondelete="SET NULL")
    )
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # PASS | FAIL | AMBIGUOUS
    details: Mapped[dict | None] = mapped_column(JSONB)

    inspection: Mapped[Inspection] = relationship("Inspection", back_populates="findings")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    officer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    inspection: Mapped[Inspection] = relationship("Inspection", back_populates="reviews")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    report_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID | None]
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
