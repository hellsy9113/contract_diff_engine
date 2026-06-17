import re

QUOTED_DEFINITION_RE = re.compile(
    r"^[\"“](?P<term>[^\"”]+)[\"”]\s+"
    r"(?P<body>(?:means|shall mean|means and includes)\b.+)$",
    re.IGNORECASE,
)
TERM_DEFINITION_RE = re.compile(
    r"^The term\s+[\"“](?P<term>[^\"”]+)[\"”]\s+"
    r"(?P<body>(?:means|shall mean)\b.+)$",
    re.IGNORECASE,
)
