"""Lazy entry point keeps RAG dependencies optional for ordinary planning."""
def lookup_travel_info(city, question, top_k=3):
    from Backend.app.rag.chain.travel import lookup_travel_info as lookup
    return lookup(city, question, top_k)
