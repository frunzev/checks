from dataclasses import dataclass


@dataclass(frozen=True)
class SourceGrammar:
    name: str
    language: str
    class_node_types: frozenset[str]
    member_node_types: frozenset[str]
    constructor_names: frozenset[str]
    detached_body_node_type: str | None


TYPESCRIPT_CLASS_NODE_TYPES = frozenset(
    {"class_declaration", "abstract_class_declaration", "class"}
)
TYPESCRIPT_MEMBER_NODE_TYPES = frozenset(
    {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "arrow_function",
        "function_expression",
    }
)
TYPESCRIPT_CONSTRUCTOR_NAMES = frozenset({"constructor"})

PYTHON = SourceGrammar(
    name="python",
    language="python",
    class_node_types=frozenset({"class_definition"}),
    member_node_types=frozenset({"function_definition"}),
    constructor_names=frozenset({"__init__"}),
    detached_body_node_type=None,
)
TYPESCRIPT = SourceGrammar(
    name="typescript",
    language="typescript",
    class_node_types=TYPESCRIPT_CLASS_NODE_TYPES,
    member_node_types=TYPESCRIPT_MEMBER_NODE_TYPES,
    constructor_names=TYPESCRIPT_CONSTRUCTOR_NAMES,
    detached_body_node_type=None,
)
TSX = SourceGrammar(
    name="tsx",
    language="typescript",
    class_node_types=TYPESCRIPT_CLASS_NODE_TYPES,
    member_node_types=TYPESCRIPT_MEMBER_NODE_TYPES,
    constructor_names=TYPESCRIPT_CONSTRUCTOR_NAMES,
    detached_body_node_type=None,
)
PHP = SourceGrammar(
    name="php",
    language="php",
    class_node_types=frozenset({"class_declaration", "trait_declaration"}),
    member_node_types=frozenset({"function_definition", "method_declaration"}),
    constructor_names=frozenset({"__construct"}),
    detached_body_node_type=None,
)
DART = SourceGrammar(
    name="dart",
    language="dart",
    class_node_types=frozenset({"class_definition", "mixin_declaration"}),
    member_node_types=frozenset({"method_signature", "function_signature"}),
    constructor_names=frozenset(),
    detached_body_node_type="function_body",
)
GRAMMARS_BY_SUFFIX = {
    ".py": PYTHON,
    ".ts": TYPESCRIPT,
    ".mts": TYPESCRIPT,
    ".cts": TYPESCRIPT,
    ".tsx": TSX,
    ".php": PHP,
    ".dart": DART,
}
