from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from ..database import Base

class ProductCategory(Base):
    __tablename__ = "product_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    category_name = Column(String(100), unique=True, nullable=False)
    description = Column(String)
