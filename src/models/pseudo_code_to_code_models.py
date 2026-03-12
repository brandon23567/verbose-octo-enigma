from ..database import Base
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4 


class PseudoCodeToCodeModel(Base):
    __tablename__ = "pseudo_code_to_code"
    
    id = Column(String, index=True, primary_key=True, default=lambda: uuid4().hex)
    title = Column(String, nullable=False)
    pseudo_code = Column(Text, nullable=False)
    actual_code = Column(Text, nullable=False)
    date_created = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    