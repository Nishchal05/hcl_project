from pydantic import BaseModel, Field
from datetime import date
from typing import Any, Literal

AnswerType = Literal['retrieved_fact','calculated','not_found','clarification_needed','refused','conflict_flagged']
class AskRequest(BaseModel):
 question: str = Field(min_length=3, max_length=2000)
 as_of_date: date|None = None
class Citation(BaseModel): doc_id:str; title:str; section:str|None=None; page:str|None=None; version:str|None=None; effective_date:str|None=None
class ToolResult(BaseModel): tool:str; result:dict[str,Any]
class AskResponse(BaseModel):
    trace_id:str; answer:str; answer_type:AnswerType; citations:list[Citation]=[]; tool_results:list[ToolResult]=[]; conflicts:list[dict[str,Any]]=[]; explanation:str=''; model:str; latency_ms:int; as_of_date:date|None=None; applied_rules:list[str]=[]
class Route(BaseModel):
 intent:Literal['exact_fact','policy_fact','procedure','personal_data','personal_eligibility','multi_step','not_answerable','clarification_needed','refused']
 entities:dict[str,str]={}
class IngestResponse(BaseModel): doc_id:str; chunks_created:int; status:str
