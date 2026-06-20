from __future__ import annotations

import re
import textwrap

GRAPH_BLOCK_LANGUAGES = {"mermaid", "graphviz", "vega", "vega-lite", "plantuml", "chart"}
IMAGE_PATTERNS = (
    re.compile(r"!\[[^\]]*\]\([^\)]+\)"),
    re.compile(r"<img\s+[^>]*>", flags=re.IGNORECASE),
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
RELEVANCE_TERMS = {
    "estudo",
    "evidencia",
    "meta-analise",
    "revisao",
    "diretriz",
    "resultado",
    "impacto",
    "risco",
    "beneficio",
    "paciente",
    "saude",
    "nutricao",
    "dieta",
    "obesidade",
    "clinico",
    "atleta",
    "creatina",
    "whey",
}
WRAP_WIDTH = 120


def _is_image_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in IMAGE_PATTERNS)


def _is_graph_block_start(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("```"):
        return False

    language = stripped[3:].strip().lower()
    return language in GRAPH_BLOCK_LANGUAGES


def _sentence_score(sentence: str) -> int:
    lowered = sentence.lower()
    words = re.findall(r"\w+", lowered)

    keyword_hits = sum(1 for term in RELEVANCE_TERMS if term in lowered)
    numeric_hits = sum(1 for token in words if any(char.isdigit() for char in token))

    score = keyword_hits * 4 + numeric_hits * 2
    if 8 <= len(words) <= 35:
        score += 2
    if ":" in sentence:
        score += 1
    return score


def _build_wrapped_lines(sentences: list[str], max_lines: int) -> list[str]:
    lines: list[str] = []
    for sentence in sentences:
        wrapped = textwrap.wrap(
            sentence,
            width=WRAP_WIDTH,
            break_long_words=False,
            break_on_hyphens=False,
        )
        for line in wrapped:
            if len(lines) >= max_lines:
                return lines
            lines.append(line)
    return lines


def summarize_text_preserving_graphics(text: str, max_lines: int = 20, min_lines: int = 15) -> str:
    if max_lines < 1:
        raise ValueError("max_lines deve ser maior que zero")
    if min_lines < 1:
        raise ValueError("min_lines deve ser maior que zero")
    if min_lines > max_lines:
        raise ValueError("min_lines nao pode ser maior que max_lines")

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
    prose_sentences = [sentence.strip() for sentence in prose_sentences if sentence.strip()]

    prose_summary_lines: list[str] = []
    if prose_sentences and available_for_prose > 0:
        ranked_indexes = sorted(
            range(len(prose_sentences)),
            key=lambda index: (_sentence_score(prose_sentences[index]), -index),
            reverse=True,
        )

        selected_indexes: set[int] = set()
        target_prose_lines = min(min_lines, available_for_prose)

        for index in ranked_indexes:
            selected_indexes.add(index)
            ordered_sentences = [
                prose_sentences[pos]
                for pos in range(len(prose_sentences))
                if pos in selected_indexes
            ]
            lines = _build_wrapped_lines(ordered_sentences, available_for_prose)
            if len(lines) >= target_prose_lines or len(lines) >= available_for_prose:
                prose_summary_lines = lines
                break

        if not prose_summary_lines:
            top_indexes = sorted(ranked_indexes[: max(1, min(6, len(ranked_indexes)))])
            top_sentences = [prose_sentences[index] for index in top_indexes]
            prose_summary_lines = _build_wrapped_lines(top_sentences, available_for_prose)

    if not prose_summary_lines and available_for_prose > 0 and prose_lines:
        prose_summary_lines = _build_wrapped_lines(prose_lines, available_for_prose)

    output_lines = prose_summary_lines
    for block in selected_graphics:
        if len(output_lines) + len(block) > max_lines:
            break
        output_lines.extend(block)

    return "\n".join(output_lines)
