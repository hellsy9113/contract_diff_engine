from enum import StrEnum


class NumberingStyle(StrEnum):
    NONE = "none"
    DECIMAL = "decimal"
    NESTED_DECIMAL = "nested_decimal"
    LETTER = "letter"
    ROMAN = "roman"
    ARTICLE = "article"
    SECTION = "section"
    BULLET = "bullet"
