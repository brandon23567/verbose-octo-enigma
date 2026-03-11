from ..database import Base
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm  import relationship
from datetime import datetime, timezone
from uuid import uuid4 


class CodeExplainerModel(Base):
    __tablename__ = "explained_code_snippets"
    
    id = Column(String, index=True, primary_key=True, default=lambda: uuid4().hex)
    title = Column(String, nullable=False, index=True)
    code_snippet = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False, index=True)
    # date_created = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    date_created = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))