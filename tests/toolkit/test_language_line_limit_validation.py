from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from check_options import MAXIMUM_LINES
from configuration_support import written_configuration
from language_limit_support import (
    LANGUAGE_LIMITS,
    LANGUAGE_LIMITS_TABLE,
    MINIMAL,
    checks_without_language_options,
    language_limit_tables,
    languages,
    line_limits,
    non_integers,
    outside_line_limits,
    setting_names,
    unknown_languages,
)
from settings import read_configuration
from settings_validation import (
    ConfigurationError,
    validate_check,
    validate_language_number_options,
    validate_language_numbers,
    validate_number,
)


@pytest.mark.parametrize(
    ("table", "complaint"),
    [
        ("go = 500\n", "go is not one of"),
        ("Rust = 500\n", "Rust is not one of"),
        ("rust = 0\n", "rust must be between 1 and 100000"),
        ("rust = 100001\n", "rust must be between 1 and 100000"),
        ("rust = 5.0\n", "rust must be an integer"),
        ('rust = "500"\n', "rust must be an integer"),
        ("rust = true\n", "rust must be an integer"),
    ],
)
def test_rejects_an_invalid_language_line_limit(
    tmp_path: Path, table: str, complaint: str
) -> None:
    configuration_path = written_configuration(
        tmp_path, MINIMAL + f"[checks.file-length.{LANGUAGE_LIMITS}]\n{table}"
    )

    with pytest.raises(ConfigurationError, match=complaint):
        _ = read_configuration(configuration_path)


def test_rejects_language_line_limits_written_as_a_number(
    tmp_path: Path,
) -> None:
    configuration_path = written_configuration(
        tmp_path, MINIMAL + f"[checks.file-length]\n{LANGUAGE_LIMITS} = 500\n"
    )

    with pytest.raises(ConfigurationError, match="must be a table"):
        _ = read_configuration(configuration_path)


@given(line_limits)
def test_validate_number_property_accepts_every_number_in_range(
    line_limit: int,
) -> None:
    validate_number(LANGUAGE_LIMITS_TABLE, line_limit, MAXIMUM_LINES)


@given(outside_line_limits)
def test_validate_number_property_rejects_every_number_out_of_range(
    line_limit: int,
) -> None:
    with pytest.raises(ConfigurationError, match="must be between"):
        validate_number(LANGUAGE_LIMITS_TABLE, line_limit, MAXIMUM_LINES)


@given(non_integers)
def test_validate_number_property_rejects_every_non_integer(
    written_value: object,
) -> None:
    with pytest.raises(ConfigurationError, match="must be an integer"):
        validate_number(LANGUAGE_LIMITS_TABLE, written_value, MAXIMUM_LINES)


@given(setting_names, outside_line_limits | non_integers)
def test_validate_number_property_names_the_setting_in_every_error(
    setting_name: str, written_value: object
) -> None:
    with pytest.raises(ConfigurationError) as raised:
        validate_number(setting_name, written_value, MAXIMUM_LINES)

    assert str(raised.value).startswith(f"{setting_name} must be")


@given(language_limit_tables)
def test_validate_language_numbers_property_accepts_every_valid_table(
    language_limits: dict[str, int],
) -> None:
    validate_language_numbers(
        LANGUAGE_LIMITS_TABLE, dict(language_limits), MAXIMUM_LINES
    )


@given(language_limit_tables, unknown_languages, line_limits)
def test_validate_language_numbers_property_rejects_any_unknown_language(
    language_limits: dict[str, int], unknown_language: str, line_limit: int
) -> None:
    written_limits: dict[str, object] = {
        **language_limits,
        unknown_language: line_limit,
    }

    with pytest.raises(ConfigurationError) as raised:
        validate_language_numbers(
            LANGUAGE_LIMITS_TABLE, written_limits, MAXIMUM_LINES
        )

    assert f"{unknown_language} is not one of" in str(raised.value)


@given(language_limit_tables, languages, outside_line_limits | non_integers)
def test_validate_language_numbers_property_names_the_bad_language(
    language_limits: dict[str, int], language: str, written_value: object
) -> None:
    written_limits: dict[str, object] = {
        **language_limits,
        language: written_value,
    }

    with pytest.raises(ConfigurationError) as raised:
        validate_language_numbers(
            LANGUAGE_LIMITS_TABLE, written_limits, MAXIMUM_LINES
        )

    assert f"{LANGUAGE_LIMITS_TABLE}.{language} must be" in str(raised.value)


@given(st.integers() | st.text() | st.lists(st.integers(), max_size=3))
def test_validate_language_numbers_property_rejects_anything_but_a_table(
    written_limits: object,
) -> None:
    with pytest.raises(ConfigurationError, match="must be a table"):
        validate_language_numbers(
            LANGUAGE_LIMITS_TABLE, written_limits, MAXIMUM_LINES
        )


@given(language_limit_tables)
def test_validate_language_number_options_property_accepts_valid_limits(
    language_limits: dict[str, int],
) -> None:
    validate_language_number_options(
        "file-length", {LANGUAGE_LIMITS: dict(language_limits)}
    )


@given(unknown_languages, line_limits)
def test_validate_language_number_options_property_rejects_unknown_language(
    unknown_language: str, line_limit: int
) -> None:
    check = {LANGUAGE_LIMITS: {unknown_language: line_limit}}

    with pytest.raises(ConfigurationError, match=LANGUAGE_LIMITS):
        validate_language_number_options("file-length", check)


@given(checks_without_language_options, unknown_languages, non_integers)
def test_validate_language_number_options_property_ignores_other_checks(
    check_name: str, unknown_language: str, written_value: object
) -> None:
    check = {LANGUAGE_LIMITS: {unknown_language: written_value}}

    validate_language_number_options(check_name, check)


@given(st.dictionaries(st.sampled_from(["when", "scope"]), st.just("off")))
def test_validate_language_number_options_property_allows_a_missing_table(
    check: dict[str, object],
) -> None:
    validate_language_number_options("file-length", check)


@given(language_limit_tables, line_limits)
def test_validate_check_property_accepts_language_limits_beside_max_lines(
    language_limits: dict[str, int], maximum_lines: int
) -> None:
    check_section = {
        "max-lines": maximum_lines,
        LANGUAGE_LIMITS: dict(language_limits),
    }

    validate_check("file-length", check_section)


@given(checks_without_language_options, language_limit_tables)
def test_validate_check_property_rejects_language_limits_of_other_checks(
    check_name: str, language_limits: dict[str, int]
) -> None:
    check_section = {LANGUAGE_LIMITS: dict(language_limits)}

    with pytest.raises(ConfigurationError, match="unknown settings"):
        validate_check(check_name, check_section)


@given(languages, outside_line_limits)
def test_validate_check_property_rejects_a_language_limit_out_of_range(
    language: str, line_limit: int
) -> None:
    check_section = {LANGUAGE_LIMITS: {language: line_limit}}

    with pytest.raises(ConfigurationError, match=f"{language} must be"):
        validate_check("file-length", check_section)
