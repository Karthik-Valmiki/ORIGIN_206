from sqlalchemy import Column, String, Boolean, ForeignKey, Float, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database import Base

class OcrResult(Base):
    __tablename__ = "ocr_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    detected_text = Column(String, nullable=False)
    bounding_box = Column(JSONB, nullable=False)
    confidence_score = Column(Float)
    language = Column(String(20), default="en")

class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    ocr_result_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.id", ondelete="SET NULL"))
    field_type = Column(String(50), nullable=False)
    raw_value = Column(String)
    normalized_value = Column(String)
    unit = Column(String(30))
    is_validated = Column(Boolean, nullable=False, default=False)
    confidence = Column(Float)  # Added from schema gaps
