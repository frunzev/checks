from hypothesis import given
from hypothesis import strategies as st

from identifier_words import (
    IGNORED_WORDS,
    MINIMUM_WORD_LENGTH,
    split_identifier_words,
    vocabulary_of,
)
from semantic_finder_support import lowercase_words

meaningful_words = lowercase_words.filter(
    lambda word: word not in IGNORED_WORDS
)
identifier_lists = st.lists(st.text(max_size=20), max_size=6)


def test_splits_snake_camel_and_acronym_spellings() -> None:
    words = split_identifier_words("parse_HTTPServer_requestBody")

    assert words == frozenset({"parse", "http", "server", "request", "body"})


def test_drops_short_and_ignored_words() -> None:
    assert split_identifier_words("self.id_of_this") == frozenset()


@given(st.text(max_size=40))
def test_split_identifier_words_property_returns_only_long_lowercase_words(
    identifier: str,
) -> None:
    for word in split_identifier_words(identifier):
        assert word.isascii()
        assert word.isalpha()
        assert word.islower()
        assert len(word) >= MINIMUM_WORD_LENGTH
        assert word not in IGNORED_WORDS


@given(st.lists(meaningful_words, min_size=1, max_size=5))
def test_split_identifier_words_property_agrees_on_snake_and_camel_case(
    words: list[str],
) -> None:
    snake_case = "_".join(words)
    capitalized_words = [word.capitalize() for word in words[1:]]
    camel_case = words[0] + "".join(capitalized_words)

    snake_case_words = split_identifier_words(snake_case)
    camel_case_words = split_identifier_words(camel_case)

    assert snake_case_words == camel_case_words == frozenset(words)


@given(identifier_lists)
def test_vocabulary_of_property_ignores_identifier_order(
    identifiers: list[str],
) -> None:
    forward_vocabulary = vocabulary_of(tuple(identifiers))
    backward_vocabulary = vocabulary_of(tuple(reversed(identifiers)))

    assert forward_vocabulary == backward_vocabulary


@given(identifier_lists)
def test_vocabulary_of_property_holds_the_words_of_every_identifier(
    identifiers: list[str],
) -> None:
    vocabulary = vocabulary_of(tuple(identifiers))

    for identifier in identifiers:
        assert split_identifier_words(identifier) <= vocabulary

