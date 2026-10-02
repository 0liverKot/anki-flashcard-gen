import sqlite3
from typing import List

from ..db.db import VectorDB
from ..models.card_embedding import CardEmbeddingModel
from ..schemas import Card

SIMILARITY_THRESHOLD = 0.1

class DuplicateManager:
    def __init__(self, db: VectorDB) -> None:
        self.db = db
        self.model = CardEmbeddingModel()

    def check_duplicate(self, card: Card) -> Card | None:
        return self._find_duplicate(self._embedding_for(card))

    def check_duplicates(self, cards: List[Card]) -> List[Card | None]:
        embeddings = self.model.combined_embeddings(cards)
        return [
            self._find_duplicate(embedding)
            for embedding in embeddings
        ]

    def _embedding_for(self, card: Card):
        return self.model.combined_embeddings([card])[0]

    def _find_duplicate(self, embedding) -> Card | None:
        query_vector = sqlite3.Binary(
            embedding.astype("float32", copy=False).tobytes()
        )

        row = self.db.cursor.execute(
            """
            SELECT rowid, distance
            FROM vector_full_scan(
                "card_embeddings",
                "combined_embedding",
                vector_as_f32(?),
                1
            )                   
            """,
            (query_vector,)
        ).fetchone()

        if row is None:
            return None
        
        rowid, distance = row

        if distance > 1 - SIMILARITY_THRESHOLD:
            return None
        
        question, answer = self.db.cursor.execute(
            """
            SELECT question, answer
            FROM card_embeddings
            WHERE rowid = ?
            """,
            (rowid,),
        ).fetchone()

        return Card(
            front=question,
            back =answer,
            source=""
        )


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
