import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS students (student_id TEXT PRIMARY KEY, full_name TEXT, programme TEXT, batch_year INTEGER, current_semester INTEGER, cgpa REAL CHECK(cgpa BETWEEN 0 AND 10), active_backlogs INTEGER CHECK(active_backlogs >= 0));
CREATE TABLE IF NOT EXISTS courses (course_code TEXT PRIMARY KEY, course_name TEXT, programme TEXT, semester INTEGER, credits INTEGER);
CREATE TABLE IF NOT EXISTS attendance (student_id TEXT, course_code TEXT, classes_held INTEGER CHECK(classes_held > 0), classes_attended INTEGER CHECK(classes_attended <= classes_held), PRIMARY KEY(student_id,course_code), FOREIGN KEY(student_id) REFERENCES students(student_id), FOREIGN KEY(course_code) REFERENCES courses(course_code));
CREATE TABLE IF NOT EXISTS results (student_id TEXT, course_code TEXT, exam_session TEXT, exam_type TEXT DEFAULT 'END_SEM', internal_marks INTEGER CHECK(internal_marks>=0), external_marks INTEGER CHECK(external_marks>=0), total_marks INTEGER CHECK(total_marks>=0 AND total_marks<=max_marks AND total_marks=internal_marks+external_marks), max_marks INTEGER CHECK(max_marks>0), result TEXT CHECK(result IN ('PASS','FAIL','ABSENT','DETAINED')), PRIMARY KEY(student_id,course_code,exam_session), FOREIGN KEY(student_id) REFERENCES students(student_id), FOREIGN KEY(course_code) REFERENCES courses(course_code));
CREATE TABLE IF NOT EXISTS rule_registry (rule_id TEXT PRIMARY KEY, description TEXT, parameter TEXT, operator TEXT, value TEXT, scope_programme TEXT, scope_batches TEXT, effective_from TEXT, effective_to TEXT, source_doc_id TEXT, source_section TEXT);
CREATE TABLE IF NOT EXISTS source_register (doc_id TEXT PRIMARY KEY, title TEXT, issuer TEXT, authority_level INTEGER, doc_type TEXT, version TEXT, effective_from TEXT, effective_to TEXT, supersedes TEXT, scope_programme TEXT, scope_batches TEXT, provenance TEXT, retrieved_on TEXT, synthetic TEXT);
CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, text TEXT);
CREATE TABLE IF NOT EXISTS audits (trace_id TEXT PRIMARY KEY, timestamp TEXT, payload TEXT);
'''

@contextmanager
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row
    try: yield c; c.commit()
    finally: c.close()

def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        columns=[r[1] for r in c.execute('PRAGMA table_info(results)')]
        if 'exam_type' not in columns: c.execute("ALTER TABLE results ADD COLUMN exam_type TEXT DEFAULT 'END_SEM'")
