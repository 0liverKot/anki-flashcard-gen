import sqlite3
from typing import List

try:
    from src.db.db import VectorDB
    from src.models.card_embedding import CardEmbeddingModel
    from src.schemas import Card
except ModuleNotFoundError:
    from db.db import VectorDB
    from models.card_embedding import CardEmbeddingModel
    from schemas import Card

class DuplicateManager:
    def __init__(self, db: VectorDB) -> None:
        self.db = db
        self.model = CardEmbeddingModel()

    def add_cards(self, cards: List[Card]) -> None:
        embeddings = self.model.combined_embeddings(cards)

        rows = [
            (
                card.front,
                card.back,
                sqlite3.Binary(embedding.astype("float32").tobytes())
            )
            for card, embedding in zip(cards, embeddings)
        ]

        self.db.cursor.executemany(
            """
            INSERT INTO card_embeddings
                (question, answer, combined_embedding)
            VALUES (?, ?, vector_as_f32(?))
            """, 
            rows
        )
        self.db.sqliteConnection.commit()
