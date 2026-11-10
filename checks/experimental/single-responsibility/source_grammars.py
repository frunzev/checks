from dataclasses import dataclass

import tree_sitter_php
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language


@dataclass(frozen=True)
class SourceGrammar:
    language: str
    tree_sitter_language: Language
    class_node_types: frozenset[str]
    member_node_types: frozenset[str]
    constructor_names: frozenset[str]


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
    language="python",
    tree_sitter_language=Language(tree_sitter_python.language()),
    class_node_types=frozenset({"class_definition"}),
    member_node_types=frozenset({"function_definition"}),
    constructor_names=frozenset({"__init__"}),
)
TYPESCRIPT = SourceGrammar(
    language="typescript",
    tree_sitter_language=Language(tree_sitter_typescript.language_typescript()),
    class_node_types=TYPESCRIPT_CLASS_NODE_TYPES,
    member_node_types=TYPESCRIPT_MEMBER_NODE_TYPES,
    constructor_names=TYPESCRIPT_CONSTRUCTOR_NAMES,
)
TSX = SourceGrammar(
    language="typescript",
    tree_sitter_language=Language(tree_sitter_typescript.language_tsx()),
    class_node_types=TYPESCRIPT_CLASS_NODE_TYPES,
    member_node_types=TYPESCRIPT_MEMBER_NODE_TYPES,
    constructor_names=TYPESCRIPT_CONSTRUCTOR_NAMES,
)
PHP = SourceGrammar(
    language="php",
    tree_sitter_language=Language(tree_sitter_php.language_php()),
    class_node_types=frozenset({"class_declaration", "trait_declaration"}),
    member_node_types=frozenset({"function_definition", "method_declaration"}),
    constructor_names=frozenset({"__construct"}),
)
GRAMMARS_BY_SUFFIX = {
    ".py": PYTHON,
    ".ts": TYPESCRIPT,
    ".mts": TYPESCRIPT,
    ".cts": TYPESCRIPT,
    ".tsx": TSX,
    ".php": PHP,
}
