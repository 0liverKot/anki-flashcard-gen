import json
import re

from ..type_aliases import SourceFile


HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")


def markdown_to_sections(content: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    heading_path: list[tuple[int, str]] = []
    section_content: list[str] = []

    def add_section() -> None:
        section_text = "\n".join(section_content).strip()
        if not heading_path or not section_text:
            return

        sections.append(
            {
                "source": " > ".join(heading for _, heading in heading_path),
                "content": section_text,
            }
        )

    for line in content.splitlines():
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            add_section()
            level = len(heading_match.group(1))
            while heading_path and heading_path[-1][0] >= level:
                heading_path.pop()
            heading_path.append((level, heading_match.group(2).strip()))
            section_content = []
            continue

        section_content.append(line)

    add_section()
    return sections


def md_parse(path) -> tuple[str, SourceFile]:
    content = path.read_text()
    sections = markdown_to_sections(content)
    
    return json.dumps(sections), sections
