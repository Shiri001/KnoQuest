from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class SourceCitation(BaseModel):
    source: str = Field(..., description="Name of the enterprise document, e.g., HR_Policy.pdf")
    section: Optional[str] = Field(None, description="Section or article within the document")
    snippet: Optional[str] = Field(None, description="Relevant excerpt grounded in the text")

class ToolCallResult(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's natural language question or prompt")
    conversation_id: Optional[str] = Field(None, description="Optional conversation tracking ID")
    language: Optional[str] = Field("en", description="Target ISO language code, e.g., en, hi, es, fr, pa")
    session_file_id: Optional[str] = Field(None, description="ID of a temporarily uploaded document")
    employee_id: Optional[str] = Field(None, description="Optional employee ID e.g. NOVA-EMP001")

class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    sources: List[SourceCitation] = []
    tool_calls: Optional[List[ToolCallResult]] = []
    mode: str = Field("local_sandbox", description="'azure_foundry' or 'local_sandbox'")
    language: str = "en"
    authenticated_user: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "KnoQuest — Enterprise Knowledge Agent"
    version: str = "1.0.0"
    mode: str
    azure_configured: bool
    enterprise_docs_loaded: int = 0

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    chunks_count: int
    message: str

class SpeechTranscriptionResponse(BaseModel):
    text: str
    language: str = "en"

class SpeechSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to convert into speech")
    language: Optional[str] = Field("en", description="Target ISO language code (en, hi, pa, es, fr)")

class SpeechSynthesisResponse(BaseModel):
    status: str = "success"
    audio_format: str = "wav"
    audio_base64: Optional[str] = None
    message: str = "Speech synthesized successfully"

class TicketRequest(BaseModel):
    issue: str
    priority: Optional[str] = "Medium"
    user_name: Optional[str] = "Employee"
    department: Optional[str] = "General"

class TicketResponse(BaseModel):
    ticket_id: str
    status: str
    issue: str
    priority: str
    user_name: str
    department: str
    created_at: str
    message: str
