from typing import NamedTuple


class NumberOption(NamedTuple):
    name: str
    lowest: int
    highest: int
    default: int


type LanguageNumberOptions = dict[str, NumberOption]

SUPPORTED_LANGUAGES = frozenset(
    {"python", "typescript", "php", "dart", "rust"}
)
MAXIMUM_LINES = NumberOption("max-lines", 1, 100_000, 300)
NUMBER_OPTIONS: dict[str, tuple[NumberOption, ...]] = {
    "file-length": (MAXIMUM_LINES,),
    "coverage": (NumberOption("fail-under", 0, 100, 100),),
    "single-responsibility": (
        NumberOption("code-similarity", 1, 100, 50),
        NumberOption("word-overlap", 1, 100, 20),
    ),
    "semantic-duplicates": (NumberOption("code-similarity", 1, 100, 85),),
}
LANGUAGE_NUMBER_OPTIONS: dict[str, LanguageNumberOptions] = {
    "file-length": {"max-lines-by-language": MAXIMUM_LINES},
}
TOOL_OPTIONS: dict[str, frozenset[str]] = {
    "linters": frozenset({"ruff", "eslint", "phpcs"}),
    "strict-typing": frozenset({"phpstan"}),
    "dead-code": frozenset({"phpstan"}),
    "unused-deps": frozenset({"composer-dependency-analyser"}),
}
