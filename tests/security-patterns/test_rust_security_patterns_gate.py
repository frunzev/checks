import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from check_support import (
    COPIED_TOOLKIT,
    HYPOTHESIS_SETTINGS,
    TOOLKIT,
    link_toolkit_tool,
    repository,
    run_configured,
    stage_file,
)

CALL_RULE = (
    "rules:\n"
    "  - id: no-{name}\n"
    "    pattern: {name}(...)\n"
    "    message: {name} runs arbitrary code\n"
    "    languages: [rust]\n"
    "    severity: ERROR\n"
)
RULESETS = "checks/stable/security-patterns/rust/rulesets.txt"
REGISTRY_RULESET = "p/rust"
function_names = st.from_regex(r"run_[a-z]{2,8}", fullmatch=True)
skipped_folders = st.sampled_from(["tools/build", "web/dist", "app/vendor"])


def _flagging_rule(root: Path, name: str) -> None:
    rule = root / "call-rule.yml"
    _ = rule.write_text(CALL_RULE.format(name=name), encoding="utf-8")
    rulesets = root / COPIED_TOOLKIT / RULESETS
    _ = rulesets.write_text(f"{rule}\n", encoding="utf-8")


def _source(name: str, entry_body: str) -> str:
    return (
        f"pub fn {name}(value: i32) -> i32 {{\n    value\n}}\n\n"
        f"pub fn entry() -> i32 {{\n    {entry_body}\n}}\n"
    )


def _verdict(
    name: str, source: str, source_directory: str, whitelist: str
) -> tuple[int, str]:
    configuration = (
        f'source_directories = ["{source_directory}"]\n'
        f"[checks.security-patterns]\nwhitelist = [{whitelist}]\n"
    )

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        repository(root)
        link_toolkit_tool(root, "semgrep")
        _flagging_rule(root, name)
        stage_file(root, f"{source_directory}/lib.rs", source)

        finished = run_configured(root, configuration, "security-patterns")

    return finished.returncode, finished.stdout + finished.stderr


def test_rust_rules_come_from_the_semgrep_rust_registry_ruleset() -> None:
    rulesets = (TOOLKIT / RULESETS).read_text(encoding="utf-8").split()

    assert REGISTRY_RULESET in rulesets


@HYPOTHESIS_SETTINGS
@given(function_names, st.booleans())
def test_security_patterns_property_fails_only_on_a_flagged_rust_call(
    name: str, is_called: bool
) -> None:
    entry_body = f"{name}(1)" if is_called else "1"

    returncode, output = _verdict(
        name, _source(name, entry_body), "app/src", ""
    )

    assert returncode == int(is_called), output


@HYPOTHESIS_SETTINGS
@given(function_names, skipped_folders)
def test_security_patterns_property_scans_rust_in_folders_semgrep_skips(
    name: str, source_directory: str
) -> None:
    returncode, output = _verdict(
        name, _source(name, f"{name}(1)"), source_directory, ""
    )

    assert returncode == 1, output


@HYPOTHESIS_SETTINGS
@given(function_names, st.booleans())
def test_security_patterns_property_honours_a_whitelisted_rust_rule(
    name: str, is_whitelisted: bool
) -> None:
    rule_id = f'"no-{name}"' if is_whitelisted else ""

    returncode, output = _verdict(
        name, _source(name, f"{name}(1)"), "app/src", rule_id
    )

    assert returncode == int(not is_whitelisted), output
