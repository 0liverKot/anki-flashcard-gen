from pathlib import Path
from src.db.db import DB
from src.md_parser import md_parse
from src.type_aliases import SourceFile
from typing import List
from src.schemas import Card, Card_Source_Schema
import hashlib
import json


class SourceManager:
    def __init__(self, db: DB) -> None:
        self.current_source_path = Path(__file__).parent / "notes" / "waves_and_particle_nature_of_light.md"

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
    

    def hash_excerpt(self, excerpt: str) -> str:
        return hashlib.sha256(
            excerpt.encode("utf-8")
        ).hexdigest()


    def add_card_sources(self, cards: List[Card]):

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


        ids = list(range(100))
        index = 0
        rows = []
        for card in cards:
            card_id = ids[index]
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