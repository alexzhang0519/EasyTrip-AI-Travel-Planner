from Backend.app.rag.base.embeddings import embed_texts

def retrieve(query: str, chunks: list[str], index, top_k: int = 3) -> list[str]:
    """Find the top_k chunks most relevant to the query."""
    query_vector = embed_texts([query])   # embed the question (as a 1-item list)

    # index.search returns distances and the indices of the closest vectors.
    distances, indices = index.search(query_vector, top_k)

    # Map those indices back to the original text chunks.
    return [chunks[i] for i in indices[0] if 0 <= i < len(chunks)]

