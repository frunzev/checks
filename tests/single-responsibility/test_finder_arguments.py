from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from finder_arguments import PERCENT, finder_argument_parser, fraction_of

percents = st.integers(min_value=0, max_value=PERCENT)
folder_names = st.from_regex(r"[a-z]{1,10}", fullmatch=True)


@given(percents)
def test_fraction_of_property_maps_percents_onto_zero_to_one(
    percent: int,
) -> None:
    fraction = fraction_of(percent)

    assert 0.0 <= fraction <= 1.0
    assert round(fraction * PERCENT) == percent


@given(percents, folder_names, folder_names)
def test_finder_argument_parser_property_reads_back_every_argument(
    percent: int, models_folder: str, cache_folder: str
) -> None:
    parser = finder_argument_parser("finder")

    arguments = parser.parse_args(
        [
            "--code-similarity",
            str(percent),
            "--models",
            models_folder,
            "--cache",
            cache_folder,
        ]
    )

    assert arguments.code_similarity == percent
    assert arguments.models == Path(models_folder)
    assert arguments.cache == Path(cache_folder)
