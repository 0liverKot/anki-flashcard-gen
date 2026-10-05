from typing import List

from src.parsers.md_parser import markdown_to_sections
from src.schemas import Chunk_Schema


def content_to_chunks(content: dict[str, str]) -> List[Chunk_Schema]:
    chunks: List[Chunk_Schema] = []

    for source_path, markdown in content.items():
        sections = markdown_to_sections(markdown)

        for section in sections:
            chunks.append(
                Chunk_Schema(
                    source_path=f"{source_path} > {section['source']}",
                    content=section["content"],
                    embedded_content=b"",
                )
            )

    return chunks