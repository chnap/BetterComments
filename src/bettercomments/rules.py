"""Deterministic rules for translating and shortening known comment patterns."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .config import CustomRule


@dataclass(frozen=True, slots=True)
class RuleResult:
    text: str
    reason: str


_EXACT_RULES = {
    "comprueba los permisos": "Check permissions.",
    "comprueba los permisos del usuario": "Check user permissions.",
    "verifica los permisos": "Check permissions.",
    "verifica los permisos del usuario": "Check user permissions.",
    "guarda el resultado": "Store the result.",
    "configuracion principal de la pagina": "Main page configuration.",
    "verifie les permissions": "Check permissions.",
    "verifie les autorisations": "Check permissions.",
    "enregistre le resultat": "Store the result.",
    "configuration principale de la page": "Main page configuration.",
    "uberpruft die berechtigungen": "Check permissions.",
    "benutzerberechtigungen prufen": "Check user permissions.",
    "speichert das ergebnis": "Store the result.",
    "verifica i permessi": "Check permissions.",
    "salva il risultato": "Store the result.",
    "verifica as permissoes": "Check permissions.",
    "salva o resultado": "Store the result.",
    "parse configuration": "Parse configuration.",
    "check permissions": "Check permissions.",
    "check user permissions": "Check user permissions.",
}

_PATTERN_RULES = (
    (
        re.compile(r"^(?:esta funcion )?(?:comprueba|verifica) si el usuario (?:tiene|posee) permisos .*(?:continuar|operacion).*$"),
        "Check user permissions.",
    ),
    (
        re.compile(r"^(?:cette fonction )?(?:verifie|controle) si l utilisateur (?:a|possede) (?:les )?(?:permissions|autorisations) .*$"),
        "Check user permissions.",
    ),
    (
        re.compile(r"^(?:this function is responsible for )?iterat(?:e|ing) over all users and check(?:ing)? whether each user is active before add(?:ing)? them to the result(?:ing array)?$"),
        "Add active users to the result.",
    ),
    (
        re.compile(r"^iterate over every item returned by the api check whether the item is currently active add active items to the result array$"),
        "Add active API items to the result.",
    ),
)

_IMPERATIVE_VERBS = {
    "adds": "Add",
    "calculates": "Calculate",
    "checks": "Check",
    "converts": "Convert",
    "creates": "Create",
    "loads": "Load",
    "parses": "Parse",
    "removes": "Remove",
    "returns": "Return",
    "updates": "Update",
    "validates": "Validate",
    "verifies": "Verify",
}
_FUNCTION_DESCRIPTION = re.compile(
    r"^this (?:function|method) (" + "|".join(_IMPERATIVE_VERBS) + r") (.+)$",
    re.IGNORECASE,
)


def apply_rules(content: str, custom_rules: tuple[CustomRule, ...], *, allow_generic: bool) -> RuleResult | None:
    collapsed = collapse_comment(content)
    for rule in custom_rules:
        left = collapsed if rule.case_sensitive else collapsed.casefold()
        right = collapse_comment(rule.match) if rule.case_sensitive else collapse_comment(rule.match).casefold()
        if left == right:
            return RuleResult(normalize_sentence(rule.replacement), "project rule")

    key = match_key(collapsed)
    exact = _EXACT_RULES.get(key)
    if exact is not None:
        return RuleResult(exact, "curated rewrite rule")
    for pattern, replacement in _PATTERN_RULES:
        if pattern.fullmatch(key):
            return RuleResult(replacement, "curated rewrite rule")

    if allow_generic and is_probably_english(collapsed):
        match = _FUNCTION_DESCRIPTION.fullmatch(collapsed.rstrip(".!?"))
        if match is not None:
            verb, remainder = match.groups()
            return RuleResult(normalize_sentence(f"{_IMPERATIVE_VERBS[verb.casefold()]} {remainder}"), "concise imperative style")
    return None


def collapse_comment(content: str) -> str:
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned = [re.sub(r"^\s*\*?\s?", "", line).strip() for line in lines]
    return re.sub(r"\s+", " ", " ".join(part for part in cleaned if part)).strip()


def normalize_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return text


def match_key(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    apostrophes_as_spaces = without_marks.replace("'", " ").replace("’", " ")
    words_only = re.sub(r"[^\w]+", " ", apostrophes_as_spaces, flags=re.UNICODE)
    return re.sub(r"\s+", " ", words_only).strip().casefold()


def is_probably_english(text: str) -> bool:
    words = set(match_key(text).split())
    if not words:
        return False
    english = words & {"a", "all", "and", "before", "check", "configuration", "for", "from", "is", "of", "parse", "result", "the", "this", "to", "user", "with"}
    foreign = words & {"das", "de", "der", "die", "el", "esta", "la", "le", "les", "los", "para", "per", "pour", "que", "un", "une", "verifica"}
    return len(english) > len(foreign)

