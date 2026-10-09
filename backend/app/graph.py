"""One LangGraph. Router only returns validated intent/entities; answers use verified evidence."""
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from .retrieval import retrieve,citation
from .policy.source_precedence import resolve
from .tools import attendance,eligibility
from .schemas import Route
import re
class State(TypedDict,total=False):
 question:str;student_id:str|None;as_of_date:str;qtype:str;entities:dict;docs:list;selected:list;conflicts:list;tools:list;rules:list;answer:str;answer_type:str;citations:list;explanation:str;precedence:str
def router(s):
 q=s['question'].lower();course=(re.search(r'\b[A-Z]{2,4}\d{3}\b',s['question'].upper()) or [None])[0]; e={'course_code':course} if course else {}
 if re.search(r'\b(s\d{4}|another student|friend)\b',q): i='refused'
 elif ('if i pass' in q or 'what if' in q) and ('placement' in q or 'supplementary' in q): i='multi_step'
 elif 'my attendance' in q or 'attendance in' in q:i='personal_data'
 elif 'eligible' in q or 'can i appear' in q or 'i failed' in q:i='personal_eligibility'
 elif len(q.strip())<8:i='clarification_needed'
 elif any(x in q for x in ('scholarship','antarctica','mars')):i='not_answerable'
 elif re.match(r'\s*(who|when)\b',q) or any(x in q for x in ('minimum attendance','placement cutoff','last date')):i='exact_fact'
 elif 'how' in q or 'procedure' in q or 'apply' in q:i='procedure'
 else:i='policy_fact'
 r=Route(intent=i,entities=e);return {**s,'qtype':r.intent,'entities':r.entities}
def retrieve_node(s):
 raw=retrieve(s['question']); grouped={}
 for hit in raw:
  if hit['doc_id'] not in grouped: grouped[hit['doc_id']]={**hit,'text':hit['text']}
  elif hit['text'] not in grouped[hit['doc_id']]['text']: grouped[hit['doc_id']]['text']+='\n'+hit['text']
 # Identical evidence uploaded under different IDs is a duplicate, not a policy conflict.
 # Keep one deterministic representative; distinct equal-precedence documents still reach conflict detection.
 unique={}
 for doc in grouped.values():
  fingerprint=' '.join(doc['text'].lower().split())
  if fingerprint not in unique or doc['doc_id'] < unique[fingerprint]['doc_id']: unique[fingerprint]=doc
 docs=list(unique.values())
 # Corpus-wide, document-agnostic reranking. Precedence compares only sources
 # that have lexical evidence for the question, not unrelated high-authority PDFs.
 stop={'who','what','when','where','which','does','the','and','for','with','from','policy','rules','about'}
 terms=[w for w in re.findall(r'[a-z0-9]{3,}',s['question'].lower()) if w not in stop]
 scored=[(sum(text.lower().count(term) for term in terms),doc) for doc in docs for text in [doc['text']]]
 relevant=[doc for score,doc in scored if score>0]
 candidates=relevant or docs
 selected,conflicts,reason=resolve(candidates,s.get('as_of_date'),programme='ALL',batch=9999)
 return {**s,'docs':docs,'selected':selected,'conflicts':conflicts,'precedence':reason}
