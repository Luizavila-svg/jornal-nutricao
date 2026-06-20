from __future__ import annotations

import re

GRAPH_BLOCK_LANGUAGES = {"mermaid", "graphviz", "vega", "vega-lite", "plantuml", "chart"}
IMAGE_PATTERNS = (
    re.compile(r"!\[[^\]]*\]\([^\)]+\)"),
    re.compile(r"<img\s+[^>]*>", flags=re.IGNORECASE),
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _is_image_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in IMAGE_PATTERNS)


def _is_graph_block_start(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("```"):
        return False

    language = stripped[3:].strip().lower()
    return language in GRAPH_BLOCK_LANGUAGES


def summarize_text_preserving_graphics(text: str, max_lines: int = 30) -> str:
    if max_lines < 1:
        raise ValueError("max_lines deve ser maior que zero")

    lines = text.splitlines()
    prose_lines: list[str] = []
    graphic_blocks: list[list[str]] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if _is_graph_block_start(line):
            block = [line]
            i += 1
            while i < len(lines):
                block.append(lines[i])
                if lines[i].strip().startswith("```"):
                    i += 1
                    break
                i += 1
            graphic_blocks.append(block)
            continue

        if _is_image_line(line):
            graphic_blocks.append([line])
            i += 1
            continue

        cleaned = line.strip()
        if cleaned:
            prose_lines.append(cleaned)
        i += 1

    selected_graphics: list[list[str]] = []
    used_graphic_lines = 0
    for block in graphic_blocks:
        if used_graphic_lines + len(block) > max_lines:
            break
        selected_graphics.append(block)
        used_graphic_lines += len(block)

    available_for_prose = max_lines - used_graphic_lines

    prose_sentences = SENTENCE_SPLIT_RE.split(" ".join(prose_lines)) if prose_lines else []
    prose_summary_lines: list[str] = []
    for sentence in prose_sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        prose_summary_lines.append(sentence)
        if len(prose_summary_lines) >= available_for_prose:
            break

    if not prose_summary_lines and available_for_prose > 0 and prose_lines:
        prose_summary_lines = prose_lines[:available_for_prose]

    output_lines = prose_summary_lines
    for block in selected_graphics:
        if len(output_lines) + len(block) > max_lines:
            break
        output_lines.extend(block)

    return "\n".join(output_lines)
