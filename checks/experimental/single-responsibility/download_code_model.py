import sys
from pathlib import Path

from code_embeddings import download_code_model

download_code_model(Path(sys.argv[1]))
