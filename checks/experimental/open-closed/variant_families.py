from responsibility_groups import find_connected_groups
from set_overlap import overlap_of

RARE_SHARE = 0.05
RARE_FLOOR = 10
MINIMUM_TOKEN_PLACES = 2
FAMILY_OVERLAP = 0.6
MINIMUM_FAMILY_SIZE = 3

type TokenPlaces = dict[str, frozenset[int]]


def rare_tokens(token_sets: list[frozenset[str]]) -> frozenset[str]:
    place_limit = max(RARE_FLOOR, RARE_SHARE * len(token_sets))
    kept_tokens: set[str] = set()

    for token, places in _places_of_tokens(token_sets).items():
        if MINIMUM_TOKEN_PLACES <= len(places) <= place_limit:
            kept_tokens.add(token)

    return frozenset(kept_tokens)


def find_variant_families(
    token_sets: list[frozenset[str]],
) -> tuple[frozenset[str], ...]:
    kept_tokens = sorted(rare_tokens(token_sets))
    token_positions = {token: index for index, token in enumerate(kept_tokens)}
    places_of_tokens = _places_of_tokens(token_sets)
    related_pairs: set[tuple[int, int]] = set()

    for token_set in token_sets:
        present_tokens = sorted(token_set & token_positions.keys())

        for first_position, first_token in enumerate(present_tokens):
            for second_token in present_tokens[first_position + 1 :]:
                first_places = places_of_tokens[first_token]
                second_places = places_of_tokens[second_token]

                if overlap_of(first_places, second_places) >= FAMILY_OVERLAP:
                    first_index = token_positions[first_token]
                    second_index = token_positions[second_token]
                    related_pairs.add((first_index, second_index))

    groups = find_connected_groups(len(kept_tokens), frozenset(related_pairs))
    families: list[frozenset[str]] = []

    for group in groups:
        if len(group) >= MINIMUM_FAMILY_SIZE:
            families.append(frozenset(kept_tokens[index] for index in group))

    return tuple(families)


def _places_of_tokens(token_sets: list[frozenset[str]]) -> TokenPlaces:
    places_by_token: dict[str, set[int]] = {}

    for place, token_set in enumerate(token_sets):
        for token in token_set:
            places_by_token.setdefault(token, set()).add(place)

    frozen_places: TokenPlaces = {}

    for token, places in places_by_token.items():
        frozen_places[token] = frozenset(places)

    return frozen_places
