import faiss
from Backend.app.rag.base.embeddings import embed_texts

def build_index(chunks: list[str]):
    """Embed all chunks and build a FAISS index for fast similarity search."""
    vectors = embed_texts(chunks)

    # dimension = length of one embedding vector.
    dimension = vectors.shape[1]

    # IndexFlatL2 = exact nearest-neighbor search using L2 (Euclidean) distance.
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)   # store all chunk vectors in the index

    return index


