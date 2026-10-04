from markdownify import markdownify

def page_content_to_markdown(html_content: str) -> str:
    markdown = markdownify(
        html_content,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"]
    )

    return markdown.strip()