import re

WORD_PATTERN = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])")
MINIMUM_WORD_LENGTH = 3
IGNORED_WORDS = frozenset({"self", "this", "cls"})


def split_identifier_words(identifier: str) -> frozenset[str]:
    words: set[str] = set()

    for word_match in WORD_PATTERN.finditer(identifier):
        word = word_match.group().lower()

        if len(word) < MINIMUM_WORD_LENGTH or word in IGNORED_WORDS:
            continue

        words.add(word)

    return frozenset(words)


def vocabulary_of(identifiers: tuple[str, ...]) -> frozenset[str]:
    vocabulary: set[str] = set()

    for identifier in identifiers:
        vocabulary.update(split_identifier_words(identifier))

    return frozenset(vocabulary)

