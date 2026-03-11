from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UploadCodeSnippetSchema(BaseModel):
    code_snippet: str = Field(..., description="The actual snippet to explain")    
    
    
class CodeExplanationLLMSchema(BaseModel):
    code_snippet: str
    explanation: str
    title: str
    
    model_config = ConfigDict(from_attributes=True)
    

class DisplayCodeExplanationSchema(BaseModel):
    id: str 
    code_snippet: str 
    explanation: str 
    title: str
    date_created: datetime 
    
    model_config = ConfigDict(from_attributes=True)
    