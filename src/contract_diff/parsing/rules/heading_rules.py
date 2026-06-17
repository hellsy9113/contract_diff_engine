import re

ARTICLE_HEADING_RE = re.compile(
    r"^ARTICLE\s+(?P<number>[IVXLCDM]+|\d+)\s*[-:.]?\s*(?P<title>.+)$",
    re.IGNORECASE,
)
SECTION_HEADING_RE = re.compile(
    r"^SECTION\s+(?P<number>\d+(?:\.\d+)*)\s*[-:.]?\s*(?P<title>.+)$",
    re.IGNORECASE,
)
NUMBERED_HEADING_RE = re.compile(
    r"^(?P<number>\d+)\.\s+(?P<title>[A-Z][\w\s,&/-]{1,80})$"
)
