from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from .schemas import AskRequest,AskResponse,IngestResponse
from .seed import seed
from .db import conn
from .graph import graph
from .config import OLLAMA_BASE_URL,OLLAMA_MODEL,MOCK_LLM,EMBEDDING_MODEL,MAX_UPLOAD_MB,DEMO_MODE
from .tools import profile
from .rag import index_document,remove_document,rebuild,chunks,embeddings
from .llm import explain
import uuid,time,json,datetime,httpx,csv

app=FastAPI(title='University Student Services Assistant',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173'],allow_methods=['*'],allow_headers=['*'])
@app.on_event('startup')
def startup(): seed()
def require_student(sid):
 if not sid or not profile(sid): raise HTTPException(401,'A valid X-Student-Id header is required.')
 return sid
@app.post('/ask',response_model=AskResponse)
def ask(body:AskRequest,x_student_id:str|None=Header(default=None)):
 sid=require_student(x_student_id); started=time.perf_counter(); trace=uuid.uuid4().hex[:12]
 as_of=body.as_of_date or datetime.date.today();state=graph.invoke({'question':body.question,'student_id':sid,'as_of_date':str(as_of)}); latency=round((time.perf_counter()-started)*1000)
 final_answer,llm_info=explain(state['answer'],[d.get('text','')[:500] for d in state.get('selected',[])],state.get('tools',[])); response=AskResponse(trace_id=trace,answer=final_answer,answer_type=state['answer_type'],citations=state.get('citations',[]),tool_results=state.get('tools',[]),conflicts=[{'doc_id':x['doc_id'],'title':x['title']} for x in state.get('conflicts',[])],explanation=state.get('explanation',''),model='MOCK_LLM' if MOCK_LLM else OLLAMA_MODEL,latency_ms=latency,as_of_date=as_of,applied_rules=state.get('rules',[]))
 audit={'trace_id':trace,'timestamp':datetime.datetime.now(datetime.UTC).isoformat(),'student_id':sid,'question':body.question,'question_type':state.get('qtype'),'as_of_date':str(as_of),'sources_retrieved':[d['doc_id'] for d in state.get('docs',[])],'sources_selected':[d['doc_id'] for d in state.get('selected',[])],'precedence_decision':state.get('precedence'),'tools_invoked':[item.model_dump() for item in response.tool_results],'applied_rules':response.applied_rules,'answer_type':response.answer_type,'model':response.model,'llm_calls':llm_info['calls'],'latency_ms':latency,'tokens':llm_info['tokens'],'conflicts_detected':response.conflicts,'final_answer':response.answer}
 with conn() as c:c.execute('INSERT INTO audits VALUES (?,?,?)',(trace,audit['timestamp'],json.dumps(audit)))
 return response
@app.get('/audit/{trace_id}')
def audit(trace_id:str):
 with conn() as c:r=c.execute('SELECT payload FROM audits WHERE trace_id=?',(trace_id,)).fetchone()
 if not r:raise HTTPException(404,'Audit record not found.')
 return json.loads(r['payload'])
@app.get('/sources')
def sources():
 with conn() as c:return [dict(r) for r in c.execute('SELECT * FROM source_register ORDER BY authority_level,effective_from DESC')]
@app.delete('/sources/{doc_id}')
def delete_source(doc_id:str):
 """Remove an ingested source and all of its vector chunks (admin/demo maintenance)."""
 with conn() as c:
  if not c.execute('SELECT 1 FROM source_register WHERE doc_id=?',(doc_id,)).fetchone(): raise HTTPException(404,'Source not found.')
  c.execute('DELETE FROM documents WHERE doc_id=?',(doc_id,));c.execute('DELETE FROM source_register WHERE doc_id=?',(doc_id,))
 remove_document(doc_id)
 return {'doc_id':doc_id,'status':'removed'}
@app.post('/reindex')
def reindex():
 """Development/admin operation; rebuilds the global Chroma index from source records."""
 with conn() as c: documents=[dict(r) for r in c.execute('SELECT d.doc_id,d.text,s.* FROM documents d JOIN source_register s USING(doc_id)')]
 return {'status':'rebuilt','documents_indexed':rebuild(documents),'embedding_model':EMBEDDING_MODEL}
@app.get('/rules')
def rules():
 with conn() as c:return [dict(r) for r in c.execute('SELECT * FROM rule_registry')]
@app.get('/demo/students')
def demo_students():
 """Demo-only selector data: IDs only, never personal student records."""
 if not DEMO_MODE: raise HTTPException(404,'Demo mode is disabled.')
 with conn() as c:return [{'student_id':r['student_id']} for r in c.execute('SELECT student_id FROM students ORDER BY student_id')]
@app.get('/student/{student_id}')
def student(student_id:str,x_student_id:str|None=Header(default=None)):
 require_student(x_student_id)
 if student_id!=x_student_id:raise HTTPException(403,'You may only access your own student record.')
 return profile(student_id)
@app.post('/ingest',response_model=IngestResponse)
async def ingest(file:UploadFile=File(...),doc_id:str=Form(...),title:str=Form(...),issuer:str=Form(...),authority_level:int=Form(...),doc_type:str=Form(...),version:str=Form(...),effective_from:str=Form(...),effective_to:str=Form(''),supersedes:str=Form(''),scope_programme:str=Form('ALL'),scope_batches:str=Form(''),provenance:str=Form('uploaded'),synthetic:str=Form('Y')):
 if file.content_type not in ('text/plain','text/markdown','application/pdf') and not file.filename.endswith(('.txt','.md')): raise HTTPException(400,'Only TXT, Markdown, and PDF metadata uploads are supported in this demo.')
 raw=await file.read()
 if len(raw)>MAX_UPLOAD_MB*1024*1024:raise HTTPException(413,f'Document exceeds {MAX_UPLOAD_MB}MB limit.')
 if file.content_type=='application/pdf' or file.filename.endswith('.pdf'):
  try:
   from pypdf import PdfReader
   from io import BytesIO
   text='\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(raw)).pages)
  except Exception: raise HTTPException(400,'Unable to extract text from PDF.')
 else:text=raw.decode('utf-8','replace')
 if not text.strip(): raise HTTPException(400,'No readable text was found. Use an OCR/extracted TXT file for scanned PDFs.')
 with conn() as c:
  # Re-uploading a document ID replaces its chunks and metadata, avoiding stale duplicate retrieval.
  c.execute('DELETE FROM documents WHERE doc_id=?',(doc_id,));c.execute('DELETE FROM source_register WHERE doc_id=?',(doc_id,));remove_document(doc_id)
  c.execute('INSERT INTO source_register VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(doc_id,title,issuer,authority_level,doc_type,version,effective_from,effective_to,supersedes,scope_programme,scope_batches,provenance,str(datetime.date.today()),synthetic));c.execute('INSERT INTO documents VALUES (?,?)',(doc_id,text));index_document(doc_id,text,{'doc_id':doc_id,'title':title,'issuer':issuer,'authority_level':authority_level,'doc_type':doc_type,'version':version,'effective_from':effective_from,'effective_to':effective_to,'supersedes':supersedes,'scope_programme':scope_programme,'scope_batches':scope_batches,'provenance':provenance,'synthetic':synthetic})
  rows=list(c.execute('SELECT * FROM source_register'))
 with open(__import__('pathlib').Path(__file__).resolve().parents[2]/'data'/'source_register.csv','w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['doc_id','title','issuer','authority_level','doc_type','version','effective_from','effective_to','supersedes','scope_programme','scope_batches','provenance','retrieved_on','synthetic']);w.writerows(rows)
 return IngestResponse(doc_id=doc_id,chunks_created=len(chunks(text)),status='available')
@app.get('/health')
async def health():
 sqlite_ok=True
 try:
  with conn() as c:c.execute('SELECT 1')
 except Exception:sqlite_ok=False
 try: ollama=(await httpx.AsyncClient(timeout=1).get(f'{OLLAMA_BASE_URL}/api/tags')).status_code==200
 except Exception:ollama=False
 return {'api':'ok','sqlite':'ok' if sqlite_ok else 'unavailable','chromadb':'ok','ollama':'mock' if MOCK_LLM else ('ok' if ollama else 'unavailable'),'llm_mode':'MOCK_LLM' if MOCK_LLM else 'OLLAMA','embedding_model':EMBEDDING_MODEL,'embedding_runtime':embeddings.mode,'model':OLLAMA_MODEL}
