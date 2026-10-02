import requests
from typing import List
from ..schemas import NotebookData, SectionData
from datetime import datetime

BASE_URL = "https://graph.microsoft.com/v1.0/me/onenote"

def to_NotebookData(data: dict) -> NotebookData:
    return NotebookData(
        id=data["id"],
        self=data["self"],
        createdDateTime=datetime.fromisoformat(
            data["createdDateTime"].replace("Z", "+00:00")
        ),
        displayName=data["displayName"],
        lastModifiedDateTime=datetime.fromisoformat(
            data["lastModifiedDateTime"].replace("Z", "+00:00")
        ),
        sectionsUrl=data["sectionsUrl"],
        sectionGroupsUrl=data["sectionGroupsUrl"]
    )

def to_SectionData(data: dict) -> SectionData:
    return SectionData(
        id=data["id"],
        self=data["self"],
        createdDateTime=datetime.fromisoformat(
            data["createdDateTime"].replace("Z", "+00:00")
        ),
        displayName=data["displayName"],
        lastModifiedDateTime=datetime.fromisoformat(
            data["lastModifiedDateTime"].replace("Z", "+00:00")
        ),
        pagesUrl=data["pagesUrl"],
    )


def authHeader(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def getNoteBookMetadata(token: str) -> List[NotebookData]:
    headers = authHeader(token)
    response = requests.get(f"{BASE_URL}/notebooks", headers=headers)

    if response.ok:
        return list(map(lambda data: to_NotebookData(data), response.json()["value"]))
    

def _getSections(headers: str, notebook: NotebookData) -> List[SectionData]:
    response = requests.get(notebook.sectionsUrl, headers=headers)

    if response.ok:
        return list(map(lambda section: to_SectionData(section), response.json()["value"]))


def _getSectionGroups(headers: str, notebook: NotebookData):
    response = requests.get(notebook.sectionGroupsUrl, headers=headers)

    if response.ok:
        return response.json()["value"]

# gets all the sections within a notebook
def getAllNoteBookSections(token: str, notebook: NotebookData):
    headers = authHeader(token)

    # have to go through sections and section groups to capture everything 
    sections = _getSections(headers, notebook)
    section_groups = _getSectionGroups(headers, notebook)
    return sections, section_groups