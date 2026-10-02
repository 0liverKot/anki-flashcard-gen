from pydantic import BaseModel, Field
from typing import List
import datetime

class Card(BaseModel):
    front: str
    back: str
    source: str


class Response_Schema(BaseModel):
    cards: List[Card]


class Single_Card_Response_Schema(BaseModel):
    answer: str


class Judge_Schema(BaseModel):
    groundedness: int = Field(ge=0, le=2)
    atomicity: int = Field(ge=0, le=1)
    usefulness: int = Field(ge=0, le=2)
    clarity: int = Field(ge=0, le=2)
    overall: int = Field(ge=0, le=2)
    explanation: str


class Card_Source_Schema(BaseModel):
    card_id: int
    source_document: str
    source_section: List[str]
    source_excerpt: str
    source_hash: str

class NotebookData(BaseModel):
    id: str
    self: str
    createdDateTime: datetime.datetime
    displayName: str
    lastModifiedDateTime: datetime.datetime
    sectionsUrl: str
    sectionGroupsUrl: str

    
       
