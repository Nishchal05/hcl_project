"""Persistent Chroma RAG. Documents remain untrusted evidence, never instructions."""
import hashlib,re
from chromadb import PersistentClient
from .config import CHROMA_PATH, EMBEDDING_MODEL, TOP_K, MOCK_LLM

class Embeddings:
 """Configured local model; deterministic hashing fallback preserves offline mock mode."""
 def __init__(self): self.model=None; self.mode='hashing-fallback'
 def name(self): return 'configured-local-embeddings'
 def embed_query(self,input): return self(input)
 def embed_documents(self,input): return self(input)
 def __call__(self, input):
  try:
   if self.model is None and not MOCK_LLM:
    from sentence_transformers import SentenceTransformer
    self.model=SentenceTransformer(EMBEDDING_MODEL);self.mode=EMBEDDING_MODEL
   if self.model:return self.model.encode(input).tolist()
  except Exception: self.mode='hashing-fallback'
  vectors=[]
  for text in input:
   v=[0.0]*128
   for word in re.findall(r'[a-z0-9]{3,}',text.lower()):v[int(hashlib.sha256(word.encode()).hexdigest(),16)%128]+=1
   norm=sum(x*x for x in v)**.5 or 1;vectors.append([x/norm for x in v])
  return vectors
embeddings=Embeddings()
def collection():
 CHROMA_PATH.mkdir(parents=True,exist_ok=True)
 return PersistentClient(path=str(CHROMA_PATH)).get_or_create_collection('university_documents_v2',embedding_function=embeddings)
def chunks(text,size=800,overlap=120):
 return [text[i:i+size] for i in range(0,max(len(text),1),size-overlap)]
HEADING=re.compile(r'(?im)^(?P<title>(?:experiment|section|chapter|module|unit)\s+[\divxlcdm]+\b[^\n]*|\d+(?:\.\d+)*[.)]?\s+[A-Z][^\n]{2,})\s*$')
def sections(text):
 """Preserve generic heading-delimited units for any uploaded document."""
 matches=list(HEADING.finditer(text))
 if not matches:return [('Document text',text)]
 result=[]
 if text[:matches[0].start()].strip():result.append(('Introduction',text[:matches[0].start()]))
 for index,match in enumerate(matches):
  end=matches[index+1].start() if index+1<len(matches) else len(text)
  result.append((match.group('title').strip(),text[match.end():end].strip()))
 def clean(body):
  # Drop PDF conversion divider lines while preserving all substantive evidence.
  lines=[line.strip() for line in body.splitlines() if not re.fullmatch(r'[-=*_\s]{3,}',line.strip())]
  return '\n'.join(lines).strip()
 return [(title,clean(body)) for title,body in result if clean(body)]
def index_document(doc_id,text,metadata):
 col=collection(); ids=[];documents=[];metas=[]
 for section_index,(title,body) in enumerate(sections(text)):
  for part_index,part in enumerate(chunks(body)):
   chunk_id=f'{doc_id}:s{section_index}:c{part_index}';ids.append(chunk_id);documents.append(part)
   metas.append({**{k:str(v or '') for k,v in metadata.items()},'doc_id':doc_id,'scope_programmes':str(metadata.get('scope_programme','ALL') or 'ALL'),'chunk_id':chunk_id,'section':title,'page':'1'})
 # A legacy/failed upload may have a source-register row but no extractable text.
 # It must not make a global rebuild fail for every valid document.
 if not documents:return 0
 col.upsert(ids=ids,documents=documents,metadatas=metas);return len(documents)
def remove_document(doc_id):
 col=collection(); found=col.get(where={'doc_id':doc_id},include=[])
 if found['ids']: col.delete(ids=found['ids'])
def rebuild(documents):
 """Development maintenance: recreate all vector chunks using current settings."""
 # Replace source-by-source instead of deleting a live collection. This is safe
 # while FastAPI holds an active Chroma collection handle on Windows.
 for doc in documents: remove_document(doc['doc_id'])
 indexed=0
 for doc in documents:
  if index_document(doc['doc_id'],doc['text'],doc)>0:indexed+=1
 return indexed
def search(question,top_k=TOP_K):
 col=collection();r=col.query(query_texts=[question],n_results=top_k,include=['documents','metadatas','distances'])
 return [{**r['metadatas'][0][i],'text':r['documents'][0][i],'distance':r['distances'][0][i]} for i in range(len(r['ids'][0]))]
