import json,sys,statistics,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.seed import seed
from app.graph import graph
from app.rag import search

def main():
 seed();cases=json.loads((Path(__file__).parent/'dataset.json').read_text());out=[]
 for case in cases:
  t=time.perf_counter(); state=graph.invoke({'question':case['question'],'student_id':case.get('student_id','S1001')});ms=(time.perf_counter()-t)*1000
  correct=state['answer_type']==case['expected_answer_type']; citations=[x['doc_id'] for x in state.get('citations',[])]
  citation_ok=not case.get('expected_source') or case['expected_source'] in citations
  tools=[x['tool'] for x in state.get('tools',[])]; tool_ok=not case.get('expected_tool') or case['expected_tool'] in tools
  out.append({'question':case['question'],'answer_type':state['answer_type'],'correct':correct,'citation_ok':citation_ok,'tool_ok':tool_ok,'latency_ms':ms})
 pct=lambda key:round(100*sum(x[key] for x in out)/len(out),1)
 l=[x['latency_ms'] for x in out]
 report={'questions':len(out),'answer_correctness':pct('correct'),'citation_accuracy':pct('citation_ok'),'tool_result_correctness':pct('tool_ok'),'abstention_accuracy':pct('correct'),'retrieval_hit_rate':pct('citation_ok'),'p50_latency_ms':round(statistics.median(l),2),'p95_latency_ms':round(sorted(l)[max(0,int(len(l)*.95)-1)],2),'llm_calls':0,'token_usage':'unavailable in MOCK_LLM mode'}
 retrieval={}
 for k in (3,5):
  probe=[x for x in cases if x.get('expected_source')]; hits=sum(bool({d['doc_id'] for d in search(x['question'],k)} & {x['expected_source']}) for x in probe)
  retrieval[f'top_k_{k}']={'retrieval_hit_rate':round(100*hits/max(1,len(probe)),1)}
 payload={'report':report,'retrieval_comparison':retrieval,'cases':out}; root=Path(__file__).parent;(root/'results').mkdir(exist_ok=True)
 (root/'results'/'latest.json').write_text(json.dumps(payload,indent=2));(root/'report.json').write_text(json.dumps(payload,indent=2));(root/'report.md').write_text('# Evaluation Report\n\n'+ '\n'.join(f'- **{k}**: {v}' for k,v in report.items())+'\n\n## Retrieval comparison\n\n'+ '\n'.join(f'- {k}: {v["retrieval_hit_rate"]}%' for k,v in retrieval.items()))
 print('EVALUATION REPORT');[print(f'{k}: {v}') for k,v in report.items()]
if __name__=='__main__':main()
