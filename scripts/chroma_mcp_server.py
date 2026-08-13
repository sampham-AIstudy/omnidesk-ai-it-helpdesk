"""ChromaDB FastMCP Server for Antigravity IDE."""
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import chromadb
from mcp.server.fastmcp import FastMCP
from src.services.rag_service import embed_query, get_collection

mcp = FastMCP("ChromaDB Vector Store")

CHROMA_PATH = os.getenv("CHROMA_PATH", r"C:\Users\Admin\Python Advanced\VinAI Lab\P-236\data\chroma")

@mcp.tool()
def list_chroma_collections() -> dict:
    """List all vector collections in ChromaDB and their document counts."""
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        cols = client.list_collections()
        return {col.name: col.count() for col in cols}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def query_chroma_documents(collection_name: str, query_text: str, n_results: int = 5) -> dict:
    """Query ChromaDB collection for nearest documents matching query_text."""
    try:
        col = get_collection()
        if col.name != collection_name:
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            col = client.get_collection(collection_name)
        results = col.query(query_embeddings=[embed_query(query_text)], n_results=n_results)
        return {
            "documents": results.get("documents", []),
            "metadatas": results.get("metadatas", []),
            "distances": results.get("distances", []),
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
