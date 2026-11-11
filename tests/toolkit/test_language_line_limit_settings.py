import subprocess
import tempfile
import tomllib
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from check_options import LANGUAGE_NUMBER_OPTIONS, SUPPORTED_LANGUAGES
from configuration_support import TOOLKIT, written_configuration
from language_limit_support import (
    KNOWN_SETTINGS,
    LANGUAGE_LIMITS,
    LANGUAGE_LIMITS_TABLE,
    MINIMAL,
    checks_without_language_options,
    file_length_configuration,
    language_limit_tables,
    line_limits,
)
from settings import (
    check_settings,
    read_configuration,
    setting_lines,
    with_defaults,
)
from settings_validation import (
    CHECK_ORDER,
    COMMON_CHECK_KEYS,
    allowed_check_keys,
    validate_configuration,
)

LANGUAGES_SCRIPT = TOOLKIT / "languages.sh"


def test_defaults_to_no_language_line_limits() -> None:
    configuration = with_defaults({"source_directories": ["src"]})

    file_length = check_settings(configuration, "file-length")

    assert file_length[LANGUAGE_LIMITS] == {}


def test_reads_language_line_limits_from_toml(tmp_path: Path) -> None:
    configuration_path = written_configuration(
        tmp_path,
        MINIMAL
        + "[checks.file-length]\nmax-lines = 300\n"
        + f"[checks.file-length.{LANGUAGE_LIMITS}]\nrust = 500\ndart = 200\n",
    )

    configuration = read_configuration(configuration_path)

    lines = setting_lines(configuration, LANGUAGE_LIMITS_TABLE)
    assert lines == ["rust = 500", "dart = 200"]


def test_supported_languages_match_the_shell_languages() -> None:
    finished = subprocess.run(
        ["sh", "-c", f'. "{LANGUAGES_SCRIPT}"; echo $supported_languages'],
        capture_output=True,
        text=True,
        check=True,
    )

    assert set(finished.stdout.split()) == SUPPORTED_LANGUAGES


@given(language_limit_tables)
def test_check_settings_property_keeps_the_written_language_limits(
    language_limits: dict[str, int],
) -> None:
    configuration = file_length_configuration(
        {LANGUAGE_LIMITS: dict(language_limits)}
    )
    validate_configuration(configuration, KNOWN_SETTINGS)

    file_length = check_settings(configuration, "file-length")

    assert file_length[LANGUAGE_LIMITS] == language_limits


@given(language_limit_tables, line_limits)
def test_check_settings_property_keeps_the_default_beside_language_limits(
    language_limits: dict[str, int], maximum_lines: int
) -> None:
    configuration = file_length_configuration(
        {"max-lines": maximum_lines, LANGUAGE_LIMITS: dict(language_limits)}
    )
    validate_configuration(configuration, KNOWN_SETTINGS)

    file_length = check_settings(configuration, "file-length")

    assert file_length["max-lines"] == maximum_lines


@given(checks_without_language_options)
def test_check_settings_property_gives_language_limits_only_to_file_length(
    check_name: str,
) -> None:
    configuration = with_defaults({"source_directories": ["src"]})

    filled_settings = check_settings(configuration, check_name)

    assert LANGUAGE_LIMITS not in filled_settings


@given(st.sampled_from(CHECK_ORDER))
def test_allowed_check_keys_property_allows_language_limits_only_where_set(
    check_name: str,
) -> None:
    allowed_keys = allowed_check_keys(check_name)

    is_allowed = LANGUAGE_LIMITS in allowed_keys
    assert is_allowed == (check_name in LANGUAGE_NUMBER_OPTIONS)


@given(st.sampled_from(CHECK_ORDER))
def test_allowed_check_keys_property_always_allows_the_common_keys(
    check_name: str,
) -> None:
    allowed_keys = allowed_check_keys(check_name)

    assert COMMON_CHECK_KEYS.issubset(allowed_keys)


@given(st.sampled_from(sorted(LANGUAGE_NUMBER_OPTIONS)))
def test_allowed_check_keys_property_allows_every_language_option(
    check_name: str,
) -> None:
    allowed_keys = allowed_check_keys(check_name)

    assert set(LANGUAGE_NUMBER_OPTIONS[check_name]).issubset(allowed_keys)


@given(language_limit_tables)
def test_setting_lines_property_round_trips_language_limits_through_toml(
    language_limits: dict[str, int],
) -> None:
    configuration = file_length_configuration(
        {LANGUAGE_LIMITS: dict(language_limits)}
    )

    lines = setting_lines(configuration, LANGUAGE_LIMITS_TABLE)

    assert tomllib.loads("\n".join(lines)) == language_limits


@settings(deadline=None)
@given(language_limit_tables)
def test_read_configuration_property_round_trips_language_limits(
    language_limits: dict[str, int],
) -> None:
    table_lines: list[str] = []

    for language, line_limit in language_limits.items():
        table_lines.append(f"{language} = {line_limit}\n")

    text = (
        MINIMAL
        + f"[checks.file-length.{LANGUAGE_LIMITS}]\n"
        + "".join(table_lines)
    )

    with tempfile.TemporaryDirectory() as directory_name:
        configuration_path = written_configuration(Path(directory_name), text)
        configuration = read_configuration(configuration_path)

    file_length = check_settings(configuration, "file-length")
    assert file_length[LANGUAGE_LIMITS] == language_limits
