import pytest
from hypothesis import given

from code_members import CodeUnit
from code_units import BRANCH_KEYWORDS, parse_code_units
from semantic_finder_support import unique_member_names
from source_grammars import GRAMMARS_BY_SUFFIX

CLASS_NAME = "Holder"
CLASS_TITLE = f"class {CLASS_NAME}"
MARKER_SUFFIX = "_marker"


def _python_class(method_names: list[str]) -> str:
    methods = [
        f"    def {name}(self):\n        return {name}{MARKER_SUFFIX}\n"
        for name in method_names
    ]

    return f"class {CLASS_NAME}:\n" + "\n".join(methods)


def _typescript_class(method_names: list[str]) -> str:
    methods = [
        f"  {name}(): number {{ return {name}{MARKER_SUFFIX}; }}\n"
        for name in method_names
    ]

    return f"export class {CLASS_NAME} {{\n" + "".join(methods) + "}\n"


def _php_class(method_names: list[str]) -> str:
    methods = [
        f"  public function {name}() {{ return ${name}{MARKER_SUFFIX}; }}\n"
        for name in method_names
    ]

    return f"<?php\nclass {CLASS_NAME} {{\n" + "".join(methods) + "}\n"



def _python_functions(function_names: list[str]) -> str:
    functions = [
        f"def {name}():\n"
        "    def nested_helper():\n"
        f"        return {name}{MARKER_SUFFIX}\n"
        "    return nested_helper()\n"
        for name in function_names
    ]

    return "\n".join(functions)


def _typescript_functions(function_names: list[str]) -> str:
    functions = [
        f"export const {name} = (): number => {{\n"
        "  function nestedHelper(): number {\n"
        f"    return {name}{MARKER_SUFFIX};\n"
        "  }\n"
        "  return nestedHelper();\n"
        "};\n"
        for name in function_names
    ]

    return "".join(functions)


def _php_functions(function_names: list[str]) -> str:
    functions = [
        f"function {name}() {{\n"
        f"  $nested = function () {{ return ${name}{MARKER_SUFFIX}; }};\n"
        "  return $nested();\n"
        "}\n"
        for name in function_names
    ]

    return "<?php\n" + "".join(functions)



CLASS_SOURCES = {
    ".py": _python_class,
    ".ts": _typescript_class,
    ".php": _php_class,
}
FUNCTION_SOURCES = {
    ".py": _python_functions,
    ".ts": _typescript_functions,
    ".php": _php_functions,
}
CONSTRUCTOR_CLASSES = {
    ".py": "class Holder:\n    def __init__(self):\n        pass\n"
    "    def {name}(self):\n        pass\n",
    ".ts": "class Holder {\n  constructor() {}\n  {name}() {}\n}\n",
    ".php": "<?php\nclass Holder {\n  public function __construct() {}\n"
    "  public function {name}() {}\n}\n",
}


def _units_of(suffix: str, source: str) -> tuple[CodeUnit, ...]:
    grammar = GRAMMARS_BY_SUFFIX[suffix]

    return parse_code_units(f"src/holder{suffix}", source.encode(), grammar)


def _unit_titled(units: tuple[CodeUnit, ...], title: str) -> CodeUnit:
    for unit in units:
        if unit.title == title:
            return unit

    message = f"no unit titled {title}"
    raise AssertionError(message)


def test_names_the_module_unit_after_the_file() -> None:
    units = _units_of(".py", "def run_once():\n    pass\n")

    assert units[0].title == "module holder"
    assert units[0].line == 1


def test_reads_a_tsx_component_assigned_to_a_constant() -> None:
    source = "export const Badge = () => <span>{label}</span>;\n"

    units = _units_of(".tsx", source)

    assert [member.name for member in units[0].members] == ["Badge"]


@pytest.mark.parametrize("suffix", sorted(CLASS_SOURCES))
@given(method_names=unique_member_names)
def test_parse_code_units_property_lists_class_methods_in_order(
    suffix: str, method_names: list[str]
) -> None:
    units = _units_of(suffix, CLASS_SOURCES[suffix](method_names))

    class_unit = _unit_titled(units, CLASS_TITLE)

    grammar = GRAMMARS_BY_SUFFIX[suffix]

    for member in class_unit.members:
        assert member.owner_name == CLASS_NAME
        assert member.language == grammar.language

    assert [member.name for member in class_unit.members] == method_names


@pytest.mark.parametrize("suffix", sorted(CLASS_SOURCES))
@given(method_names=unique_member_names)
def test_parse_code_units_property_keeps_methods_out_of_the_module(
    suffix: str, method_names: list[str]
) -> None:
    units = _units_of(suffix, CLASS_SOURCES[suffix](method_names))

    assert units[0].members == ()


