import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from check_support import (
    HYPOTHESIS_SETTINGS,
    link_toolkit_node_modules,
    repository,
    run_configured,
    stage_file,
)

CONFIGURATION = 'source_directories = ["app/src"]\n'
FIRST = "app/src/first.rs"
SECOND = "app/src/second.rs"
COPIED_FUNCTION = (
    "pub fn total(values: &[i64]) -> i64 {\n"
    "    let mut sum = 0;\n"
    "    for value in values {\n"
    "        if *value > 100 {\n"
    "            sum += value * 2;\n"
    "        } else if *value > 10 {\n"
    "            sum += value + 3;\n"
    "        } else {\n"
    "            sum -= value;\n"
    "        }\n"
    "    }\n"
    "    let rounded = (sum * 100) / 100;\n"
    "    if rounded > 0 { rounded } else { 0 }\n"
    "}\n"
)
identifiers = st.from_regex(r"[a-z][a-z_]{2,12}[a-z]", fullmatch=True)
folder_names = st.lists(
    st.from_regex(r"[a-z]{2,8}", fullmatch=True), min_size=1, max_size=3
)
use_prefixes = st.sampled_from(["use", "pub use", "pub(crate) use"])


def _use_declarations(prefix: str, count: int) -> str:
    lines: list[str] = []

    for index in range(count):
        lines.append(f"{prefix} crate::helpers::helper{index}::{{one, two}};")

    return "\n".join(lines) + "\n"


def _distinct_module(name: str) -> str:
    return (
        f"pub fn {name}(count: u64) -> u64 {{\n"
        f"    let mut {name}_total = 0;\n"
        f"    for step in 0..count {{ {name}_total += step; }}\n"
        f"    {name}_total\n"
        "}\n"
    )


def _verdict(
    files: dict[str, str], configuration: str = CONFIGURATION
) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repository(root)
        link_toolkit_node_modules(root)

        for relative, source in files.items():
            stage_file(root, relative, source)

        finished = run_configured(root, configuration, "duplicate-code")

    return finished.returncode, finished.stdout + finished.stderr


def _copied_pair(name: str) -> dict[str, str]:
    return {
        FIRST: COPIED_FUNCTION + _distinct_module(f"{name}_one"),
        SECOND: COPIED_FUNCTION + _distinct_module(f"{name}_two"),
    }


@HYPOTHESIS_SETTINGS
@given(identifiers, st.booleans())
def test_duplicate_code_property_fails_only_on_a_copied_rust_block(
    name: str, is_copied: bool
) -> None:
    second_body = COPIED_FUNCTION if is_copied else ""

    returncode, output = _verdict(
        {
            FIRST: COPIED_FUNCTION + _distinct_module(f"{name}_one"),
            SECOND: second_body + _distinct_module(f"{name}_two"),
        }
    )

    assert returncode == int(is_copied), output


@HYPOTHESIS_SETTINGS
@given(st.integers(min_value=20, max_value=60), identifiers, use_prefixes)
def test_duplicate_code_property_ignores_shared_rust_use_declarations(
    declaration_count: int, name: str, prefix: str
) -> None:
    shared_declarations = _use_declarations(prefix, declaration_count)

    returncode, output = _verdict(
        {
            FIRST: shared_declarations + _distinct_module(f"{name}_one"),
            SECOND: shared_declarations + _distinct_module(f"{name}_two"),
        }
    )

    assert returncode == 0, output


@HYPOTHESIS_SETTINGS
@given(identifiers, folder_names)
def test_duplicate_code_property_finds_a_copy_in_nested_rust_folders(
    name: str, folders: list[str]
) -> None:
    nested_folder = "/".join(folders)
    copied_pair = _copied_pair(name)

    returncode, output = _verdict(
        {
            FIRST: copied_pair[FIRST],
            f"app/src/{nested_folder}/second.rs": copied_pair[SECOND],
        }
    )

    assert returncode == 1, output


@HYPOTHESIS_SETTINGS
@given(identifiers)
def test_duplicate_code_property_never_flags_a_whitelisted_rust_copy(
    name: str,
) -> None:
    configuration = (
        CONFIGURATION
        + '[checks.duplicate-code]\nwhitelist = ["**/second.rs"]\n'
    )

    returncode, output = _verdict(_copied_pair(name), configuration)

    assert returncode == 0, output
