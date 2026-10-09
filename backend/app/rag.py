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
def index_document(doc_id,text,metadata):
 col=collection();parts=chunks(text);ids=[f'{doc_id}:{i}' for i in range(len(parts))]
 metas=[{**{k:str(v or '') for k,v in metadata.items()},'doc_id':doc_id,'scope_programmes':str(metadata.get('scope_programme','ALL') or 'ALL'),'chunk_id':ids[i],'section':'Document text','page':'1'} for i in range(len(parts))]
 col.upsert(ids=ids,documents=parts,metadatas=metas);return len(parts)
def remove_document(doc_id):
 col=collection(); found=col.get(where={'doc_id':doc_id},include=[])
 if found['ids']: col.delete(ids=found['ids'])
def rebuild(documents):
 """Development maintenance: recreate all vector chunks using current settings."""
 client=PersistentClient(path=str(CHROMA_PATH))
 try: client.delete_collection('university_documents_v2')
 except Exception: pass
 for doc in documents: index_document(doc['doc_id'],doc['text'],doc)
 return len(documents)
def search(question,top_k=TOP_K):
 col=collection();r=col.query(query_texts=[question],n_results=top_k,include=['documents','metadatas','distances'])
 return [{**r['metadatas'][0][i],'text':r['documents'][0][i],'distance':r['distances'][0][i]} for i in range(len(r['ids'][0]))]
