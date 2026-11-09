from dataclasses import dataclass


@dataclass(frozen=True)
class BranchHead:
    keyword: str
    condition: str


@dataclass(frozen=True)
class CodeMember:
    path: str
    language: str
    line: int
    line_count: int
    name: str
    owner_name: str | None
    is_constructor: bool
    source_text: str
    identifiers: tuple[str, ...]
    branch_heads: tuple[BranchHead, ...]

    @property
    def display_name(self) -> str:
        if self.owner_name is None:
            return self.name

        return f"{self.owner_name}.{self.name}"


@dataclass(frozen=True)
class CodeUnit:
    path: str
    line: int
    title: str
    members: tuple[CodeMember, ...]


def members_of(units: tuple[CodeUnit, ...]) -> tuple[CodeMember, ...]:
    members: list[CodeMember] = []

    for unit in units:
        members.extend(unit.members)

    return tuple(members)
