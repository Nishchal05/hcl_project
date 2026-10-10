from pathlib import Path
import os
try:
 from dotenv import load_dotenv
 load_dotenv(Path(__file__).resolve().parents[2] / '.env')
except ImportError:
 pass

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv("DATA_DIR", str(ROOT / "data"))).resolve()
DB_PATH = DATA / "university.db"
DOCS = DATA / "documents"
CHROMA_PATH = DATA / "chroma"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
TOP_K = int(os.getenv("TOP_K", "5"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
MOCK_LLM = os.getenv("MOCK_LLM", "true").lower() == "true"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
