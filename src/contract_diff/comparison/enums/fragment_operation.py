from enum import StrEnum


class FragmentOperation(StrEnum):
    EQUAL = "equal"
    INSERTED = "inserted"
    DELETED = "deleted"
    REPLACED = "replaced"
