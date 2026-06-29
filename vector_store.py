import chromadb
from typing import List, Dict, Any
from llm_service import get_embeddings_batch, get_embedding

COLLECTION_NAME = "job_postings"
CHROMA_PATH = "./chroma_db"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def chunk_text(text: str) -> List[str]:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + CHUNK_SIZE, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_len:
            break
        start = end - CHUNK_OVERLAP
    return chunks


def store_job_posting(
    posting_id: int, company_name: str, role_title: str, text: str
) -> int:
    collection = get_collection()
    chunks = chunk_text(text)
    if not chunks:
        return 0

    _delete_posting_vectors(collection, posting_id)

    embeddings = get_embeddings_batch(chunks)
    ids = [f"{posting_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "company_name": company_name,
            "role_title": role_title,
            "chunk_index": i,
            "posting_id": str(posting_id),
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)


def search_similar_chunks(query: str, n_results: int = 6) -> List[Dict[str, Any]]:
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    n = min(n_results, total)
    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        chunks.append(
            {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": distance,
                "relevance_score": round((1 - distance) * 100, 1),
            }
        )
    return chunks


def deduplicate_by_posting(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only the highest-relevance chunk per unique posting_id."""
    seen: Dict[str, Dict] = {}
    for chunk in chunks:
        pid = chunk["metadata"]["posting_id"]
        if pid not in seen or chunk["relevance_score"] > seen[pid]["relevance_score"]:
            seen[pid] = chunk
    return list(seen.values())


def delete_job_posting(posting_id: int) -> None:
    collection = get_collection()
    _delete_posting_vectors(collection, posting_id)


def _delete_posting_vectors(collection, posting_id: int) -> None:
    try:
        results = collection.get(
            where={"posting_id": str(posting_id)},
            include=["documents"],
        )
        if results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass


def get_total_chunks() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0
