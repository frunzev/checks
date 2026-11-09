import pytest
from hypothesis import given
from hypothesis import strategies as st

from settings import DEFAULT_SETTINGS, check_settings, with_defaults
from settings_validation import Configuration, validate_configuration

KNOWN_SETTINGS = {*DEFAULT_SETTINGS, "source_directories"}
PERCENT_OPTIONS = [
    ("single-responsibility", "code-similarity"),
    ("single-responsibility", "word-overlap"),
    ("semantic-duplicates", "code-similarity"),
]
DEFAULT_PERCENTS = [
    ("single-responsibility", "code-similarity", 50),
    ("single-responsibility", "word-overlap", 20),
    ("semantic-duplicates", "code-similarity", 85),
]
percents = st.integers(min_value=1, max_value=100)
outside_percents = st.integers(max_value=0) | st.integers(min_value=101)
non_integers = st.floats() | st.text() | st.booleans()


def _configured(
    check_name: str, option_name: str, percent: object
) -> Configuration:
    return with_defaults(
        {
            "source_directories": ["src"],
            "checks": {check_name: {option_name: percent}},
        }
    )


@pytest.mark.parametrize(
    ("check_name", "option_name", "default_percent"), DEFAULT_PERCENTS
)
def test_defaults_every_similarity_percent(
    check_name: str, option_name: str, default_percent: int
) -> None:
    configuration = with_defaults({"source_directories": ["src"]})

    written_settings = check_settings(configuration, check_name)

    assert written_settings[option_name] == default_percent


@pytest.mark.parametrize(("check_name", "option_name"), PERCENT_OPTIONS)
@given(percent=percents)
def test_check_settings_property_keeps_a_written_percent(
    check_name: str, option_name: str, percent: int
) -> None:
    configuration = _configured(check_name, option_name, percent)
    validate_configuration(configuration, KNOWN_SETTINGS)

    written_settings = check_settings(configuration, check_name)

    assert written_settings[option_name] == percent


@pytest.mark.parametrize(("check_name", "option_name"), PERCENT_OPTIONS)
@given(percent=outside_percents)
def test_validate_configuration_property_rejects_a_percent_out_of_range(
    check_name: str, option_name: str, percent: int
) -> None:
    configuration = _configured(check_name, option_name, percent)

    with pytest.raises(ValueError, match=option_name):
        validate_configuration(configuration, KNOWN_SETTINGS)


@pytest.mark.parametrize(("check_name", "option_name"), PERCENT_OPTIONS)
@given(percent=non_integers)
def test_validate_configuration_property_rejects_a_percent_of_another_type(
    check_name: str, option_name: str, percent: object
) -> None:
    configuration = _configured(check_name, option_name, percent)

    with pytest.raises(ValueError, match=option_name):
        validate_configuration(configuration, KNOWN_SETTINGS)
