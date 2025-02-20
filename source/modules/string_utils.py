from operator import add
import re

from bs4 import BeautifulSoup
from markdown import markdown
import re


def markdown_to_text(markdown_text: str) -> str:
    """Converts a markdown string to plaintext"""

    html = markdown(markdown_text)

    html = re.sub(r"<pre>(.*?)</pre>", " ", html)
    html = re.sub(r"<code>(.*?)</code >", " ", html)

    soup = BeautifulSoup(html, "html.parser")

    return "".join(soup.findAll(text=True))


def add_bullet_point(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("-") or line.startswith("*"):
            lines[i] = line[:1] + " •" + line[1:]
    return "\n".join(lines)


def patch_note_cleaner(patch_note_text: str) -> str:
    text = add_bullet_point(patch_note_text)
    text = markdown_to_text(text)
    text = re.sub(r":\n\n", ":\n", text)  # Remove double newlines after colons
    lines = text.splitlines()
    lines = [line for line in lines if line.strip() != ""]

    # Add space after "What's Changed" header
    if lines[0].startswith("What's Changed"):
        if len(lines) == 1 or lines[1].strip() != "":
            lines.insert(1, "")

    # Add space after colon
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].endswith(":") and lines[i - 1] != "":
            lines.insert(i, "")

    return "\n".join(lines)
