"""Generate/reseed reproducible synthetic data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.seed import seed
seed(); print('Synthetic student dataset is present.')
