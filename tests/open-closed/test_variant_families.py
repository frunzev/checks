from hypothesis import given
from hypothesis import strategies as st

from variant_families import (
    MINIMUM_FAMILY_SIZE,
    MINIMUM_TOKEN_PLACES,
    RARE_FLOOR,
    RARE_SHARE,
    find_variant_families,
    rare_tokens,
)

variant_words = st.from_regex(r"[a-m]{3,6}", fullmatch=True)
noise_words = st.from_regex(r"[n-z]{3,6}", fullmatch=True)
token_set_lists = st.lists(st.frozensets(noise_words, max_size=5), max_size=40)
family_tokens = st.frozensets(variant_words, min_size=3, max_size=5)
place_counts = st.integers(min_value=MINIMUM_TOKEN_PLACES, max_value=4)


def _place_counts_of(token_sets: list[frozenset[str]]) -> dict[str, int]:
    place_counts_by_token: dict[str, int] = {}

    for token_set in token_sets:
        for token in token_set:
            known_count = place_counts_by_token.get(token, 0)
            place_counts_by_token[token] = known_count + 1

    return place_counts_by_token


@given(token_set_lists)
def test_rare_tokens_property_keeps_tokens_seen_in_a_few_places(
    token_sets: list[frozenset[str]],
) -> None:
    place_limit = max(RARE_FLOOR, RARE_SHARE * len(token_sets))
    place_counts_by_token = _place_counts_of(token_sets)

    for token in rare_tokens(token_sets):
        assert place_counts_by_token[token] >= MINIMUM_TOKEN_PLACES
        assert place_counts_by_token[token] <= place_limit


@given(st.integers(min_value=RARE_FLOOR + 1, max_value=40))
def test_rare_tokens_property_drops_a_token_found_everywhere(
    set_count: int,
) -> None:
    token_sets = [
        frozenset({"kind", f"value{index}"}) for index in range(set_count)
    ]

    assert "kind" not in rare_tokens(token_sets)


@given(family_tokens, place_counts, token_set_lists)
def test_find_variant_families_property_finds_tokens_that_travel_together(
    family: frozenset[str],
    family_places: int,
    noise_sets: list[frozenset[str]],
) -> None:
    token_sets = [family] * family_places + noise_sets

    assert family in find_variant_families(token_sets)


@given(token_set_lists)
def test_find_variant_families_property_returns_large_rare_families(
    token_sets: list[frozenset[str]],
) -> None:
    kept_tokens = rare_tokens(token_sets)

    for family in find_variant_families(token_sets):
        assert len(family) >= MINIMUM_FAMILY_SIZE
        assert family <= kept_tokens
