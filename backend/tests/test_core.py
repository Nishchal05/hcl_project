from app.policy.source_precedence import resolve
from app.tools import attendance
from app.seed import seed
from app.db import conn
from app.main import ask, student
from app.graph import graph
from app.rag import index_document,search,remove_document
from app.rag import sections
from app.retrieval import retrieve
from app.schemas import AskRequest
from fastapi import HTTPException
from datetime import date

def setup_module(): seed()
def test_attendance_is_deterministic():
    assert attendance('S1001','CS201')['attendance_percentage']==78.57
def test_supersession_wins():
    docs=[{'doc_id':'old','authority_level':1,'effective_from':'2023-01-01','effective_to':'','scope_programme':'ALL','scope_batches':'','supersedes':''},{'doc_id':'new','authority_level':1,'effective_from':'2024-01-01','effective_to':'','scope_programme':'ALL','scope_batches':'','supersedes':'old'}]
    selected,conflicts,_=resolve(docs,'2025-01-01'); assert selected[0]['doc_id']=='new' and not conflicts
def test_equal_sources_conflict():
    docs=[{'doc_id':x,'authority_level':1,'effective_from':'2024-01-01','effective_to':'','scope_programme':'ALL','scope_batches':'','supersedes':''} for x in ('a','b')]
    selected,conflicts,_=resolve(docs,'2025-01-01');assert not selected and len(conflicts)==2
def test_ask_and_audit():
    r=ask(AskRequest(question='What is my attendance in CS201?'),'S1001')
    assert r.answer_type=='calculated'
    with conn() as c: assert c.execute('SELECT 1 FROM audits WHERE trace_id=?',(r.trace_id,)).fetchone()
def test_other_student_refused():
    try: student('S1002','S1001'); assert False
    except HTTPException as e: assert e.status_code==403
def test_as_of_date_selects_historical_version():
    docs=[{'doc_id':'old','authority_level':1,'effective_from':'2023-01-01','effective_to':'2024-06-30','scope_programme':'ALL','scope_batches':'','supersedes':''},{'doc_id':'new','authority_level':1,'effective_from':'2024-07-01','effective_to':'','scope_programme':'ALL','scope_batches':'','supersedes':'old'}]
    selected,_,_=resolve(docs,'2024-01-01'); assert selected[0]['doc_id']=='old'
    selected,_,_=resolve(docs,'2025-01-01'); assert selected[0]['doc_id']=='new'
def test_future_policy_is_not_applicable():
    docs=[{'doc_id':'future','authority_level':1,'effective_from':'2099-01-01','effective_to':'','scope_programme':'ALL','scope_batches':'','supersedes':''}]
    selected,_,_=resolve(docs,'2026-01-01');assert not selected
def test_what_if_does_not_change_database():
    before=attendance('S1001','CS201');state=graph.invoke({'question':'If I pass my supplementary exam, will I become eligible for placement?','student_id':'S1001','as_of_date':'2026-10-08'});after=attendance('S1001','CS201')
    assert state['answer_type']=='not_found' and before==after
def test_new_document_is_retrievable_without_code_changes():
    doc_id='TEST-LIBRARY-POLICY-2026'
    index_document(doc_id,'Library Coordinator: Dr. Test Person. Library borrowing period is 14 days.',{'title':'Library Policy 2026','issuer':'Library','authority_level':2,'doc_type':'policy','version':'1.0','effective_from':'2026-01-01','effective_to':'','supersedes':'','scope_programme':'ALL','scope_batches':'','provenance':'test','synthetic':'Y'})
    try:
        assert any(x['doc_id']==doc_id for x in search('Who is the library coordinator?',5))
    finally: remove_document(doc_id)
def test_section_parser_does_not_bleed_between_numbered_sections():
    text='EXPERIMENT 1\nFirst experiment evidence.\nEXPERIMENT 2\nSecond experiment evidence.'
    parsed=dict(sections(text))
    assert parsed['EXPERIMENT 1']=='First experiment evidence.'
    assert 'Second experiment' not in parsed['EXPERIMENT 1']
def test_topic_title_outweighs_unrelated_vector_candidate():
    results=retrieve('what is placement policy')
    assert results and results[0]['doc_id']=='DEMO-PLACEMENT-POLICY-2026'
