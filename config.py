import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("maritime_ai")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "ais_sample_data.csv")
STATIC_DIR = os.path.join(BASE_DIR, "static")
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "faiss_index")

os.makedirs(STATIC_DIR, exist_ok=True)