from hypothesis import strategies as st

from check_options import (
    LANGUAGE_NUMBER_OPTIONS,
    MAXIMUM_LINES,
    SUPPORTED_LANGUAGES,
)
from settings import DEFAULT_SETTINGS, with_defaults
from settings_validation import CHECK_ORDER, Configuration

KNOWN_SETTINGS = {*DEFAULT_SETTINGS, "source_directories"}
LANGUAGE_LIMITS = "max-lines-by-language"
LANGUAGE_LIMITS_TABLE = f"checks.file-length.{LANGUAGE_LIMITS}"
MINIMAL = 'source_directories = ["src"]\n'
languages = st.sampled_from(sorted(SUPPORTED_LANGUAGES))
line_limits = st.integers(
    min_value=MAXIMUM_LINES.lowest, max_value=MAXIMUM_LINES.highest
)
too_low_line_limits = st.integers(max_value=MAXIMUM_LINES.lowest - 1)
too_high_line_limits = st.integers(min_value=MAXIMUM_LINES.highest + 1)
outside_line_limits = too_low_line_limits | too_high_line_limits
non_integers = (
    st.floats()
    | st.text()
    | st.booleans()
    | st.lists(st.integers(), max_size=2)
    | st.dictionaries(st.text(max_size=3), st.integers(), max_size=2)
)
language_limit_tables = st.dictionaries(languages, line_limits)
unknown_languages = st.text(min_size=1).filter(
    lambda name: name not in SUPPORTED_LANGUAGES
)
setting_names = st.from_regex(
    r"checks\.[a-z-]{1,12}\.[a-z-]{1,12}", fullmatch=True
)
checks_without_language_options = st.sampled_from(
    sorted(set(CHECK_ORDER) - set(LANGUAGE_NUMBER_OPTIONS))
)


def file_length_configuration(
    file_length: dict[str, object],
) -> Configuration:
    return with_defaults(
        {
            "source_directories": ["src"],
            "checks": {"file-length": file_length},
        }
    )
