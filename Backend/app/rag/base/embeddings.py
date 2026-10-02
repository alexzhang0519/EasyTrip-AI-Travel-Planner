import os
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Initialize lazily; opening the app does not require an API key.
client = None
EMBED_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def get_client():
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("Travel-guide retrieval needs OPENAI_API_KEY.")
        client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1",
                        timeout=60.0, max_retries=2)
    return client


def embed_texts(texts: list[str]) -> np.ndarray:
    """Turn a list of texts into a NumPy array of embedding vectors."""
    response = get_client().embeddings.create(model=EMBED_MODEL, input=texts, encoding_format="float")
    # Each item in response.data has an .embedding (a list of floats).
    vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
    # FAISS needs a 2D float32 NumPy array.
    return np.array(vectors, dtype="float32")

