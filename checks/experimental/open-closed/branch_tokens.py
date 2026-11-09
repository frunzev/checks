import re

WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")
QUOTE_CHARACTERS = frozenset({'"', "'", "`"})
ORDERING_OPERATOR = re.compile(r"(?<![-=<>!])[<>](?![<>])")


def head_tokens(condition: str) -> frozenset[str]:
    tokens: set[str] = set()

    for word_match in WORD_PATTERN.finditer(condition):
        tokens.add(word_match.group().lower())

    return frozenset(tokens)


def head_values(condition: str) -> frozenset[str]:
    if ORDERING_OPERATOR.search(condition):
        return frozenset()

    values: set[str] = set()

    for word_match in WORD_PATTERN.finditer(condition):
        word = word_match.group()
        word_start = word_match.start()
        preceding_character = condition[word_start - 1 : word_start]
        is_quoted = preceding_character in QUOTE_CHARACTERS
        is_capitalized = word[0].isupper()

        if is_quoted or is_capitalized:
            values.add(word.lower())

    return frozenset(values)
