from pathlib import PurePosixPath
from typing import NamedTuple

from tree_sitter import Node, Parser

from code_members import BranchHead, CodeMember, CodeUnit
from source_grammars import SourceGrammar

NAME_FIELD = "name"
MODULE_LINE = 1
SOURCE_ENCODING = "utf-8"
IDENTIFIER_NODE_TYPES = frozenset(
    {
        "identifier",
        "property_identifier",
        "private_property_identifier",
        "shorthand_property_identifier",
        "shorthand_property_identifier_pattern",
        "type_identifier",
        "name",
    }
)
BRANCH_KEYWORDS = frozenset({"if", "elif", "elseif", "case"})
HEAD_TERMINATORS = frozenset({":", "{", ")", ";"})


class NamedNode(NamedTuple):
    node: Node
    name_node: Node


def parse_code_units(
    path: str, source: bytes, grammar: SourceGrammar
) -> tuple[CodeUnit, ...]:
    parser = Parser(grammar.tree_sitter_language)
    root = parser.parse(source).root_node
    module_members = _members_of(root, None, path, source, grammar)
    module_title = f"module {PurePosixPath(path).stem}"
    units = [CodeUnit(path, MODULE_LINE, module_title, module_members)]

    for named_class in _named_classes_in(root, grammar):
        class_name = _text_of(named_class.name_node, source)
        class_members = _members_of(
            named_class.node, class_name, path, source, grammar
        )
        class_line = named_class.node.start_point.row + 1
        class_title = f"class {class_name}"
        units.append(CodeUnit(path, class_line, class_title, class_members))

    return tuple(units)


def _members_of(
    container: Node,
    owner_name: str | None,
    path: str,
    source: bytes,
    grammar: SourceGrammar,
) -> tuple[CodeMember, ...]:
    members: list[CodeMember] = []

    for named_member in _named_members_in(container, grammar):
        member_node = named_member.node
        name = _text_of(named_member.name_node, source)
        first_row = member_node.start_point.row

        members.append(
            CodeMember(
                path=path,
                language=grammar.language,
                line=first_row + 1,
                line_count=member_node.end_point.row - first_row + 1,
                name=name,
                owner_name=owner_name,
                is_constructor=name in grammar.constructor_names,
                source_text=_text_of(member_node, source),
                identifiers=_identifiers_in(member_node, source),
                branch_heads=_branch_heads_in(member_node, source),
            )
        )

    return tuple(members)


def _named_members_in(
    container: Node, grammar: SourceGrammar
) -> list[NamedNode]:
    named_members: list[NamedNode] = []
    pending_nodes = list(reversed(container.named_children))

    while pending_nodes:
        node = pending_nodes.pop()

        if node.type in grammar.member_node_types:
            name_node = _name_node_of(node)

            if name_node is not None:
                named_members.append(NamedNode(node, name_node))

            continue

        if node.type in grammar.class_node_types:
            continue

        pending_nodes.extend(reversed(node.named_children))

    return named_members


def _named_classes_in(root: Node, grammar: SourceGrammar) -> list[NamedNode]:
    named_classes: list[NamedNode] = []
    pending_nodes = list(reversed(root.named_children))

    while pending_nodes:
        node = pending_nodes.pop()
        if node.type in grammar.member_node_types:
            continue

        if node.type in grammar.class_node_types:
            name_node = _name_node_of(node)

            if name_node is not None:
                named_classes.append(NamedNode(node, name_node))

        pending_nodes.extend(reversed(node.named_children))

    return named_classes


def _name_node_of(node: Node) -> Node | None:
    naming_nodes = [node]

    if node.parent is not None:
        naming_nodes.append(node.parent)

    for naming_node in naming_nodes:
        name_node = naming_node.child_by_field_name(NAME_FIELD)

        if name_node is not None:
            return name_node

    return None


def _identifiers_in(member_node: Node, source: bytes) -> tuple[str, ...]:
    identifiers: list[str] = []
    pending_nodes = [member_node]

    while pending_nodes:
        node = pending_nodes.pop()

        if node.child_count == 0 and node.type in IDENTIFIER_NODE_TYPES:
            identifiers.append(_text_of(node, source))

        pending_nodes.extend(reversed(node.children))

    return tuple(identifiers)


def _branch_heads_in(
    member_node: Node, source: bytes
) -> tuple[BranchHead, ...]:
    branch_heads: list[BranchHead] = []
    open_keyword: Node | None = None
    pending_nodes = [member_node]

    while pending_nodes:
        node = pending_nodes.pop()
        pending_nodes.extend(reversed(node.children))

        if node.child_count > 0:
            continue

        if not node.is_named and node.type in BRANCH_KEYWORDS:
            open_keyword = node
            continue

        if open_keyword is None or node.type not in HEAD_TERMINATORS:
            continue

        condition_bytes = source[open_keyword.end_byte : node.start_byte]
        condition = condition_bytes.decode(SOURCE_ENCODING)
        branch_heads.append(BranchHead(open_keyword.type, condition))
        open_keyword = None

    return tuple(branch_heads)


def _text_of(node: Node, source: bytes) -> str:
    node_bytes = source[node.start_byte : node.end_byte]

    return node_bytes.decode(SOURCE_ENCODING)
