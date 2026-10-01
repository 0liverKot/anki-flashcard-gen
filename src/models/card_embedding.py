from typing import List
from sentence_transformers import SentenceTransformer
from numpy import ndarray

try: 
    from src.schemas import Card
except ModuleNotFoundError:
    from schemas import Card

class CardEmbeddingModel:

    def __init__(self) -> None:
        self.model = SentenceTransformer("MongoDB/mdbr-leaf-mt", device="cuda")

    def combined_embeddings(self, cards: List[Card]) -> ndarray:
        queries = list(map(lambda card: f"Question: {card.front} \n Answer: {card.back}", cards))
        return self.model.encode(queries)
    