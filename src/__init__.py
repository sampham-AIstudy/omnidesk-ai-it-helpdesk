import os
import sys

# Mitigate native SentenceTransformer / safetensors async loader race conditions on Windows.
if sys.platform == "win32":
    os.environ.setdefault("HF_DEACTIVATE_ASYNC_LOAD", "1")
