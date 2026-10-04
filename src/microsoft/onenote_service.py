import requests
from typing import List, Mapping
from ..schemas import NotebookData, SectionData
from datetime import datetime

BASE_URL = "https://graph.microsoft.com/v1.0/me/onenote"

def raise_for_response_error(response: requests.Response, operation: str) -> None:
    """Raise a useful error when a Microsoft Graph request fails."""
    if response.ok:
        return

    try:
        error_data = response.json()
    except ValueError:
        error_data = response.text.strip()

    message = error_data
    if isinstance(error_data, dict):
        graph_error = error_data.get("error", error_data)
        if isinstance(graph_error, dict):
            message = (
                graph_error.get("message")
                or graph_error.get("code")
                or graph_error
            )

    raise requests.HTTPError(
        f"{operation} failed with HTTP {response.status_code}: {message}",
        response=response,
    )


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
    raise_for_response_error(response, "Getting notebook metadata")

    return list(map(lambda data: to_NotebookData(data), response.json()["value"]))

def _getSections(
    headers: Mapping[str, str],
    notebook: NotebookData,
) -> List[SectionData]:
    response = requests.get(notebook.sectionsUrl, headers=headers)
    raise_for_response_error(response, "Getting notebook sections")

    return list(map(lambda section: to_SectionData(section), response.json()["value"]))


def _getSectionGroups(headers: Mapping[str, str], notebook: NotebookData):
    response = requests.get(notebook.sectionGroupsUrl, headers=headers)
    raise_for_response_error(response, "Getting notebook section groups")

    return response.json()["value"]

# gets all the sections within a notebook
def getAllNoteBookSections(token: str, notebook: NotebookData):
    headers = authHeader(token)

    # have to go through sections and section groups to capture everything 
    sections = _getSections(headers, notebook)
    section_groups = _getSectionGroups(headers, notebook)
    return sections, section_groups