from typing import List

import torch
from sentence_transformers import SentenceTransformer
from numpy import ndarray

from ..schemas import Card, Chunk_Schema

class EmbeddingModel:

    def __init__(self) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer("MongoDB/mdbr-leaf-mt", device=device)

    def combined_embeddings(self, cards: List[Card]) -> ndarray:
        queries = list(map(lambda card: f"Question: {card.front} \n Answer: {card.back}", cards))
        return self.model.encode(queries)
    
    def embed_content(self, chunks: List[Chunk_Schema]) -> List[Chunk_Schema]:
        queries = [
            f"Source: {chunk.source_path}\nContent: {chunk.content}"
            for chunk in chunks
        ]
        embedded_contents = self.model.encode(queries)

        for chunk, embedded_content in zip(chunks, embedded_contents):
            chunk.embedded_content = embedded_content.astype("float32").tobytes()

        return chunks
