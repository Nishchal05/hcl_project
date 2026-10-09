import re
from .db import conn
from .config import TOP_K
from .rag import search
STOPWORDS={'the','and','for','with','what','how','are','can','you','your','from','this','that','about','exam','examination','student','students'}
def retrieve(question):
    try:
        hits=search(question)
        if hits: return hits
    except Exception:
        pass
    tokens=set(re.findall(r'[a-z]{3,}',question.lower()))-STOPWORDS
    with conn() as c:
        rows=[dict(x) for x in c.execute('SELECT d.doc_id,d.text,s.* FROM documents d JOIN source_register s USING(doc_id)')]
    scored=[]
    for r in rows:
        score=len(tokens & (set(re.findall(r'[a-z]{3,}',r['text'].lower()))-STOPWORDS))
        if score: scored.append((score,r))
    return [r for _,r in sorted(scored,key=lambda x:x[0],reverse=True)[:TOP_K]]
def citation(d, section='Relevant section'):
    return {'doc_id':d['doc_id'],'title':d['title'],'section':section,'page':None,'version':d['version'],'effective_date':d['effective_from']}
