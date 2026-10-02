"""Bounded per-process guide indexes; no persistent embedding migration needed."""
from collections import OrderedDict
from threading import Lock
from Backend.app.rag.base.documents import fetch_article, chunk_text
from Backend.app.rag.pre_data.index import build_index
from Backend.app.rag.retriever.vector import retrieve
_cache = OrderedDict()
_lock = Lock()

def lookup_travel_info(city: str, question: str, top_k: int = 3) -> str:
    if not isinstance(city,str) or not city.strip() or not isinstance(question,str):
        raise ValueError('City and question must be text')
    if type(top_k) is not int or not 1 <= top_k <= 10:
        raise ValueError('top_k must be between 1 and 10')
    city = city.strip()
    with _lock:
        if city not in _cache:
            text = fetch_article(city)
            if not text: return f'No travel guide found for {city}.'
            chunks = chunk_text(text)
            if not chunks: return f'No travel guide found for {city}.'
            _cache[city] = (chunks, build_index(chunks))
            while len(_cache) > 16: _cache.popitem(last=False)
        _cache.move_to_end(city)
        chunks, index = _cache[city]
    return '\n\n'.join(retrieve(question, chunks, index, top_k=top_k))
