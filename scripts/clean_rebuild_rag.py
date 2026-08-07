"""Clean and rebuild ChromaDB vector collection cleanly.
Deletes the existing collection first to prevent duplicate embeddings.
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.services.rag_service import get_chroma_client, get_collection_count
from scripts.rebuild_rag_index import main as rebuild_main

logger = logging.getLogger("clean_rag_rebuild")

def reset_and_rebuild():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    client = get_chroma_client()
    
    collection_name = settings.chroma_collection_name
    logger.info("Cleaning existing collection '%s' to eliminate duplicates...", collection_name)
    
    try:
        client.delete_collection(collection_name)
        logger.info("Collection '%s' successfully deleted.", collection_name)
    except Exception as e:
        logger.info("Collection deletion notice: %s", e)
        
    logger.info("Rebuilding clean vector index...")
    rebuild_main()
    logger.info("Clean rebuild complete! Total unique embeddings: %d", get_collection_count())

if __name__ == "__main__":
    reset_and_rebuild()
