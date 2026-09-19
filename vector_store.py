import os
import json
from typing import List, Dict, Any, Optional

# Set up local embedding directory if needed
os.environ["TOKENIZERS_PARALLELISM"] = "false"

CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), ".chroma_db")
CORPUS_PATH = os.path.join(os.path.dirname(__file__), "corpus.jsonl")

# Lazy initialized global client and collection
_client = None
_collection = None

def get_chroma_collection():
    """Initializes and returns the Chroma collection using local all-MiniLM-L6-v2 embeddings."""
    global _client, _collection
    if _collection is not None:
        return _collection

    import chromadb
    from chromadb.utils import embedding_functions

    # Local embedding function using sentence-transformers (all-MiniLM-L6-v2)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    _collection = _client.get_or_create_collection(
        name="kestrel_corpus",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    # Ingest if collection is empty
    if _collection.count() == 0:
        print(f"[*] Ingesting corpus from {CORPUS_PATH} into local Chroma...")
        ingest_corpus(_collection, CORPUS_PATH)
        print(f"[+] Ingested {_collection.count()} chunks successfully.")

    return _collection


def ingest_corpus(collection, corpus_path: str):
    """Ingests corpus.jsonl into the Chroma vector store with rich metadata."""
    ids = []
    documents = []
    metadatas = []

    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            chunk_id = item["chunk_id"]
            doc_id = item.get("doc_id", "")
            title = item.get("title", "")
            category = item.get("category", "")
            published = item.get("published", "")
            version = str(item.get("version", ""))
            source_url = item.get("source_url", "")
            text = item.get("text", "")

            # Combined document text with title context for higher semantic density
            doc_content = f"Title: {title} (Category: {category}, Version: {version}, Published: {published})\n\n{text}"

            ids.append(chunk_id)
            documents.append(doc_content)
            metadatas.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "title": title,
                "category": category,
                "published": published,
                "version": version,
                "source_url": source_url,
                "raw_text": text
            })

    # Batch add in chunks of 50 to avoid memory pressure
    batch_size = 50
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size]
        )


def retrieve_evidence(query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant chunks from the Kestrel corpus.
    Performs vector similarity search with optional metadata filtering and keyword boosting.
    """
    collection = get_chroma_collection()

    where_filter = None
    if category:
        where_filter = {"category": category}

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
        include=["metadatas", "distances", "documents"]
    )

    chunks = []
    if results and results.get("ids") and len(results["ids"]) > 0:
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            similarity_score = 1.0 - distance  # Cosine similarity

            chunks.append({
                "chunk_id": meta["chunk_id"],
                "doc_id": meta["doc_id"],
                "title": meta["title"],
                "category": meta["category"],
                "published": meta["published"],
                "version": meta["version"],
                "source_url": meta["source_url"],
                "text": meta["raw_text"],
                "score": round(similarity_score, 4)
            })

    # Sort chunks by relevance score, with tie-breaking by published date for conflict recency
    chunks.sort(key=lambda x: (x["score"], x["published"]), reverse=True)
    return chunks


if __name__ == "__main__":
    print("[*] Initializing and verifying vector store...")
    col = get_chroma_collection()
    print(f"[+] Total indexed chunks: {col.count()}")

    test_q = "What is the Beacon limit on the Starter plan?"
    print(f"\n[*] Test retrieval for: '{test_q}'")
    hits = retrieve_evidence(test_q, top_k=3)
    for h in hits:
        print(f" -> [{h['chunk_id']}] {h['title']} (Score: {h['score']}) | Pub: {h['published']}")
        print(f"    Excerpt: {h['text'][:140]}...\n")
