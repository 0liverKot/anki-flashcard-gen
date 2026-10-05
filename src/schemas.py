from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Annotated, Literal
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


class Chunk_Schema(BaseModel):
    chunk_id: str
    source_path: str
    content: str
    embedded_content: bytes


class OneNoteMetadata(BaseModel):
    id: str
    self: str
    createdDateTime: datetime.datetime
    displayName: str
    lastModifiedDateTime: datetime.datetime


class NotebookData(OneNoteMetadata):
    sectionsUrl: str
    sectionGroupsUrl: str


class SectionData(OneNoteMetadata):
    pagesUrl: str     


class SectionGroupData(OneNoteMetadata):
    sectionsUrl: str
    sectionGroupsUrl: str


class PageData(OneNoteMetadata):
    contentUrl: str


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class OneNotePage(StrictModel):
    type: Literal["page"] = "page"

    id: str
    title: str
    content_url: str | None = None
    parent_page_id: str | None = None


class OneNoteSection(StrictModel):
    type: Literal["section"] = "section"

    id: str
    name: str

    parent_notebook_id: str | None = None
    parent_section_group_id: str | None = None

    pages: list[OneNotePage] = Field(default_factory=list)


class OneNoteSectionGroup(StrictModel):
    type: Literal["section_group"] = "section_group"

    id: str
    name: str
    
    parent_notebook_id: str | None = None
    parent_section_group_id: str | None = None
    
    sections: list[OneNoteSection] = Field(default_factory=list)
    section_groups: list[OneNoteSectionGroup] = Field(
        default_factory=list
    )

NotebookChild = Annotated[
    OneNoteSection | OneNoteSectionGroup,
    Field(discriminator="type"),
]


class FetchedOneNoteNotebook(StrictModel):
    type: Literal["notebook"] = "notebook"

    id: str
    name: str
    children: list[NotebookChild] = Field(default_factory=list)
