from .db import init_db,conn
from .config import DOCS
from datetime import date
import csv
from .rag import index_document
DOCS_DATA=[
 ('ACAD-REG-2023','Academic Regulations for B.Tech (Synthetic Demo)','Office of Dean (Academics)',1,'regulation','2.0','2023-07-01','2024-06-30','', 'ALL','2023+','Academic regulation: Students require a minimum attendance of 70% for end-semester examination. This synthetic document expired on 2024-06-30.'),
 ('ACAD-REG-2024','Academic Regulations for B.Tech (Synthetic Demo)','Office of Dean (Academics)',1,'regulation','3.1','2024-07-01','','ACAD-REG-2023#7.2','ALL','2023+','Section 7.2 Attendance: A student must maintain at least 75% attendance in each registered course to appear in the end-semester examination. This is a synthetic demo regulation.'),
 ('EXAM-RULES-2024','Examination and Supplementary Rules (Synthetic Demo)','Controller of Examinations',1,'regulation','1.0','2024-07-01','','','ALL','2023+','Section 5 Supplementary examination: A student who receives FAIL in a course may apply for supplementary examination, provided the student has attendance of at least 75% in that course. Apply through the examination portal within seven days of result publication. This is synthetic demo content.'),
 ('ATT-CIRCULAR-2024','Attendance Circular (Synthetic Demo)','Academic Office',2,'circular','1.0','2024-08-01','','','ALL','2023+','The Academic Office recommends 80% attendance. This circular does not supersede Academic Regulations and cannot override the regulation.'),
 ('CSE-NOTICE-2024','CSE Department Notice (Synthetic Demo)','CSE Department',3,'notice','1.0','2024-07-01','','','BTECH_CSE','2024+','CSE students should consult advisors for attendance support. This notice is informational only.')]
def seed():
 init_db(); DOCS.mkdir(parents=True,exist_ok=True)
 with conn() as c:
  if c.execute('SELECT count(*) FROM students').fetchone()[0] and c.execute('SELECT count(*) FROM results').fetchone()[0]: return
  students=[]
  for i in range(1,31):
   sid=f'S{1000+i}'; prog='BTECH_CSE' if i<=15 else 'BTECH_ECE'; batch=2023 if i%2 else 2024
   students.append((sid,f'Demo Student {i:02d}',prog,batch,4,round(6.5+i*.1,2),1 if i in (1,5,12) else 0))
  c.executemany('INSERT OR IGNORE INTO students VALUES (?,?,?,?,?,?,?)',students)
  courses=[('CS201','Data Structures','BTECH_CSE',3,4),('CS202','Algorithms','BTECH_CSE',4,4),('EC201','Signals and Systems','BTECH_ECE',3,4),('EC202','Digital Systems','BTECH_ECE',4,4),('HS201','Technical Communication','BTECH_CSE',3,2),('MA201','Discrete Mathematics','BTECH_ECE',3,4)]
  c.executemany('INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?)',courses)
  for i in range(1,31):
   sid=f'S{1000+i}'; course='CS201' if i<=15 else 'EC201'; held=28; attended=22 if i==1 else (21 if i==2 else (20 if i==3 else 25))
   c.execute('INSERT OR IGNORE INTO attendance VALUES (?,?,?,?)',(sid,course,held,attended)); total=42 if i in (1,5,12) else 70
   c.execute('INSERT OR IGNORE INTO results (student_id,course_code,exam_session,internal_marks,external_marks,total_marks,max_marks,result) VALUES (?,?,?,?,?,?,?,?)',(sid,course,'2024-DEC',20,total-20,total,100,'FAIL' if total<50 else 'PASS'))
  for doc in DOCS_DATA:
   meta=doc[:11]; text=doc[11]; c.execute('INSERT OR IGNORE INTO source_register VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(*meta,'https://example.edu/synthetic',str(date.today()),'Y'))
   c.execute('INSERT OR IGNORE INTO documents VALUES (?,?)',(doc[0],text)); (DOCS/f'{doc[0]}.md').write_text(f'# {doc[1]}\n\n{text}',encoding='utf-8')
   index_document(doc[0],text,dict(c.execute('SELECT * FROM source_register WHERE doc_id=?',(doc[0],)).fetchone()))
  rules=[('ATT-MIN-01','Minimum attendance for end semester','attendance_percentage','>=','75','ALL','2023+','2024-07-01','','ACAD-REG-2024','7.2'),('SUPP-01','Supplementary eligibility','result','=','FAIL','ALL','2023+','2024-07-01','','EXAM-RULES-2024','5')]
  c.executemany('INSERT OR IGNORE INTO rule_registry VALUES (?,?,?,?,?,?,?,?,?,?,?)',rules)
  with open(DOCS.parent/'source_register.csv','w',newline='',encoding='utf-8') as f:
   w=csv.writer(f);w.writerow(['doc_id','title','issuer','authority_level','doc_type','version','effective_from','effective_to','supersedes','scope_programme','scope_batches','provenance','retrieved_on','synthetic']);w.writerows(c.execute('SELECT * FROM source_register'))
