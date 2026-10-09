from .db import conn
def _one(sql,args=()):
    with conn() as c:
        row=c.execute(sql,args).fetchone(); return dict(row) if row else None
def profile(student_id): return _one('SELECT * FROM students WHERE student_id=?',(student_id,))
def attendance(student_id, course_code):
    row=_one('SELECT a.*,c.course_name FROM attendance a JOIN courses c USING(course_code) WHERE student_id=? AND course_code=?',(student_id,course_code.upper()))
    if row: row['attendance_percentage']=round(row['classes_attended']/row['classes_held']*100,2)
    return row
def result(student_id, course_code): return _one('SELECT * FROM results WHERE student_id=? AND course_code=? ORDER BY exam_session DESC',(student_id,course_code.upper()))
def rules(as_of_date=None, programme='ALL', batch=9999):
    with conn() as c:return [dict(x) for x in c.execute('SELECT * FROM rule_registry')]
def _rule(parameter, as_of_date=None, programme='ALL', batch=9999):
 from datetime import date
 when=str(as_of_date or date.today())
 candidates=[r for r in rules() if r['parameter']==parameter and r['effective_from']<=when and (not r['effective_to'] or r['effective_to']>when)]
 candidates=[r for r in candidates if r['scope_programme'] in ('ALL','',programme)]
 candidates=[r for r in candidates if not r['scope_batches'].endswith('+') or batch>=int(r['scope_batches'][:-1])]
 return sorted(candidates,key=lambda r:r['effective_from'],reverse=True)[0] if candidates else None
def eligibility(student_id, course_code='CS201', as_of_date=None, hypothetical_pass=False):
    a=attendance(student_id,course_code); r=result(student_id,course_code)
    if not a or not r:return {'eligible':False,'reason':'Attendance or result record unavailable'}
    student=profile(student_id); att_rule=_rule('attendance_percentage',as_of_date,student['programme'],student['batch_year']);supp_rule=_rule('result',as_of_date,student['programme'],student['batch_year'])
    threshold=float(att_rule['value']) if att_rule else None; result_value='PASS' if hypothetical_pass else r['result']
    eligible=bool(threshold is not None and a['attendance_percentage']>=threshold and result_value=='FAIL')
    return {'eligible':eligible,'course_code':course_code.upper(),'attendance_percentage':a['attendance_percentage'],'result':result_value,'requirements':{'minimum_attendance':threshold,'must_have_failed_course':True},'applied_rule_ids':[x['rule_id'] for x in (att_rule,supp_rule) if x]}
