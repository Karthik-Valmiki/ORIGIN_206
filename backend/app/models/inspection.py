from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Float, text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database import Base

class Inspection(Base):
    __tablename__ = "inspections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    inspection_number = Column(String(50), unique=True)
    officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    product_category_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="RESTRICT"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("lmpc_rules.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    
    # Metadata additions from part 1 schema gap
    product_name = Column(String(200))
    location = Column(String(300))
    is_imported = Column(Boolean, nullable=False, default=False)
    notes = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    
    images = relationship("Image", back_populates="inspection", cascade="all, delete-orphan")
    findings = relationship("Finding", cascade="all, delete-orphan")
    officer = relationship("User")
    category = relationship("ProductCategory")
    rule = relationship("LMPCRule")


class Image(Base):
    __tablename__ = "images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(512), nullable=False)
    is_valid_file = Column(Boolean, nullable=False, default=True)
    resolution_width = Column(Integer)
    resolution_height = Column(Integer)
    blur_score = Column(Float)
    glare_score = Column(Float)
    reflection_score = Column(Float)
    orientation_angle = Column(Integer)
    preprocessing_status = Column(String(50), nullable=False, default="UNPROCESSED")
    ocr_status = Column(String(50), nullable=False, default="PENDING")
    uploaded_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    
    inspection = relationship("Inspection", back_populates="images")
    history = relationship("ImageProcessingHistory", back_populates="image", cascade="all, delete-orphan")


class ImageProcessingHistory(Base):
    __tablename__ = "image_processing_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    step_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    parameters = Column(JSONB)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    
    image = relationship("Image", back_populates="history")
