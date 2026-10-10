import re
from .db import conn
from .config import TOP_K
from .rag import search
from .rag import sections
STOPWORDS={'the','and','for','with','what','how','are','can','you','your','from','this','that','about','exam','examination','student','students'}
def retrieve(question):
    """Hybrid global retrieval: vector candidates plus deterministic lexical reranking.

    This protects clear document/topic questions (for example "placement policy")
    when a lightweight/offline embedding fallback ranks an unrelated chunk highly.
    """
    vector_hits=[]
    try:
        vector_hits=search(question,TOP_K)
    except Exception:
        pass
    tokens=set(re.findall(r'[a-z0-9]{3,}',question.lower()))-STOPWORDS
    with conn() as c:
        rows=[dict(x) for x in c.execute('SELECT d.doc_id,d.text,s.* FROM documents d JOIN source_register s USING(doc_id)')]
    vector_by_id={hit['doc_id']:hit for hit in vector_hits}
    scored=[]
    for r in rows:
        title=(r.get('title') or '').lower(); doc_type=(r.get('doc_type') or '').lower(); text=r['text'].lower()
        # Exact title/topic terms are strongest, then body frequency. A vector
        # hit adds a modest tie-breaker rather than overriding explicit evidence.
        title_score=sum(8*title.count(token) for token in tokens)
        type_score=sum(3 for token in tokens if token==doc_type)
        body_score=sum(min(text.count(token),4) for token in tokens)
        vector_score=1 if r['doc_id'] in vector_by_id else 0
        score=title_score+type_score+body_score+vector_score
        if score: scored.append((score,r))
    if scored:return [r for _,r in sorted(scored,key=lambda x:(x[0],x[1]['doc_id']),reverse=True)[:TOP_K]]
    return vector_hits
def exact_section(question):
    """Find a numbered/generic named section across the whole authoritative corpus."""
    target=re.search(r'\b(experiment|section|chapter|module|unit)\s+([\divxlcdm]+)\b',question,re.I)
    if not target:return []
    needle=' '.join(target.group(0).lower().split())
    with conn() as c: rows=[dict(x) for x in c.execute('SELECT d.doc_id,d.text,s.* FROM documents d JOIN source_register s USING(doc_id)')]
    found=[]
    for doc in rows:
        for title,body in sections(doc['text']):
            if needle== ' '.join(title.lower().split()).split(':')[0]:
                found.append({**doc,'text':body,'section':title})
    return found
def citation(d, section='Relevant section'):
    return {'doc_id':d['doc_id'],'title':d['title'],'section':d.get('section') or section,'page':d.get('page'),'version':d['version'],'effective_date':d['effective_from']}
