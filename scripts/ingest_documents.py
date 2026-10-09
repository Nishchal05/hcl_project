import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.seed import seed
seed(); print('Seed documents are available for retrieval.')
