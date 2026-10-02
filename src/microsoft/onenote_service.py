import requests
from ..schemas import NotebookData
from datetime import datetime

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

def authHeader(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def getNoteBook():
    pass

def getPages(token: str):
    headers = authHeader(token)
    response = requests.get("https://graph.microsoft.com/v1.0/me/onenote/notebooks", headers=headers)

    if response.ok:
        return list(map(lambda data: to_NotebookData(data), response.json()["value"]))