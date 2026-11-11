import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from check_support import (
    HYPOTHESIS_SETTINGS,
    repository,
    run_configured,
    stage_file,
)

DEFAULT_MAXIMUM_LINES = 300
SOURCE_DIRECTORY = "svc/src"
CONFIGURATION = f'source_directories = ["{SOURCE_DIRECTORY}"]\n'
LINE_TEMPLATES = {
    "python": "value_{number} = {number}",
    "typescript": "export const value{number} = {number};",
    "php": "$value{number} = {number};",
    "dart": "const value{number} = {number};",
    "rust": "pub const VALUE_{number}: i32 = {number};",
}
EXTENSIONS = {
    "python": "py",
    "typescript": "ts",
    "php": "php",
    "dart": "dart",
    "rust": "rs",
}
languages = st.sampled_from(sorted(LINE_TEMPLATES))
small_counts = st.integers(min_value=1, max_value=30)
language_limits = st.dictionaries(languages, small_counts)


def _count_per_language() -> dict[str, st.SearchStrategy[int]]:
    counts: dict[str, st.SearchStrategy[int]] = {}

    for language in sorted(LINE_TEMPLATES):
        counts[language] = small_counts

    return counts


line_counts = st.fixed_dictionaries(_count_per_language())


def _source_path(language: str) -> str:
    return f"{SOURCE_DIRECTORY}/values.{EXTENSIONS[language]}"


def _numbered_lines(language: str, count: int) -> str:
    lines: list[str] = []

    for number in range(count):
        lines.append(LINE_TEMPLATES[language].format(number=number))

    return "\n".join(lines) + "\n"


def _limits_configuration(
    maximum_lines: int, limits_by_language: dict[str, int]
) -> str:
    table_lines: list[str] = []

    for language, line_limit in limits_by_language.items():
        table_lines.append(f"{language} = {line_limit}\n")

    return (
        CONFIGURATION
        + f"[checks.file-length]\nmax-lines = {maximum_lines}\n"
        + "[checks.file-length.max-lines-by-language]\n"
        + "".join(table_lines)
    )


def _verdict(
    counts_by_language: dict[str, int], configuration: str
) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repository(root)

        for language, line_count in counts_by_language.items():
            source = _numbered_lines(language, line_count)
            stage_file(root, _source_path(language), source)

        finished = run_configured(root, configuration, "file-length")

    return finished.returncode, finished.stdout + finished.stderr


@HYPOTHESIS_SETTINGS
@given(small_counts, language_limits, line_counts)
def test_file_length_property_applies_the_limit_of_each_files_language(
    maximum_lines: int,
    limits_by_language: dict[str, int],
    counts_by_language: dict[str, int],
) -> None:
    configuration = _limits_configuration(maximum_lines, limits_by_language)

    returncode, output = _verdict(counts_by_language, configuration)

    is_any_overlong = False

    for language, line_count in counts_by_language.items():
        line_limit = limits_by_language.get(language, maximum_lines)
        is_overlong = line_count > line_limit
        finding = f"{_source_path(language)} ({line_count} lines)"
        is_reported = finding in output
        assert is_reported == is_overlong, output
        is_any_overlong = is_any_overlong or is_overlong

    assert returncode == int(is_any_overlong), output


@HYPOTHESIS_SETTINGS
@given(languages, languages, small_counts)
def test_file_length_property_never_lends_a_limit_to_another_language(
    raised_language: str, file_language: str, extra_lines: int
) -> None:
    maximum_lines = 5
    line_count = maximum_lines + extra_lines
    configuration = _limits_configuration(
        maximum_lines, {raised_language: line_count}
    )

    returncode, output = _verdict({file_language: line_count}, configuration)

    is_raised_for_the_file = raised_language == file_language
    assert returncode == int(not is_raised_for_the_file), output


@HYPOTHESIS_SETTINGS
@given(st.integers(min_value=DEFAULT_MAXIMUM_LINES - 3, max_value=320))
def test_file_length_property_holds_rust_to_the_default_limit(
    line_count: int,
) -> None:
    returncode, output = _verdict({"rust": line_count}, CONFIGURATION)

    is_overlong = line_count > DEFAULT_MAXIMUM_LINES
    assert returncode == int(is_overlong), output
    expected_finding = f"{_source_path('rust')} ({line_count} lines)"
    assert (expected_finding in output) == is_overlong


@HYPOTHESIS_SETTINGS
@given(st.from_regex(r"[a-z]{2,10}", fullmatch=True), small_counts)
def test_file_length_property_fails_fast_on_an_unknown_language(
    language_name: str, line_limit: int
) -> None:
    is_known = language_name in LINE_TEMPLATES
    configuration = _limits_configuration(300, {language_name: line_limit})

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repository(root)
        stage_file(root, _source_path("python"), "value = 1\n")

        finished = run_configured(root, configuration, "file-length")

    assert finished.returncode == int(not is_known), finished.stderr
    is_named = f"{language_name} is not one of" in finished.stderr
    assert is_named == (not is_known)


@HYPOTHESIS_SETTINGS
@given(languages, small_counts)
def test_file_length_property_whitelists_a_file_whatever_its_language(
    language: str, extra_lines: int
) -> None:
    configuration = (
        CONFIGURATION
        + "[checks.file-length]\nmax-lines = 1\n"
        + f'whitelist = ["{_source_path(language)}"]\n'
        + f"[checks.file-length.max-lines-by-language]\n{language} = 1\n"
    )

    returncode, output = _verdict({language: 1 + extra_lines}, configuration)

    assert returncode == 0, output
