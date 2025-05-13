from pydantic import BaseModel
from typing import Dict, Any, List, Literal

class ToolUsage(BaseModel):
    step: int
    tool: str
    input: Dict[str, Any]
    output: Any = None

class DebugInfo(BaseModel):
    tool_usage: List[ToolUsage]
    message_count: int
    error: str | None = None # Added error field based on your log output for debug

class AgentLogicResponse(BaseModel):
    response: str
    debug: DebugInfo | None = None
    trace_data: Any | None = None # Added trace_data field based on your log output

# Models for Vercel AI SDK compatible /api/chat endpoint (used by main.py)
class MessageVercelAI(BaseModel):
    role: Literal['user', 'assistant', 'system', 'function', 'tool']
    content: str
    id: str | None = None
    name: str | None = None
    tool_calls: List[Dict[str, Any]] | None = None
    tool_call_id: str | None = None

class ChatRequestVercelAI(BaseModel):
    messages: List[MessageVercelAI]
    data: Dict[str, Any] | None = None

# Original QueryRequest for /api/debug (used by main.py)
class QueryRequest(BaseModel):
    query: str 