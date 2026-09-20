from sqlalchemy import Column, String, ForeignKey, Float, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database import Base

class Finding(Base):
    __tablename__ = "findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="SET NULL"))
    finding_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    details = Column(JSONB)
    
    evidences = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    ocr_result_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.id", ondelete="SET NULL"))
    image_crop_path = Column(String(512))
    highlighted_image_path = Column(String(512))
    fusion_confidence = Column(Float)
    
    finding = relationship("Finding", back_populates="evidences")