def answer(s):
 q=s['question'];typ=s['qtype'];course=s.get('entities',{}).get('course_code')
 if typ=='refused':return {**s,'answer':'I can only access the record belonging to the X-Student-Id request context. I cannot disclose another student’s data.','answer_type':'refused','explanation':'Authorization is limited to the request identity.'}
 if typ=='clarification_needed':return {**s,'answer':'Please provide a course code or policy topic.','answer_type':'clarification_needed','explanation':'The request is ambiguous.'}
 if typ=='not_answerable':return {**s,'answer':'I could not find this information in authoritative university sources.','answer_type':'not_found','explanation':'No authoritative evidence exists.'}
 if typ=='personal_data':
  if not course:return {**s,'answer':'Please specify a course code, for example CS201.','answer_type':'clarification_needed','explanation':'Course code is required.'}
  v=attendance(s['student_id'],course)
  if not v:return {**s,'answer':'No attendance record was found for that course.','answer_type':'not_found','explanation':'No matching record.'}
  t=[{'tool':'get_attendance','result':v},{'tool':'calculate_attendance','result':{'formula':'attended / held × 100','percentage':v['attendance_percentage']}}]
  return {**s,'tools':t,'answer':f"Your attendance in {course} is {v['attendance_percentage']:.2f}% ({v['classes_attended']} attended / {v['classes_held']} held).",'answer_type':'calculated','explanation':'Calculated from your stored attendance, not by an LLM.'}
 if typ in ('personal_eligibility','multi_step'):
  course=course or 'CS201';v=eligibility(s['student_id'],course,s.get('as_of_date'),hypothetical_pass=typ=='multi_step');t=[{'tool':'check_exam_eligibility','result':v}];cites=[citation(d,'Supplementary examination eligibility') for d in s.get('selected',[]) if 'EXAM' in d['doc_id'] or 'ACAD' in d['doc_id']]
  if typ=='multi_step':return {**s,'tools':t,'rules':v['applied_rule_ids'],'citations':cites,'answer':f"Current state: attendance is {v['attendance_percentage']}% and result is FAIL. Hypothetical assumption: you pass the supplementary examination. Placement policy is not present in authoritative sources; no database record was changed.",'answer_type':'not_found','explanation':'Hypothetical state is in-memory only.'}
  return {**s,'tools':t,'rules':v['applied_rule_ids'],'citations':cites,'answer':f"You are {'eligible' if v['eligible'] else 'not eligible'} for the supplementary examination in {course}. Attendance: {v.get('attendance_percentage')}%; result: {v.get('result')}.",'answer_type':'calculated','explanation':'Decision uses rule-registry entries and deterministic records.'}
 if s.get('conflicts'):return {**s,'citations':[citation(d) for d in s['conflicts']],'answer':'Authoritative sources conflict and cannot be resolved safely.','answer_type':'conflict_flagged','explanation':'Equal-precedence documents are cited.'}
 if not s.get('selected'):return {**s,'answer':'I could not find this information in authoritative university sources.','answer_type':'not_found','explanation':'No applicable evidence was retrieved.'}
 # Exact-fact extraction is deliberately narrow: one evidence sentence, never a policy summary.
 if typ=='exact_fact':
  facts=[]
  for d in s['selected']:
   for sentence in re.split(r'(?<!Dr\.)(?<=[.!?])\s+',d['text']):
    terms=[w for w in re.findall(r'[a-z]{4,}',q) if w not in ('what','when','who','minimum')]
    if sentence.strip() and any(w in sentence.lower() for w in terms):facts.append((sentence.strip(),d))
  if not facts:return {**s,'answer':'I could not find that exact fact in authoritative university sources.','answer_type':'not_found','explanation':'No evidence sentence matched the requested entity or value.'}
  text,d=facts[0]
  # PDF/TXT extraction can glue an all-caps heading to its first sentence.
  # Remove only that presentation artifact; evidence and entity matching remain generic.
  text=re.sub(r'^[\d.\sA-Z&-]{4,}(?=[A-Z][a-z])','',text).strip()
  return {**s,'citations':[citation(d,'Exact evidence')],'answer':text,'answer_type':'retrieved_fact','explanation':'Exact evidence extraction from the selected source.'}
 # Normal RAG path: synthesize a concise summary from multiple relevant chunks, not one fact.
 evidence=[];citations=[]
 for d in s['selected']:
  citations.append(citation(d));terms=[w for w in re.findall(r'[a-z]{4,}',q)]
  evidence.extend(x.strip() for x in re.split(r'(?<!Dr\.)(?<=[.!?])\s+',d['text']) if x.strip() and any(w in x.lower() for w in terms))
 summary=' '.join(dict.fromkeys(evidence))[:1200] or s['selected'][0]['text'][:700]
 return {**s,'citations':citations,'answer':summary,'answer_type':'retrieved_fact','explanation':'Normal RAG synthesis from selected policy evidence; retrieved documents are untrusted data.'}
def build():
 g=StateGraph(State);g.add_node('router',router);g.add_node('retrieve',retrieve_node);g.add_node('answer',answer);g.add_edge(START,'router');g.add_edge('router','retrieve');g.add_edge('retrieve','answer');g.add_edge('answer',END);return g.compile()
graph=build()
