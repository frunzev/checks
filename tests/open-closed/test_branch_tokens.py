import re

from hypothesis import given
from hypothesis import strategies as st

from branch_tokens import head_tokens, head_values
from semantic_finder_support import lowercase_words

LOWERCASE_TOKEN = re.compile(r"[a-z][a-z0-9_]{2,}")
ORDERINGS = st.sampled_from(["<", ">", "<=", ">="])


def test_reads_the_subject_and_the_compared_value() -> None:
    tokens = head_tokens(' report_kind == "PDF"')

    assert tokens == frozenset({"report_kind", "pdf"})


def test_drops_words_shorter_than_three_letters() -> None:
    assert head_tokens(" (a == b) or id") == frozenset()


@given(st.text(max_size=60))
def test_head_tokens_property_returns_only_lowercase_word_tokens(
    condition: str,
) -> None:
    for token in head_tokens(condition):
        assert LOWERCASE_TOKEN.fullmatch(token)
        assert token == token.lower()


@given(st.lists(lowercase_words, min_size=1, max_size=4))
def test_head_tokens_property_finds_quoted_and_bare_words(
    words: list[str],
) -> None:
    quoted_words = [f'"{word.upper()}"' for word in words]
    condition = " == ".join(words) + " or " + " , ".join(quoted_words)

    assert head_tokens(condition) == frozenset(words)


def test_finds_quoted_and_capitalized_values_only() -> None:
    condition = ' kind == "pdf" or shape is Shape.CIRCLE or size == limit'

    assert head_values(condition) == frozenset({"pdf", "shape", "circle"})


@given(st.lists(lowercase_words, min_size=1, max_size=4))
def test_head_values_property_never_counts_a_bare_lowercase_word(
    words: list[str],
) -> None:
    condition = " and ".join(f"{word} > {word}_limit" for word in words)

    assert head_values(condition) == frozenset()


@given(st.lists(lowercase_words, min_size=1, max_size=4))
def test_head_values_property_keeps_every_quoted_or_capitalized_word(
    words: list[str],
) -> None:
    quoted_words = [f"'{word}'" for word in words]
    capitalized_words = [word.capitalize() for word in words]
    condition = " or ".join(quoted_words + capitalized_words)

    assert head_values(condition) == frozenset(words)


@given(st.text(max_size=60))
def test_head_values_property_is_a_subset_of_the_head_tokens(
    condition: str,
) -> None:
    assert head_values(condition) <= head_tokens(condition)


def test_keeps_values_behind_member_access_arrows() -> None:
    assert head_values(" ($this->kind === 'pdf'") == frozenset({"pdf"})


@given(st.lists(lowercase_words, min_size=1, max_size=4), ORDERINGS)
def test_head_values_property_ignores_ordering_comparisons(
    words: list[str], ordering: str
) -> None:
    condition = f" {words[0]} {ordering} " + " or ".join(
        f"'{word}'" for word in words
    )

    assert head_values(condition) == frozenset()
