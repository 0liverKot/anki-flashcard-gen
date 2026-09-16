import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import markdown_to_json

def flatten_markdown(document: Mapping[str, Any]) -> list[dict[str, str]]:
   """Convert markdown_to_json's nested result into source/content sections.

   Lists are treated as multiple pieces of content under the current heading
   path, while dictionaries add another heading to that path.
   """
   sections: list[dict[str, str]] = []

   def visit(value: Any, heading_path: tuple[str, ...]) -> None:
       if isinstance(value, Mapping):
           for heading, content in value.items():
               visit(content, (*heading_path, str(heading)))
           return

       if isinstance(value, (list, tuple)):
           for item in value:
               visit(item, heading_path)
           return

       if value is None or not heading_path:
           return

       sections.append(
           {
               "source": " > ".join(heading_path),
               "content": str(value),
           }
       )

   visit(document, ())
   return sections


def md_to_json(path) -> str:
   content = path.read_text()
   md_dict = markdown_to_json.dictify(content)
   return json.dumps(md_dict)