@pytest.mark.parametrize("suffix", sorted(FUNCTION_SOURCES))
@given(function_names=unique_member_names)
def test_parse_code_units_property_never_lists_a_nested_function(
    suffix: str, function_names: list[str]
) -> None:
    units = _units_of(suffix, FUNCTION_SOURCES[suffix](function_names))

    module_members = units[0].members

    assert [member.name for member in module_members] == function_names
    assert all(member.owner_name is None for member in module_members)


@pytest.mark.parametrize("suffix", sorted(CLASS_SOURCES))
@given(method_names=unique_member_names)
def test_parse_code_units_property_keeps_the_body_of_every_member(
    suffix: str, method_names: list[str]
) -> None:
    units = _units_of(suffix, CLASS_SOURCES[suffix](method_names))

    class_unit = _unit_titled(units, CLASS_TITLE)

    for member in class_unit.members:
        marker = f"{member.name}{MARKER_SUFFIX}"

        assert marker in member.source_text
        assert marker in member.identifiers


@pytest.mark.parametrize("suffix", sorted(CLASS_SOURCES))
@given(method_names=unique_member_names)
def test_parse_code_units_property_counts_the_lines_of_every_member(
    suffix: str, method_names: list[str]
) -> None:
    units = _units_of(suffix, CLASS_SOURCES[suffix](method_names))

    class_unit = _unit_titled(units, CLASS_TITLE)

    for member in class_unit.members:
        assert member.line_count == member.source_text.count("\n") + 1


@pytest.mark.parametrize("suffix", sorted(CONSTRUCTOR_CLASSES))
@given(method_names=unique_member_names)
def test_parse_code_units_property_marks_only_the_constructor(
    suffix: str, method_names: list[str]
) -> None:
    source = CONSTRUCTOR_CLASSES[suffix].replace("{name}", method_names[0])

    class_unit = _unit_titled(_units_of(suffix, source), CLASS_TITLE)
    constructor_flags = [member.is_constructor for member in class_unit.members]

    assert constructor_flags == [True, False]


def _python_dispatch(values: list[str]) -> str:
    branches = [
        f'    {"if" if position == 0 else "elif"} kind == "{value}":\n'
        f"        return {position}\n"
        for position, value in enumerate(values)
    ]

    fallback = "    else:\n        return -1\n"

    return "def dispatch(kind):\n" + "".join(branches) + fallback


def _typescript_dispatch(values: list[str]) -> str:
    cases = [
        f'    case "{value}":\n      return {position};\n'
        for position, value in enumerate(values)
    ]

    return (
        "export function dispatch(kind: string): number {\n"
        "  switch (kind) {\n" + "".join(cases) + "  }\n  return -1;\n}\n"
    )


def _php_dispatch(values: list[str]) -> str:
    branches = [
        f'{"if" if position == 0 else " elseif"} ($kind === "{value}") '
        f"{{ return {position}; }}"
        for position, value in enumerate(values)
    ]

    return (
        "<?php\nfunction dispatch($kind) {\n  "
        + "".join(branches)
        + " else { return -1; }\n}\n"
    )



DISPATCH_SOURCES = {
    ".py": _python_dispatch,
    ".ts": _typescript_dispatch,
    ".php": _php_dispatch,
}


@pytest.mark.parametrize("suffix", sorted(DISPATCH_SOURCES))
@given(values=unique_member_names)
def test_parse_code_units_property_keeps_one_head_per_compared_value(
    suffix: str, values: list[str]
) -> None:
    units = _units_of(suffix, DISPATCH_SOURCES[suffix](values))

    dispatch_member = units[0].members[0]

    assert len(dispatch_member.branch_heads) == len(values)

    for value, head in zip(values, dispatch_member.branch_heads, strict=True):
        assert value in head.condition
        assert head.keyword in BRANCH_KEYWORDS


def test_keeps_a_php_member_access_inside_its_branch_head() -> None:
    source = (
        "<?php\nclass Holder {\n  public function run() {\n"
        "    if ($this->kind === 'pdf') { return 1; }\n  }\n}\n"
    )

    class_unit = _unit_titled(_units_of(".php", source), CLASS_TITLE)
    branch_head = class_unit.members[0].branch_heads[0]

    assert branch_head.condition == " ($this->kind === 'pdf'"


def test_has_no_grammar_for_dart() -> None:
    assert ".dart" not in GRAMMARS_BY_SUFFIX
