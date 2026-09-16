from pydantic import BaseModel
from typing import List

class Cards(BaseModel):
    front: str
    back: str
    tags: str
    source: str

class Response_Model(BaseModel):
    cards: List[Cards]