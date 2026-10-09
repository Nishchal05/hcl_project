"""Validate synthetic relational data without mutating it."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import conn
def main():
 with conn() as c:
  checks=[("invalid student IDs","SELECT count(*) FROM students WHERE student_id NOT GLOB 'S[0-9][0-9][0-9][0-9]'"),("invalid attendance","SELECT count(*) FROM attendance WHERE classes_held<=0 OR classes_attended<0 OR classes_attended>classes_held"),("invalid marks","SELECT count(*) FROM results WHERE internal_marks<0 OR external_marks<0 OR total_marks!=internal_marks+external_marks OR total_marks>max_marks"),("invalid CGPA/backlogs","SELECT count(*) FROM students WHERE cgpa<0 OR cgpa>10 OR active_backlogs<0")]
  failures=[name for name,sql in checks if c.execute(sql).fetchone()[0]]
 if failures: raise SystemExit('Validation failed: '+', '.join(failures))
 print('Synthetic data validation passed.')
if __name__=='__main__':main()
