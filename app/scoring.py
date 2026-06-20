from __future__ import annotations

import re
from typing import Dict, List, Tuple

THEME_KEYWORDS: Dict[str, List[str]] = {
    "clinica": [
        "paciente",
        "hospital",
        "clinica",
        "tratamento",
        "doenca",
        "nutricao clinica",
        "guideline",
    ],
    "esportiva": [
        "atleta",
        "treino",
        "performance",
        "esporte",
        "whey",
        "creatina",
        "endurance",
    ],
    "emagrecimento": [
        "emagrecimento",
        "perda de peso",
        "obesidade",
        "deficit calorico",
        "dieta",
        "metabolismo",
    ],
}

RELEVANCE_KEYWORDS = [
    "estudo",
    "meta-analise",
    "revisao sistematica",
    "ensaio clinico",
    "diretriz",
    "evidencia",
    "nutricao",
    "saude",
]

WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


def _normalize(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


def classify_theme(title: str, content: str) -> str:
    normalized = _normalize(f"{title} {content}")

    best_theme = "geral"
    best_hits = 0

    for theme, keywords in THEME_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in normalized)
        if hits > best_hits:
            best_hits = hits
            best_theme = theme

    return best_theme


def compute_relevance_score(title: str, content: str) -> int:
    normalized = _normalize(f"{title} {content}")

    keyword_hits = sum(1 for keyword in RELEVANCE_KEYWORDS if keyword in normalized)
    length_bonus = min(len(normalized.split()) // 40, 3)

    # Score final em escala simples de 0 a 100.
    raw_score = 40 + (keyword_hits * 10) + (length_bonus * 5)
    return max(0, min(raw_score, 100))


def classify_and_score(title: str, content: str) -> Tuple[str, int]:
    theme = classify_theme(title, content)
    score = compute_relevance_score(title, content)
    return theme, score
