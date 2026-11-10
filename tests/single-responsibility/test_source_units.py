import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from code_units import parse_code_units
from semantic_finder_support import lowercase_words, unique_member_names
from source_grammars import GRAMMARS_BY_SUFFIX
from source_units import grammar_for, read_code_units, source_paths_from

known_suffixes = st.sampled_from(sorted(GRAMMARS_BY_SUFFIX))
unknown_suffixes = st.from_regex(r"\.[a-z]{1,5}", fullmatch=True).filter(
    lambda suffix: suffix not in GRAMMARS_BY_SUFFIX
)
path_lists = st.lists(
    st.from_regex(r"[a-z]{1,8}/[a-z ]{1,8}\.py", fullmatch=True), max_size=5
)


@given(lowercase_words, known_suffixes)
def test_grammar_for_property_picks_the_grammar_of_the_suffix(
    stem: str, suffix: str
) -> None:
    grammar = grammar_for(Path(f"src/{stem}{suffix}"))

    assert grammar == GRAMMARS_BY_SUFFIX[suffix]


@given(lowercase_words, unknown_suffixes)
def test_grammar_for_property_rejects_an_unknown_suffix(
    stem: str, suffix: str
) -> None:
    with pytest.raises(ValueError, match="no grammar"):
        _ = grammar_for(Path(f"src/{stem}{suffix}"))


@given(path_lists)
def test_source_paths_from_property_reads_one_path_per_line(
    paths: list[str],
) -> None:
    listing = "\n".join(paths) + "\n\n"

    assert source_paths_from(listing) == [Path(path) for path in paths]


@settings(deadline=None)
@given(unique_member_names)
def test_read_code_units_property_matches_parsing_the_file_bytes(
    function_names: list[str],
) -> None:
    source = "".join(f"def {name}():\n    pass\n" for name in function_names)

    with tempfile.TemporaryDirectory() as directory_name:
        source_path = Path(directory_name) / "module.py"
        _ = source_path.write_text(source, encoding="utf-8")

        read_units = read_code_units([source_path])

    parsed_units = parse_code_units(
        str(source_path), source.encode(), GRAMMARS_BY_SUFFIX[".py"]
    )

    assert read_units == parsed_units
