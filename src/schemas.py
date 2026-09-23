from pydantic import BaseModel, Field
from typing import List

class Card(BaseModel):
    front: str
    back: str
    tags: str
    source: str


class Response_Schema(BaseModel):
    cards: List[Card]


class Judge_Schema(BaseModel):
    groundedness: int = Field(ge=0, le=2)
    atomicity: int = Field(ge=0, le=1)
    usefulness: int = Field(ge=0, le=2)
    clarity: int = Field(ge=0, le=2)
    overall: int = Field(ge=0, le=2)
    explanation: str
