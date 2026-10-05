import sqlite3
from typing import List

from ..db.db import DB
from ..models.embedding_model import EmbeddingModel
from ..schemas import Card

SIMILARITY_THRESHOLD = 0.1

class DuplicateManager:
    def __init__(self, db: DB, embedding_model: EmbeddingModel) -> None:
        self.db = db
        self.model = embedding_model

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


    def add_cards(self, cards: List[Card], card_ids: List[int]) -> None:
        if len(cards) != len(card_ids):
            raise ValueError("cards and card_ids must have the same length")

        embeddings = self.model.combined_embeddings(cards)

        rows = [
            (
                card_id,
                card.front,
                card.back,
                sqlite3.Binary(embedding.astype("float32").tobytes())
            )
            for card_id, card, embedding in zip(card_ids, cards, embeddings)
        ]

        self.db.cursor.executemany(
            """
            INSERT INTO card_embeddings
                (anki_note_id, question, answer, combined_embedding)
            VALUES (?, ?, ?, vector_as_f32(?))
            """, 
            rows
        )
        self.db.sqliteConnection.commit()

    def update_cards(self, card_ids: List[int], cards: List[Card]) -> None:
        if len(cards) != len(card_ids):
            raise ValueError("cards and card_ids must have the same length")

        embeddings = self.model.combined_embeddings(cards)
        rows = [
            (
                card.front,
                card.back,
                sqlite3.Binary(embedding.astype("float32").tobytes()),
                card_id,
            )
            for card_id, card, embedding in zip(card_ids, cards, embeddings)
        ]

        self.db.cursor.executemany(
            """
            UPDATE card_embeddings
            SET question = ?, answer = ?, combined_embedding = vector_as_f32(?)
            WHERE anki_note_id = ?
            """,
            rows,
        )
        self.db.sqliteConnection.commit()
