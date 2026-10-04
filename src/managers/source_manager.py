from pathlib import Path
from typing import Dict, List
import hashlib
import json

from ..db.db import DB
from ..parsers.md_parser import md_parse
from ..type_aliases import SourceFile
from ..schemas import Card, Card_Source_Schema

class SourceManager:
    def __init__(self, db: DB) -> None:
        self.current_source_path = Path(__file__).parent / ".." / "notes" / "unsynced_notes.md"

        self.current_source_json, self.current_source_dict = md_parse(self.current_source_path)

        self.db = db


    def get_current_source_dict(self) -> SourceFile:
        return self.current_source_dict


    def get_current_source_json(self) -> str:
        return self.current_source_json


    def is_source_valid(self, source: str, debug=False) -> bool:
        for dict in self.current_source_dict:
            if dict.get("source") == source:
                return True

        if debug:
            for dict in self.current_source_dict:
                print(dict.get("source"))
                print(source)
                print("\n")
        return False
    

    def hash_excerpt(self, excerpt: str | None) -> str:
        if not excerpt:
            return ""
        
        return hashlib.sha256(
            excerpt.encode("utf-8")
        ).hexdigest()


    def add_card_sources(self, cards: List[Card], card_ids: List[int]):

        def create_card_source(card: Card, id: int) -> Card_Source_Schema | None:
            for dict in self.current_source_dict:
                if dict["source"] == card.source:

                    source_excerpt = dict["content"]

                    source_path = card.source.split(">")
                    source_path = list(map(lambda x: x.strip(), source_path))

                    return Card_Source_Schema(
                        card_id=id,
                        source_document=source_path[0],
                        source_section=source_path[1:],
                        source_excerpt=source_excerpt,
                        source_hash=self.hash_excerpt(source_excerpt)
                    )
            
            return None


        index = 0
        rows = []
        for card in cards:
            card_id = card_ids[index]
            card_source = create_card_source(card, card_id)

            index += 1

            if card_source is None:
                continue
                
            rows.append((
                card_source.card_id,
                card_source.source_document,
                json.dumps(card_source.source_section),
                card_source.source_excerpt,
                card_source.source_hash
            ))


        self.db.cursor.executemany(
            """
            INSERT INTO card_sources (
            card_id,
            source_document,
            source_section,
            source_excerpt,
            source_hash
            ) 
            Values(?, ?, ?, ?, ?)""", 
            rows)
        self.db.sqliteConnection.commit()

    
    def synchronise(self) -> List[int]:
        
        card_sources = self.get_card_sources()
        unsynced = list()
        for card_source in card_sources:
            id, source_document, source_section, source_hash = card_source
            source_path = " > ".join([source_document, *json.loads(source_section)])

            for dict in self.current_source_dict:
                if dict.get("source") == source_path and self.hash_excerpt(dict.get("content")) != source_hash:
                    unsynced.append(id)
                    break

        return unsynced
        

    def get_card_sources(self):
        card_sources = self.db.cursor.execute("""
            SELECT card_id, source_document, source_section, source_hash
            FROM card_sources        
            """).fetchall()
        return card_sources
    

    def get_source_paths(self, ids: List[int]) -> Dict[int, str]:
        placeholders = ",".join("?" for _ in ids)

        rows = self.db.cursor.execute(f"""
            SELECT card_id, source_document, source_section
            FROM card_sources
            WHERE card_id IN ({placeholders})
            """,
            ids).fetchall()
        
        source_paths = dict()
        for id, source_document, source_section in rows:
            source_path = " > ".join([source_document, *json.loads(source_section)])

            source_paths[id] = source_path

        return source_paths
    

    def get_sources(self, source_paths: Dict[int, str]) -> Dict[int, str]:
        
        sources = dict()
        for id, path in source_paths.items():
            for d in self.current_source_dict:
                if d.get("source") == path:
                    sources[id] = d.get("content")
        
        return sources
    

    def update_sources(self, ids: List[int], cards: List[Card]) -> None:
        for id, card in zip(ids, cards):
        
            for dict in self.current_source_dict:
                if dict.get("source") == card.source:
                    source_excerpt = dict.get("content")
                    hashed_source_exerpt = self.hash_excerpt(source_excerpt)

            self.db.cursor.execute(
                """
                UPDATE card_sources
                SET source_excerpt = ?, source_hash = ? 
                WHERE card_id = ?                
                """,
                (source_excerpt, hashed_source_exerpt, id)
            )
            self.db.sqliteConnection.commit()
                