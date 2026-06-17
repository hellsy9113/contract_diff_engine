import re

DECIMAL_CLAUSE_RE = re.compile(
    r"^(?P<number>\d+\.\d+(?:\.\d+)*(?:\([A-Za-z0-9ivxlcdmIVXLCDM]+\))?)"
    r"\s+(?P<body>.+)$"
)
STANDALONE_MARKER_RE = re.compile(
    r"^(?P<number>\([A-Za-z]\)|\([ivxlcdmIVXLCDM]+\))\s+(?P<body>.+)$"
)
LETTER_MARKER_RE = re.compile(r"^\([A-Za-z]\)$")
ROMAN_MARKER_RE = re.compile(r"^\([ivxlcdmIVXLCDM]+\)$")
BULLET_MARKER_RE = re.compile(r"^[•-]$")
