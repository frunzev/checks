import keyword
from pathlib import Path

from hypothesis import strategies as st

from code_members import BranchHead, CodeMember, CodeUnit

TOOLKIT = Path(__file__).resolve().parent.parent
CODE_MODELS_DIRECTORY = TOOLKIT / ".models"
MEMBER_NAME_PREFIX = "run_"
MEMBER_PATH = "src/module.py"
MEMBER_LINE_COUNT = 6
MEMBER_LANGUAGE = "python"

lowercase_words = st.from_regex(r"[a-z]{3,10}", fullmatch=True).filter(
    lambda word: not keyword.iskeyword(word)
)
member_names = st.from_regex(r"[a-z]{3,8}", fullmatch=True).map(
    lambda word: MEMBER_NAME_PREFIX + word
)
unique_member_names = st.lists(
    member_names, min_size=1, max_size=5, unique=True
)


def code_member(
    name: str,
    identifiers: tuple[str, ...],
    owner_name: str | None,
    line: int,
    branch_heads: tuple[BranchHead, ...] = (),
) -> CodeMember:
    return CodeMember(
        path=MEMBER_PATH,
        language=MEMBER_LANGUAGE,
        line=line,
        line_count=MEMBER_LINE_COUNT,
        name=name,
        owner_name=owner_name,
        is_constructor=False,
        source_text=f"def {name}():\n    pass\n",
        identifiers=identifiers,
        branch_heads=branch_heads,
    )


def code_unit(members: tuple[CodeMember, ...]) -> CodeUnit:
    return CodeUnit(
        path=MEMBER_PATH,
        line=1,
        title="class Holder",
        members=members,
    )
