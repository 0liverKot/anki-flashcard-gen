from typing import List

import torch
from sentence_transformers import SentenceTransformer
from numpy import ndarray

from ..schemas import Card

class CardEmbeddingModel:

    def __init__(self) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer("MongoDB/mdbr-leaf-mt", device=device)

    def combined_embeddings(self, cards: List[Card]) -> ndarray:
        queries = list(map(lambda card: f"Question: {card.front} \n Answer: {card.back}", cards))
        return self.model.encode(queries)
    