import requests
from typing import List, Mapping

from src.parsers.html_parser import page_content_to_markdown
from ..schemas import FetchedOneNoteNotebook, NotebookData, OneNotePage, OneNoteSection, OneNoteSectionGroup, PageData, SectionData, SectionGroupData
from datetime import datetime

BASE_URL = "https://graph.microsoft.com/v1.0/me/onenote"

def raise_for_response_error(response: requests.Response, operation: str) -> None:
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


def to_SectionGroupData(data: dict) -> SectionGroupData:
    return SectionGroupData(
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
        sectionGroupsUrl=data["sectionGroupsUrl"],
    )


def to_PageData(data: dict) -> PageData:
    return PageData(
        id=data["id"],
        self=data["self"],
        createdDateTime=datetime.fromisoformat(
            data["createdDateTime"].replace("Z", "+00:00")
        ),
        displayName=data["title"],
        lastModifiedDateTime=datetime.fromisoformat(
            data["lastModifiedDateTime"].replace("Z", "+00:00")
        ),
        contentUrl=data["contentUrl"],
    )


def authHeader(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def getNoteBookMetadata(token: str) -> List[NotebookData]:
    headers = authHeader(token)
    response = requests.get(f"{BASE_URL}/notebooks", headers=headers)
    raise_for_response_error(response, "Getting notebook metadata")

    return list(map(lambda data: to_NotebookData(data), response.json()["value"]))

def _getSections(headers: Mapping[str, str], notebook: NotebookData) -> List[SectionData]:
    response = requests.get(notebook.sectionsUrl, headers=headers)
    raise_for_response_error(response, "Getting notebook sections")

    return list(map(lambda section: to_SectionData(section), response.json()["value"]))


def _getSectionGroups(headers: Mapping[str, str], notebook: NotebookData) -> List[SectionGroupData]:
    response = requests.get(notebook.sectionGroupsUrl, headers=headers)
    raise_for_response_error(response, "Getting notebook section groups")

    return list(
        map(lambda section_group: to_SectionGroupData(section_group), response.json()["value"]))


def _get_sections_from_url(headers: Mapping[str, str], sections_url: str) -> List[SectionData]:
    response = requests.get(sections_url, headers=headers)
    raise_for_response_error(response, "Getting notebook sections")

    return list(map(lambda section: to_SectionData(section), response.json()["value"]))


def _get_section_groups_from_url(headers: Mapping[str, str], section_groups_url: str) -> List[SectionGroupData]:
    response = requests.get(section_groups_url, headers=headers)
    raise_for_response_error(response, "Getting notebook section groups")

    return list(map(lambda section_group: to_SectionGroupData(section_group), response.json()["value"]))


def _get_pages_from_url(headers: Mapping[str, str], pages_url: str) -> List[PageData]:
    response = requests.get(pages_url, headers=headers)
    raise_for_response_error(response, "Getting section pages")

    return list(map(lambda page: to_PageData(page), response.json()["value"]))


def to_one_note_page(page: PageData) -> OneNotePage:
    return OneNotePage(
        id=page.id,
        title=page.displayName,
        content_url=page.contentUrl,
    )


def to_one_note_section(headers: Mapping[str, str], section: SectionData, notebook_id: str, parent_section_group_id: str | None = None) -> OneNoteSection:
    pages = [
        to_one_note_page(page)
        for page in _get_pages_from_url(headers, section.pagesUrl)
    ]

    return OneNoteSection(
        id=section.id,
        name=section.displayName,
        parent_notebook_id=notebook_id,
        parent_section_group_id=parent_section_group_id,
        pages=pages,
    )


def to_one_note_section_group(headers: Mapping[str, str], section_group: SectionGroupData, notebook_id: str, parent_section_group_id: str | None = None) -> OneNoteSectionGroup:
    section_group_id = section_group.id
    sections = [
        to_one_note_section(
            headers,
            section,
            notebook_id,
            parent_section_group_id=section_group_id,
        )
        for section in _get_sections_from_url(headers, section_group.sectionsUrl)
    ]
    nested_section_groups = [
        to_one_note_section_group(
            headers,
            nested_section_group,
            notebook_id,
            parent_section_group_id=section_group_id,
        )
        for nested_section_group in _get_section_groups_from_url(headers, section_group.sectionGroupsUrl)
    ]

    return OneNoteSectionGroup(
        id=section_group_id,
        name=section_group.displayName,
        parent_notebook_id=notebook_id,
        parent_section_group_id=parent_section_group_id,
        sections=sections,
        section_groups=nested_section_groups,
    )


def getAllNoteBookStructure(token: str, notebook: NotebookData) -> FetchedOneNoteNotebook:
    headers = authHeader(token)

    sections = _getSections(headers, notebook)
    section_groups = _getSectionGroups(headers, notebook)
    children = [
        *(
            to_one_note_section(headers, section, notebook.id)
            for section in sections
        ),
        *(
            to_one_note_section_group(headers, section_group, notebook.id)
            for section_group in section_groups
        ),
    ]

    return FetchedOneNoteNotebook(
        id=notebook.id,
        name=notebook.displayName,
        children=children,
    )

def get_content_from_url(token: str, content_url: str):
    headers = authHeader(token)

    response = requests.get(content_url, headers=headers)
    raise_for_response_error(response, "Getting page content")

    return page_content_to_markdown(response.text)


def get_notebook_page_content(token: str, notebook: FetchedOneNoteNotebook) -> dict[str, str]:
    page_content: dict[str, str] = {}

    def visit_section(section: OneNoteSection, path: list[str]) -> None:
        section_path = [*path, section.name]
        for page in section.pages:
            if page.content_url is None:
                raise ValueError(
                    f"Page {page.id} ({page.title}) does not have a content URL"
                )

            page_path = " > ".join([*section_path, page.title])
            page_content[page_path] = get_content_from_url(
                token,
                page.content_url,
            )

    def visit_section_group(section_group: OneNoteSectionGroup, path: list[str]) -> None:
        group_path = [*path, section_group.name]
        for section in section_group.sections:
            visit_section(section, group_path)
        for nested_group in section_group.section_groups:
            visit_section_group(nested_group, group_path)

    notebook_path = [notebook.name]
    for child in notebook.children:
        if isinstance(child, OneNoteSection):
            visit_section(child, notebook_path)
        else:
            visit_section_group(child, notebook_path)

    return page_content
